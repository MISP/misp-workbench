import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest
import requests

from app.services import outbound

FEEDS = outbound.FEEDS


@pytest.fixture
def no_settings(monkeypatch):
    """No allowlist set, without reading the runtime settings."""
    monkeypatch.setattr(outbound, "allowed_hosts", lambda kind: [])


@pytest.fixture
def local_server():
    """An HTTP server on loopback, recording the requests it gets."""
    received = []

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            received.append(self.path)
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"secret")

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield server.server_port, received
    server.shutdown()
    server.server_close()


class TestAddresses:
    @pytest.mark.parametrize(
        "address",
        [
            "127.0.0.1",
            "127.1.2.3",
            "::1",
            "169.254.169.254",
            "fe80::1",
            "0.0.0.0",
            "::",
            "224.0.0.1",
            "240.0.0.1",
            # IPv4-mapped IPv6 is the IPv4 address to the kernel.
            "::ffff:127.0.0.1",
            "::ffff:169.254.169.254",
        ],
    )
    def test_never_reached(self, address):
        assert outbound.forbidden_address(address)

    @pytest.mark.parametrize(
        "address", ["10.1.2.3", "192.168.1.10", "172.16.0.5", "8.8.8.8", "2001:db8::1"]
    )
    def test_private_and_public_ranges_are_fine(self, address):
        # An internal MISP or a CMDB feed is on a private range.
        assert not outbound.forbidden_address(address)


class TestUrls:
    def test_any_host_while_no_allowlist_is_set(self):
        assert outbound.check_url("https://example.com/feed.csv", FEEDS, [])

    def test_allowlist(self):
        hosts = ["*.abuse.ch"]
        assert outbound.check_url("https://urlhaus.abuse.ch/x", FEEDS, hosts)
        with pytest.raises(outbound.DestinationRefused, match="feeds.source_hosts"):
            outbound.check_url("https://example.com/x", FEEDS, hosts)

    def test_warninglists_need_an_allowlist(self):
        with pytest.raises(outbound.DestinationRefused, match="isn't a host"):
            outbound.check_url("https://cmdb.example/x", outbound.WARNINGLISTS, [])

    @pytest.mark.parametrize(
        "url",
        [
            "http://169.254.169.254/latest/meta-data/",
            "http://127.0.0.1:8080/",
            "http://[::1]/",
            "http://[::ffff:127.0.0.1]/",
        ],
    )
    def test_forbidden_literals_whatever_the_allowlist(self, url):
        with pytest.raises(outbound.DestinationRefused, match="never fetch"):
            outbound.check_url(url, FEEDS, ["*"])

    @pytest.mark.parametrize("url", ["file:///etc/passwd", "ftp://x/y", "", None])
    def test_only_http(self, url):
        with pytest.raises(outbound.DestinationRefused, match="http"):
            outbound.check_url(url, FEEDS, [])

    def test_hosts_resolving_to_forbidden_addresses(self, monkeypatch):
        monkeypatch.setattr(
            outbound, "_resolve", lambda host, port: {"10.0.0.5", "169.254.169.254"}
        )
        with pytest.raises(outbound.DestinationRefused, match="169.254.169.254"):
            outbound.check_destination("http://metadata.example/", FEEDS, [])
        monkeypatch.setattr(outbound, "_resolve", lambda host, port: {"10.0.0.5"})
        outbound.check_destination("http://cmdb.example/", FEEDS, [])


class TestFetching:
    def test_loopback_is_refused(self, no_settings, local_server):
        port, received = local_server
        with pytest.raises(outbound.DestinationRefused):
            outbound.get(f"http://127.0.0.1:{port}/", FEEDS)
        with pytest.raises(outbound.DestinationRefused):
            outbound.get(f"http://localhost:{port}/", FEEDS)
        assert received == []

    def test_rebinding_is_caught_on_the_socket(
        self, no_settings, local_server, monkeypatch
    ):
        """The name resolves to a public address when checked, and to
        loopback when connecting: refused before anything is sent."""
        port, received = local_server
        monkeypatch.setattr(outbound, "_resolve", lambda host, port: {"8.8.8.8"})
        with pytest.raises(outbound.DestinationRefused, match="connection reached"):
            outbound.get(f"http://localhost:{port}/", FEEDS)
        assert received == []

    def test_redirects_are_checked_hop_by_hop(self, no_settings, monkeypatch):
        """A first hop on an allowed host redirecting to cloud metadata."""

        class Redirecting(requests.adapters.BaseAdapter):
            def send(self, request, **kwargs):
                response = requests.Response()
                response.status_code = 302
                response.headers["Location"] = "http://169.254.169.254/latest/"
                response.url = request.url
                response.request = request
                response.raw = None
                response._content = b""
                response._content_consumed = True
                return response

            def close(self):
                pass

        session = outbound.session(FEEDS, [])
        session.mount("http://feed.example/", Redirecting())
        with pytest.raises(outbound.DestinationRefused, match="never fetch"):
            session.get("http://feed.example/list.txt", timeout=5)

    def test_size_cap(self, monkeypatch, no_settings, local_server):
        port, _ = local_server
        # Let loopback through for this one: the cap is what is tested.
        monkeypatch.setattr(outbound, "forbidden_address", lambda address: False)
        response = outbound.get(f"http://127.0.0.1:{port}/", FEEDS, max_bytes=100)
        assert response.content == b"secret"
        with pytest.raises(outbound.ResponseTooLarge):
            outbound.get(f"http://127.0.0.1:{port}/", FEEDS, max_bytes=3)


class TestPyMISP:
    def test_http_requests_go_through_the_guard(
        self, no_settings, local_server, monkeypatch
    ):
        """PyMISP takes an adapter for https:// only and sends its first
        request (with the key) from its constructor: the http:// one has to
        be guarded before that, or this would reach the loopback server."""
        from app.repositories.servers import _GuardedPyMISP

        port, received = local_server
        monkeypatch.setattr(outbound, "_resolve", lambda host, port: {"8.8.8.8"})
        with pytest.raises(Exception, match="connection reached"):
            _GuardedPyMISP(
                url=f"http://localhost:{port}",
                key="k" * 40,
                ssl=False,
                timeout=5,
                https_adapter=outbound.GuardedAdapter(outbound.SERVERS, []),
            )
        assert received == []
