from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

SinkType = Literal["splunk_hec", "gelf", "syslog", "webhook"]

# What secrets read back as. Sending it back unchanged on update keeps the
# stored secret, so an edit form can round-trip a sink without knowing it.
SECRET_MASK = "********"


def _http_url(value: str) -> str:
    if not value.startswith(("http://", "https://")):
        raise ValueError("must be an http:// or https:// URL")
    return value


class SplunkHecConfig(BaseModel):
    # e.g. https://splunk.example.com:8088/services/collector/event
    url: str
    token: str
    index: Optional[str] = None
    sourcetype: str = "misp:attribute"
    source: str = "misp-workbench"
    verify_tls: bool = True
    # PEM CA certificate to verify a self-signed endpoint against, rather than
    # turning verification off.
    ca_cert: Optional[str] = None

    _check_url = field_validator("url")(_http_url)


class GelfConfig(BaseModel):
    """GELF over TCP (null-byte framed), the transport that suits batches."""

    host: str
    port: int = Field(12201, ge=1, le=65535)
    tls: bool = False
    verify_tls: bool = True
    ca_cert: Optional[str] = None


class SyslogConfig(BaseModel):
    """CEF messages in RFC 5424 syslog envelopes."""

    host: str
    port: int = Field(514, ge=1, le=65535)
    protocol: Literal["udp", "tcp"] = "udp"
    tls: bool = False
    verify_tls: bool = True
    ca_cert: Optional[str] = None
    # HOSTNAME field of the syslog header.
    hostname: str = "misp-workbench"

    @model_validator(mode="after")
    def _tls_needs_tcp(self):
        if self.tls and self.protocol != "tcp":
            raise ValueError("TLS needs protocol tcp")
        return self


class WebhookConfig(BaseModel):
    url: str
    # When set, each request is signed: X-Misp-Workbench-Signature: sha256=<hmac>.
    secret: Optional[str] = None
    verify_tls: bool = True
    ca_cert: Optional[str] = None

    _check_url = field_validator("url")(_http_url)


CONFIG_MODELS: dict[str, type[BaseModel]] = {
    "splunk_hec": SplunkHecConfig,
    "gelf": GelfConfig,
    "syslog": SyslogConfig,
    "webhook": WebhookConfig,
}

# Config fields holding credentials, masked on read.
SECRET_FIELDS: dict[str, tuple[str, ...]] = {
    "splunk_hec": ("token",),
    "webhook": ("secret",),
}


class SinkFilters(BaseModel):
    """Which attributes of a published event are sent.

    Tag patterns are shell-style (``tlp:*``) and match attribute tags and the
    event's tags alike.
    """

    to_ids_only: bool = True
    # Attribute types to send; empty means all.
    types: list[str] = []
    # Send only attributes carrying at least one of these tags; empty means all.
    tags: list[str] = []
    # Never send attributes carrying any of these tags.
    exclude_tags: list[str] = ["tlp:red"]


def validate_config(sink_type: str, config: dict) -> dict:
    return CONFIG_MODELS[sink_type].model_validate(config).model_dump()


class SinkBase(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    type: SinkType
    enabled: bool = True
    config: dict
    filters: SinkFilters = SinkFilters()


class SinkCreate(SinkBase):
    @model_validator(mode="after")
    def _validate_config(self):
        self.config = validate_config(self.type, self.config)
        return self


class SinkUpdate(BaseModel):
    # The type is fixed at creation: its config would no longer fit.
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    enabled: Optional[bool] = None
    config: Optional[dict] = None
    filters: Optional[SinkFilters] = None


class Sink(SinkBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    last_attempt_at: Optional[datetime] = None
    last_success_at: Optional[datetime] = None
    last_error: Optional[str] = None
    last_error_at: Optional[datetime] = None
    delivered_count: int = 0
    failed_count: int = 0
    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode="after")
    def _mask_secrets(self):
        config = dict(self.config or {})
        for field in SECRET_FIELDS.get(self.type, ()):
            if config.get(field):
                config[field] = SECRET_MASK
        self.config = config
        return self


class SinkTestResult(BaseModel):
    ok: bool
    error: Optional[str] = None


class SinkDeliveryQueued(BaseModel):
    task_id: str
