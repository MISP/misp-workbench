from datetime import datetime
from typing import Annotated, Literal, Optional

from pydantic import AfterValidator, BaseModel, ConfigDict, Field

from app.models.warninglist import (
    SYNC_EVERY_DEFAULT,
    SYNC_EVERY_MAX,
    SYNC_EVERY_MIN,
)

EntryKind = Literal["value", "cidr", "suffix", "regex"]


def _check_sync_every(minutes: Optional[int]) -> int:
    if not minutes:
        return 0
    if not SYNC_EVERY_MIN <= minutes <= SYNC_EVERY_MAX:
        raise ValueError(
            f"a list syncs every {SYNC_EVERY_MIN} to {SYNC_EVERY_MAX} minutes "
            "(30 days), or 0 for manual syncs only"
        )
    return minutes


# Minutes between syncs from the source URL; 0 (or null): manual only.
SyncEvery = Annotated[Optional[int], AfterValidator(_check_sync_every)]


class LocalWarninglist(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    enabled: bool
    entry_count: int = 0
    org_id: int
    # A plain list the entries are synced from, how often (minutes, 0 for
    # manual syncs only), how the last sync went and when the next one is
    # (later after failures in a row; null when manual or not synced yet).
    source_url: Optional[str] = None
    sync_every_minutes: int = SYNC_EVERY_DEFAULT
    synced_at: Optional[datetime] = None
    sync_error: Optional[str] = None
    next_sync_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


class LocalWarninglistCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=2000)
    source_url: Optional[str] = Field(None, max_length=2000)
    sync_every_minutes: SyncEvery = SYNC_EVERY_DEFAULT
    # Admins only: another organisation's list.
    org_id: Optional[int] = None


class LocalWarninglistUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=2000)
    enabled: Optional[bool] = None
    source_url: Optional[str] = Field(None, max_length=2000)
    sync_every_minutes: SyncEvery = None


class EntryIn(BaseModel):
    value: str = Field(min_length=1, max_length=2048)
    # Guessed from the value when left out: /…/ a regex, *.x a domain
    # suffix, a.b.c.d/n a CIDR, anything else an exact value.
    kind: Optional[EntryKind] = None
    comment: Optional[str] = Field(None, max_length=1000)
    expires_at: Optional[datetime] = None


class EntriesRequest(BaseModel):
    entries: list[EntryIn] = Field(..., min_length=1, max_length=10_000)


class EntryIds(BaseModel):
    ids: list[int] = Field(..., min_length=1, max_length=10_000)


class ImportRequest(BaseModel):
    # One entry per line, "entry  # comment"; "#" lines are skipped.
    text: str = Field(..., max_length=5 * 1024 * 1024)
    # Drop the imported entries no longer in the text.
    replace: bool = False


class Entry(BaseModel):
    id: int
    kind: str
    value: str
    comment: Optional[str] = None
    expires_at: Optional[datetime] = None
    origin: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class EntryPage(BaseModel):
    total: int
    page: int
    size: int
    items: list[Entry]


class EntriesChanged(BaseModel):
    added: int = 0
    updated: int = 0
    removed: int = 0


class SyncSources(BaseModel):
    # Hosts lists may sync from (exact names or *.domain), as an admin
    # allowed them (runtime setting warninglists.source_hosts).
    hosts: list[str] = []


class HitsRequest(BaseModel):
    indicators: list[str] = Field(..., min_length=1, max_length=1000)


class HitsResponse(BaseModel):
    # indicator uuid -> the ids of your organisation's lists it is on.
    hits: dict[str, list[int]]


class ExplainRequest(BaseModel):
    values: list[str] = Field(..., min_length=1, max_length=1000)
    type: Optional[str] = None


class EntryMatch(BaseModel):
    list_id: int
    list_name: str
    entry_id: int
    kind: str
    entry: str
    comment: Optional[str] = None
    expires_at: Optional[datetime] = None


class ExplainResponse(BaseModel):
    # value -> the entries of your organisation's lists it matches.
    matches: dict[str, list[EntryMatch]]
