import ipaddress
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

ListType = Literal["ip", "domain", "url", "hash"]
Vendor = Literal["paloalto", "fortinet", "checkpoint", "cisco", "squid", "plain"]

# The most entries any list holds, whatever its vendor.
MAX_ENTRIES = 1_000_000


class VendorInfo(BaseModel):
    vendor: Vendor
    name: str
    # The list types it takes, and its size limit by default (None: none).
    list_types: list[ListType]
    max_entries: Optional[int] = None


def check_vendor(vendor: str, list_type: str) -> None:
    from app.repositories import edls

    if list_type not in edls.VENDORS[vendor]["list_types"]:
        raise ValueError(
            f"{edls.VENDORS[vendor]['name']} takes no {list_type} list: "
            + ", ".join(edls.VENDORS[vendor]["list_types"])
        )


class EdlBase(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: Optional[str] = None
    # The detection profile whose indicators it lists.
    profile_id: int
    list_type: ListType
    vendor: Vendor = "plain"
    # At most this many entries, the highest scored. None: the vendor's limit.
    max_entries: Optional[int] = Field(None, ge=1, le=MAX_ENTRIES)
    # Domains also cover their subdomains (*.example.com, .example.com for
    # Squid), where the vendor's format can say so.
    include_subdomains: bool = False
    refresh_minutes: int = Field(15, ge=1, le=7 * 24 * 60)
    enabled: bool = True


class EdlCreate(EdlBase):
    @model_validator(mode="after")
    def _vendor_takes_it(self):
        check_vendor(self.vendor, self.list_type)
        return self


class EdlUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    profile_id: Optional[int] = None
    list_type: Optional[ListType] = None
    vendor: Optional[Vendor] = None
    max_entries: Optional[int] = Field(None, ge=1, le=MAX_ENTRIES)
    include_subdomains: Optional[bool] = None
    refresh_minutes: Optional[int] = Field(None, ge=1, le=7 * 24 * 60)
    enabled: Optional[bool] = None


class Edl(EdlBase):
    id: int
    org_id: int
    entry_count: Optional[int] = None
    truncated: Optional[int] = None
    checksum: Optional[str] = None
    built_at: Optional[datetime] = None
    build_error: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    # Tokens neither revoked nor expired.
    active_tokens: int = 0
    model_config = ConfigDict(from_attributes=True)


class EdlPreview(BaseModel):
    """The first lines of the list as served."""

    lines: list[str] = []
    entry_count: int = 0
    truncated: int = 0
    built_at: Optional[datetime] = None


class EdlTokenCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    expires_at: Optional[datetime] = None
    # Addresses or networks (192.0.2.10, 198.51.100.0/24) it may be used
    # from; empty: anywhere.
    allowed_ips: list[str] = Field([], max_length=100)

    @field_validator("allowed_ips")
    @classmethod
    def _networks(cls, values: list[str]) -> list[str]:
        cleaned = []
        for value in values:
            try:
                cleaned.append(str(ipaddress.ip_network(value.strip(), strict=False)))
            except ValueError:
                raise ValueError(f"{value!r} is not an address or network")
        return cleaned

    @field_validator("expires_at")
    @classmethod
    def _future(cls, value: Optional[datetime]) -> Optional[datetime]:
        from datetime import timezone

        if value is not None:
            if value.tzinfo is None:
                value = value.replace(tzinfo=timezone.utc)
            if value <= datetime.now(timezone.utc):
                raise ValueError("expires_at is in the past")
        return value


class EdlToken(BaseModel):
    id: int
    edl_id: int
    name: str
    prefix: str
    allowed_ips: list[str] = []
    expires_at: Optional[datetime] = None
    revoked_at: Optional[datetime] = None
    last_used_at: Optional[datetime] = None
    last_used_ip: Optional[str] = None
    use_count: int = 0
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class EdlTokenCreated(EdlToken):
    # Shown once: only its hash is kept.
    token: str
    # Where the list is served with it, relative to the API's base URL.
    path: str
