"""Unit tests for sink formatters and transports (no database needed).

Transports are exercised against real local listeners: an HTTP server for
Splunk HEC and webhooks, a TCP socket for GELF/syslog, a UDP socket for syslog.
"""

import hashlib
import hmac
import json
import socket
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from app.repositories import sinks as sinks_repository
from app.services.sinks import formatters
from app.services.sinks.transports import SinkDeliveryError, open_transport

ATTRIBUTE = {
    "uuid": "a1",
    "type": "ip-dst",
    "category": "Network activity",
    "value": "198.51.100.7",
    "to_ids": True,
    "comment": "C2 = beacon|relay\nsecond line",
    "timestamp": 1700000000,
    "tags": [{"name": "tlp:amber"}],
}
EVENT = {
    "uuid": "e1",
    "info": "APT campaign",
    "threat_level": 1,
    "date": "2024-01-15",
    "organisation": {"name": "CIRCL"},
    "tags": [{"name": 'misp-galaxy:threat-actor="APT29"'}],
}


def record(**overrides):
    return formatters.build_record({**ATTRIBUTE, **overrides}, EVENT)


# ── Formatters ────────────────────────────────────────────────────────────


class TestFormatters:
    def test_record_carries_event_context(self):
        r = record()
        assert r["value"] == "198.51.100.7"
        assert r["tags"] == ["tlp:amber"]
        assert r["event"]["org"] == "CIRCL"
        assert formatters.all_tags(r) == [
            "tlp:amber",
            'misp-galaxy:threat-actor="APT29"',
        ]

    def test_splunk_hec_body(self):
        body = formatters.splunk_hec_body(
            [record(), record(uuid="a2")],
            {"index": "threatintel", "sourcetype": "misp"},
        )
        events = [json.loads(line) for line in body.splitlines()]
        assert [e["event"]["uuid"] for e in events] == ["a1", "a2"]
        assert events[0]["time"] == 1700000000
        assert events[0]["index"] == "threatintel"
        assert events[0]["sourcetype"] == "misp"

    def test_gelf_frames(self):
        frames = formatters.gelf_frames([record(), record(uuid="a2")])
        messages = [json.loads(f) for f in frames.split(b"\0") if f]
        assert len(messages) == 2
        assert messages[0]["version"] == "1.1"
        assert messages[0]["_misp_value"] == "198.51.100.7"
        assert messages[0]["_misp_to_ids"] == 1
        # Null fields are dropped, not sent.
        assert all(v is not None for v in messages[0].values())

    def test_cef_escaping_and_field_mapping(self):
        line = formatters.syslog_line(record(), "siem relay")
        assert line.startswith("<134>1 ")
        assert " siem_relay misp-workbench - misp-indicator - CEF:0|MISP|" in line
        cef = line.split(" - misp-indicator - ", 1)[1]
        parts = cef.split("|", 7)
        # Event class, name and severity (threat level 1 -> 8).
        assert parts[4:7] == ["misp:ip-dst", "MISP indicator", "8"]
        extension = parts[7]
        # ip-dst lands in CEF's own dst field.
        assert "dst=198.51.100.7" in extension
        assert "msg=APT campaign" in extension
        assert "\n" not in line

    def test_cef_escapes_extension_values(self):
        cef = formatters.cef_message(record(value="a=b\\c\nd", type="text"))
        assert "cs1=a\\=b\\\\c\\nd" in cef

    def test_webhook_body_sends_event_once(self):
        body = json.loads(formatters.webhook_body([record(), record(uuid="a2")]))
        assert body["event"]["uuid"] == "e1"
        assert [a["uuid"] for a in body["attributes"]] == ["a1", "a2"]
        assert "event" not in body["attributes"][0]


class TestFilters:
    def test_select_records(self):
        attributes = [
            {**ATTRIBUTE, "uuid": "amber", "tags": [{"name": "tlp:amber"}]},
            {**ATTRIBUTE, "uuid": "red", "tags": [{"name": "tlp:red"}]},
            {**ATTRIBUTE, "uuid": "none", "tags": []},
        ]

        def uuids(filters):
            return [
                r["uuid"]
                for r in sinks_repository.select_records(attributes, EVENT, filters)
            ]

        assert uuids({"exclude_tags": ["tlp:red"]}) == ["amber", "none"]
        assert uuids({"tags": ["tlp:amber"]}) == ["amber"]
        # Patterns, and event tags count for every attribute.
        assert uuids({"tags": ["misp-galaxy:threat-actor=*"]}) == [
            "amber",
            "red",
            "none",
        ]
        assert uuids({"exclude_tags": ["misp-galaxy:*"]}) == []


