"""Send formatted batches to a sink.

``open_transport`` returns a transport whose ``send(records)`` delivers one
batch; stream transports (GELF, syslog over TCP) keep a single connection for
a whole delivery. Every failure is raised as :class:`SinkDeliveryError`, which
the delivery task retries with backoff.
"""

import hashlib
import hmac
import os
import socket
import ssl
import tempfile
import uuid
from typing import Optional, Union

import requests

from app.services.sinks import formatters

CONNECT_TIMEOUT = 5
READ_TIMEOUT = 30
USER_AGENT = "misp-workbench-sinks"


class SinkDeliveryError(Exception):
    pass


def _tls_context(config: dict) -> ssl.SSLContext:
    """Verify against ``ca_cert`` when given, else the system trust store.

    ``verify_tls: false`` is an explicit, per-sink opt-out for endpoints whose
    certificate can't be verified; ``ca_cert`` is the better fix for those.
    """
    context = ssl.create_default_context(cadata=config.get("ca_cert") or None)
    if not config.get("verify_tls", True):
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
    return context


class _HttpVerify:
    """The ``verify`` argument requests needs: a CA bundle path or a flag.

    requests only takes a CA certificate as a file, so a configured
    ``ca_cert`` is written to a temporary file for the transport's lifetime.
    """

    def __init__(self, config: dict):
        self._path: Optional[str] = None
        if config.get("ca_cert"):
            fd, self._path = tempfile.mkstemp(suffix=".pem")
            with os.fdopen(fd, "w") as f:
                f.write(config["ca_cert"])
            self.value: Union[bool, str] = self._path
        else:
            self.value = bool(config.get("verify_tls", True))

    def close(self) -> None:
        if self._path and os.path.exists(self._path):
            os.remove(self._path)


def _connect(config: dict) -> socket.socket:
    try:
        sock = socket.create_connection(
            (config["host"], config["port"]), timeout=CONNECT_TIMEOUT
        )
        sock.settimeout(READ_TIMEOUT)
        if config.get("tls"):
            sock = _tls_context(config).wrap_socket(
                sock, server_hostname=config["host"]
            )
        return sock
    except OSError as error:
        raise SinkDeliveryError(
            f"cannot connect to {config['host']}:{config['port']}: {error}"
        ) from error


def _post(
    url: str, body: str, headers: dict, verify: Union[bool, str]
) -> requests.Response:
    try:
        response = requests.post(
            url,
            data=body.encode("utf-8"),
            headers={"User-Agent": USER_AGENT, **headers},
            timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
            verify=verify,
            # A redirect would re-send the payload (and for HEC, the token) to
            # wherever the endpoint points; a sink delivers to its URL only.
            allow_redirects=False,
        )
    except requests.RequestException as error:
        raise SinkDeliveryError(f"request to {url} failed: {error}") from error
    if response.status_code >= 300:
        # Status only: the body is the endpoint's, and echoing it through the
        # test endpoint would let a sink be used to read internal services.
        raise SinkDeliveryError(f"{url} answered HTTP {response.status_code}")
    return response


class SplunkHecTransport:
    def __init__(self, config: dict):
        self.config = config
        self.verify = _HttpVerify(config)

    def send(self, records: list[dict]) -> None:
        _post(
            self.config["url"],
            formatters.splunk_hec_body(records, self.config),
            {
                "Authorization": f"Splunk {self.config['token']}",
                "Content-Type": "application/json",
            },
            self.verify.value,
        )

    def close(self) -> None:
        self.verify.close()


class WebhookTransport:
    def __init__(self, config: dict):
        self.config = config
        self.verify = _HttpVerify(config)
        self.delivery_id = str(uuid.uuid4())

    def send(self, records: list[dict]) -> None:
        body = formatters.webhook_body(records)
        headers = {
            "Content-Type": "application/json",
            # Same id for every batch of one delivery, so receivers can group them.
            "X-Misp-Workbench-Delivery": self.delivery_id,
        }
        if self.config.get("secret"):
            signature = hmac.new(
                self.config["secret"].encode("utf-8"),
                body.encode("utf-8"),
                hashlib.sha256,
            ).hexdigest()
            headers["X-Misp-Workbench-Signature"] = f"sha256={signature}"
        _post(self.config["url"], body, headers, self.verify.value)

    def close(self) -> None:
        self.verify.close()


class _StreamTransport:
    """A TCP (optionally TLS) connection opened on first send."""

    def __init__(self, config: dict):
        self.config = config
        self.sock: Optional[socket.socket] = None

    def _sendall(self, payload: bytes) -> None:
        if self.sock is None:
            self.sock = _connect(self.config)
        try:
            self.sock.sendall(payload)
        except OSError as error:
            raise SinkDeliveryError(
                f"sending to {self.config['host']}:{self.config['port']} failed: {error}"
            ) from error

    def close(self) -> None:
        if self.sock is not None:
            try:
                self.sock.close()
            finally:
                self.sock = None


class GelfTransport(_StreamTransport):
    def send(self, records: list[dict]) -> None:
        self._sendall(formatters.gelf_frames(records))


class SyslogTransport(_StreamTransport):
    def send(self, records: list[dict]) -> None:
        lines = [
            formatters.syslog_line(r, self.config.get("hostname")) for r in records
        ]
        if self.config.get("protocol", "udp") == "tcp":
            # RFC 6587 non-transparent framing: one message per line.
            self._sendall("".join(f"{line}\n" for line in lines).encode("utf-8"))
            return
        address = (self.config["host"], self.config["port"])
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                for line in lines:
                    sock.sendto(line.encode("utf-8"), address)
        except OSError as error:
            raise SinkDeliveryError(
                f"sending to {address[0]}:{address[1]}/udp failed: {error}"
            ) from error


TRANSPORTS = {
    "splunk_hec": SplunkHecTransport,
    "gelf": GelfTransport,
    "syslog": SyslogTransport,
    "webhook": WebhookTransport,
}


def open_transport(sink_type: str, config: dict):
    return TRANSPORTS[sink_type](config)
