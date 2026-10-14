import ipaddress
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator

# Expressions are short; anything longer is a mistake or an attack on the parser.
MAX_EXPRESSION = 2000


class AlertMapping(BaseModel):
    """Where an alert's parts are, as JMESPath expressions.

    ``records`` picks the alerts out of a request (``@``: the body itself,
    or each element when it is an array); the others are read from each
    record, and ``root()`` reaches back to the whole body.
    """

    records: str = Field("@", min_length=1, max_length=MAX_EXPRESSION)
    # The values the alert hit: a string, or arrays of them, nested or not.
    values: str = Field(min_length=1, max_length=MAX_EXPRESSION)
    # positive, false-positive or expiration (MISP's 0, 1, 2); empty: positive.
    type: Optional[str] = Field(None, max_length=MAX_EXPRESSION)
    # The sensor or rule that raised it; empty: the receiver's name.
    source: Optional[str] = Field(None, max_length=MAX_EXPRESSION)
    # Epoch seconds or milliseconds, or ISO 8601; empty: when it arrived.
    timestamp: Optional[str] = Field(None, max_length=MAX_EXPRESSION)
    # An attribute's uuid: the record sights that attribute.
    attribute_uuid: Optional[str] = Field(None, max_length=MAX_EXPRESSION)

    @field_validator("*")
    @classmethod
    def _compiles(cls, value: Optional[str], info: ValidationInfo) -> Optional[str]:
        from app.repositories.alert_receivers import compile_expression

        if value is None or not value.strip():
            if info.field_name in ("records", "values"):
                raise ValueError(f"{info.field_name} can't be empty")
            return None
        compile_expression(value.strip())
        return value.strip()


def _networks(values: list[str]) -> list[str]:
    cleaned = []
    for value in values:
        try:
            cleaned.append(str(ipaddress.ip_network(value.strip(), strict=False)))
        except ValueError:
            raise ValueError(f"{value!r} is not an address or network")
    return cleaned


class AlertReceiverBase(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: Optional[str] = None
    preset: str = "generic"
    only_known: bool = True
    rate_limit: int = Field(120, ge=1, le=10_000)
    enabled: bool = True
    allowed_ips: list[str] = Field([], max_length=100)

    @field_validator("allowed_ips")
    @classmethod
    def _allowed(cls, values: list[str]) -> list[str]:
        return _networks(values)


class AlertReceiverCreate(AlertReceiverBase):
    # Empty: the preset's.
    mapping: Optional[AlertMapping] = None


class AlertReceiverUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    preset: Optional[str] = None
    mapping: Optional[AlertMapping] = None
    only_known: Optional[bool] = None
    rate_limit: Optional[int] = Field(None, ge=1, le=10_000)
    enabled: Optional[bool] = None
    allowed_ips: Optional[list[str]] = Field(None, max_length=100)

    @field_validator("allowed_ips")
    @classmethod
    def _allowed(cls, values: Optional[list[str]]) -> Optional[list[str]]:
        return None if values is None else _networks(values)


class AlertReceiver(AlertReceiverBase):
    id: int
    org_id: int
    mapping: AlertMapping
    token_prefix: str
    last_received_at: Optional[datetime] = None
    last_ip: Optional[str] = None
    received_count: int = 0
    sightings_count: int = 0
    last_error: Optional[str] = None
    last_error_at: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


class AlertReceiverCreated(AlertReceiver):
    # Shown once: only its hash is kept.
    token: str
    # Where alerts are posted with it, relative to the API's base URL.
    path: str


class AlertPreset(BaseModel):
    preset: str
    name: str
    mapping: AlertMapping
    # How to point the sender at the receiver.
    setup: str
    # A body as the sender posts it, to try the mapping on.
    sample: Any


class LastPayload(BaseModel):
    received_at: Optional[datetime] = None
    payload: Optional[str] = None


class MappingTest(BaseModel):
    mapping: AlertMapping
    only_known: bool = True
    # The body to map, as the sender posts it.
    payload: Any
    # The source when the mapping reads none: the receiver's name.
    name: str = Field("this receiver", max_length=255)


class MappedSighting(BaseModel):
    value: str
    type: str
    source: str
    timestamp: float
    attribute_uuid: Optional[str] = None
    # Whether some attribute holds the value (only_known reports these only).
    known: bool = False


class MappingResult(BaseModel):
    records: int = 0
    sightings: list[MappedSighting] = []
    # Values read but left out: unknown ones, when only_known.
    skipped: int = 0
    error: Optional[str] = None


class AlertAccepted(BaseModel):
    records: int
    sightings: int
    skipped: int