# ── Transports ────────────────────────────────────────────────────────────


@pytest.fixture
def http_sink():
    received = []

    class Handler(BaseHTTPRequestHandler):
        status = 200

        def do_POST(self):
            body = self.rfile.read(int(self.headers["Content-Length"]))
            received.append(
                {"path": self.path, "headers": dict(self.headers), "body": body}
            )
            self.send_response(Handler.status)
            self.end_headers()
            self.wfile.write(b'{"text":"Success","code":0}')

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_port}", received, Handler
    server.shutdown()
    server.server_close()


@pytest.fixture
def tcp_listener():
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    sock.listen(1)
    sock.settimeout(5)
    yield sock
    sock.close()


def _read_all(listener):
    conn, _ = listener.accept()
    conn.settimeout(5)
    chunks = []
    with conn:
        while chunk := conn.recv(65536):
            chunks.append(chunk)
    return b"".join(chunks)


class TestTransports:
    def test_splunk_hec(self, http_sink):
        url, received, _ = http_sink
        transport = open_transport(
            "splunk_hec", {"url": f"{url}/services/collector/event", "token": "tok"}
        )
        transport.send([record(), record(uuid="a2")])
        transport.close()
        [request] = received
        assert request["path"] == "/services/collector/event"
        assert request["headers"]["Authorization"] == "Splunk tok"
        assert len(request["body"].splitlines()) == 2

    def test_webhook_signature(self, http_sink):
        url, received, _ = http_sink
        transport = open_transport("webhook", {"url": url, "secret": "s3cret"})
        transport.send([record()])
        transport.send([record(uuid="a2")])
        transport.close()
        first, second = received
        expected = hmac.new(b"s3cret", first["body"], hashlib.sha256).hexdigest()
        assert first["headers"]["X-Misp-Workbench-Signature"] == f"sha256={expected}"
        # Batches of one delivery share a delivery id.
        assert (
            first["headers"]["X-Misp-Workbench-Delivery"]
            == second["headers"]["X-Misp-Workbench-Delivery"]
        )

    def test_http_error_is_a_delivery_error(self, http_sink):
        url, _, handler = http_sink
        handler.status = 503
        transport = open_transport("webhook", {"url": url})
        with pytest.raises(SinkDeliveryError, match="503"):
            transport.send([record()])

    def test_unreachable_is_a_delivery_error(self):
        # Port 9 on localhost: nothing listens, the connection is refused.
        transport = open_transport("gelf", {"host": "127.0.0.1", "port": 9})
        with pytest.raises(SinkDeliveryError, match="cannot connect"):
            transport.send([record()])

    def test_gelf_over_tcp_reuses_one_connection(self, tcp_listener):
        port = tcp_listener.getsockname()[1]
        transport = open_transport("gelf", {"host": "127.0.0.1", "port": port})
        transport.send([record()])
        transport.send([record(uuid="a2")])
        transport.close()
        frames = [json.loads(f) for f in _read_all(tcp_listener).split(b"\0") if f]
        assert [f["_misp_attribute_uuid"] for f in frames] == ["a1", "a2"]

    def test_syslog_tcp_is_newline_framed(self, tcp_listener):
        port = tcp_listener.getsockname()[1]
        transport = open_transport(
            "syslog", {"host": "127.0.0.1", "port": port, "protocol": "tcp"}
        )
        transport.send([record(), record(uuid="a2")])
        transport.close()
        lines = _read_all(tcp_listener).decode().splitlines()
        assert len(lines) == 2
        assert all(line.startswith("<134>1 ") for line in lines)

    def test_syslog_udp_sends_one_datagram_per_message(self):
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as receiver:
            receiver.bind(("127.0.0.1", 0))
            receiver.settimeout(5)
            port = receiver.getsockname()[1]
            transport = open_transport(
                "syslog", {"host": "127.0.0.1", "port": port, "protocol": "udp"}
            )
            transport.send([record(), record(uuid="a2")])
            transport.close()
            datagrams = [receiver.recv(65536).decode() for _ in range(2)]
        assert all("CEF:0|MISP|misp-workbench|" in d for d in datagrams)
