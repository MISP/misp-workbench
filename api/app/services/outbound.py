"""Where the server may fetch from, when someone other than an instance admin
chooses the URL (a feed's, a MISP server's).

Organisation admins set feed and server URLs, and the server fetches them and
shows what comes back (feed previews, attributes), so an unchecked URL lets
them read what the server can reach: its own services on loopback, a cloud's
metadata service on a link-local address, anything on the private network.

Two checks, on every request and every redirect hop:

- the host is one an admin allowed (runtime setting ``<kind>.source_hosts``:
  exact names or ``*.domain``). For feeds and servers an empty list means any
  host, so instances that never set it keep working; for warninglists it
  means none;
- no address it resolves to is one a fetch may never reach: loopback,
  link-local (cloud metadata), multicast, reserved, unspecified. Private
  ranges are fine: an internal MISP or a CMDB feed is legitimate.

The address is checked when the host is resolved, for a clear error, and
again on the socket once connected, before anything is sent: a host whose
DNS answers differently the second time (rebinding) is caught there. Through
a proxy the socket's peer is the proxy, which the operator chose, so only the
resolve-time check applies.
"""

import fnmatch
import ipaddress
import socket
from typing import Optional
from urllib.parse import urlsplit

import requests
from requests.adapters import HTTPAdapter
from urllib3.connection import HTTPConnection, HTTPSConnection
from urllib3.connectionpool import HTTPConnectionPool, HTTPSConnectionPool

FEEDS = "feeds"
SERVERS = "servers"
WARNINGLISTS = "warninglists"
# Kinds whose empty allowlist allows nothing (rather than any host).
ALLOWLIST_REQUIRED = {WARNINGLISTS}
_WHAT = {
    FEEDS: "feeds may fetch from",
    SERVERS: "MISP servers may connect to",
    WARNINGLISTS: "lists may sync from",
}


class DestinationRefused(ValueError):
    """A URL the server may not fetch."""


class ResponseTooLarge(ValueError):
    pass


# ── Addresses ─────────────────────────────────────────────────────────────


def forbidden_address(address: str) -> bool:
    """An address no fetch may reach, whatever the allowlist says."""
    ip = ipaddress.ip_address(address)
    # ::ffff:127.0.0.1 is 127.0.0.1 to the kernel, but not is_loopback.
    if ip.version == 6 and ip.ipv4_mapped:
        ip = ip.ipv4_mapped
    return (
        ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    )


def _resolve(host: str, port: int) -> set[str]:
    """The addresses a host resolves to."""
    return {info[4][0] for info in socket.getaddrinfo(host, port)}


def _literal(host: str) -> Optional[str]:
    try:
        return str(ipaddress.ip_address(host.strip("[]")))
    except ValueError:
        return None


# ── Hosts ─────────────────────────────────────────────────────────────────


def allowed_hosts(kind: str) -> list[str]:
    """The host patterns an admin allowed for ``kind`` (runtime setting
    ``<kind>.source_hosts``)."""
    from app.database import SessionLocal
    from app.services.runtime_settings import RuntimeSettings

    with SessionLocal() as db:
        hosts = RuntimeSettings(db).get_value(f"{kind}.source_hosts", default=[])
    return [str(h).strip().lower() for h in hosts or [] if str(h).strip()]


def check_url(url: Optional[str], kind: str, hosts: Optional[list] = None) -> str:
    """An http(s) URL on an allowed host, and not on a forbidden address
    written as such. Doesn't resolve the host: for saving a URL, when DNS
    may be down; fetching checks the addresses too (check_destination)."""
    parts = urlsplit((url or "").strip())
    if parts.scheme not in ("http", "https") or not parts.hostname:
        raise DestinationRefused("the URL must be http(s), with a host")
    host = parts.hostname.lower()
    literal = _literal(host)
    if literal and forbidden_address(literal):
        raise DestinationRefused(
            f"{host} is an address the server may never fetch from "
            "(loopback, link-local, multicast or reserved)"
        )
    hosts = allowed_hosts(kind) if hosts is None else hosts
    if hosts or kind in ALLOWLIST_REQUIRED:
        if not any(fnmatch.fnmatchcase(host, pattern) for pattern in hosts):
            raise DestinationRefused(
                f"{host} isn't a host {_WHAT.get(kind, 'the server may fetch from')}; "
                f"an admin allows hosts in the runtime settings ({kind}.source_hosts)"
            )
    return url.strip()


def check_destination(url: str, kind: str, hosts: Optional[list] = None) -> None:
    """check_url, and none of the addresses the host resolves to is one a
    fetch may never reach."""
    check_url(url, kind, hosts)
    parts = urlsplit(url.strip())
    port = parts.port or (443 if parts.scheme == "https" else 80)
    try:
        addresses = _resolve(parts.hostname, port)
    except socket.gaierror as error:
        raise DestinationRefused(f"{parts.hostname} doesn't resolve: {error}") from None
    blocked = sorted(a for a in addresses if forbidden_address(a))
    if blocked:
        raise DestinationRefused(
            f"{parts.hostname} resolves to an address the server may never "
            f"fetch from ({', '.join(blocked)})"
        )


# ── Sessions ──────────────────────────────────────────────────────────────


def _check_peer(sock) -> None:
    address = sock.getpeername()[0]
    if forbidden_address(address):
        raise DestinationRefused(
            f"the connection reached an address the server may never fetch "
            f"from ({address})"
        )


class _GuardedConnectionMixin:
    def _new_conn(self):
        sock = super()._new_conn()
        try:
            _check_peer(sock)
        except Exception:
            sock.close()
            raise
        return sock


class _GuardedHTTPConnection(_GuardedConnectionMixin, HTTPConnection):
    pass


class _GuardedHTTPSConnection(_GuardedConnectionMixin, HTTPSConnection):
    pass


class _GuardedHTTPPool(HTTPConnectionPool):
    ConnectionCls = _GuardedHTTPConnection


class _GuardedHTTPSPool(HTTPSConnectionPool):
    ConnectionCls = _GuardedHTTPSConnection


class GuardedAdapter(HTTPAdapter):
    """Checks every request it sends, redirect hops included (requests calls
    the adapter once per hop), against ``kind``'s rules."""

    def __init__(self, kind: str, hosts: Optional[list] = None, **kwargs):
        self.kind = kind
        # Read once: a MISP pull sends thousands of requests.
        self.hosts = allowed_hosts(kind) if hosts is None else list(hosts)
        super().__init__(**kwargs)

    def init_poolmanager(self, *args, **kwargs):
        super().init_poolmanager(*args, **kwargs)
        # A new dict: urllib3's default is shared by every pool manager.
        self.poolmanager.pool_classes_by_scheme = {
            "http": _GuardedHTTPPool,
            "https": _GuardedHTTPSPool,
        }

    def send(self, request, *args, **kwargs):
        check_destination(request.url, self.kind, self.hosts)
        return super().send(request, *args, **kwargs)


def guard(session: requests.Session, kind: str, hosts=None) -> requests.Session:
    adapter = GuardedAdapter(kind, hosts)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


def session(kind: str, hosts: Optional[list] = None) -> requests.Session:
    return guard(requests.Session(), kind, hosts)


def get(
    url: str,
    kind: str,
    *,
    headers: Optional[dict] = None,
    timeout=(10, 120),
    max_bytes: Optional[int] = None,
) -> requests.Response:
    """GET ``url`` within ``kind``'s rules, reading at most ``max_bytes``.

    The body is read before returning (``response.content``); a larger one
    raises ResponseTooLarge.
    """
    with session(kind) as s:
        response = s.get(url, headers=headers, timeout=timeout, stream=True)
        try:
            body = bytearray()
            for chunk in response.iter_content(64 * 1024):
                body += chunk
                if max_bytes is not None and len(body) > max_bytes:
                    raise ResponseTooLarge(
                        f"the response is larger than {max_bytes // (1024 * 1024)} MB"
                    )
            response._content = bytes(body)
        finally:
            response.close()
        return response
