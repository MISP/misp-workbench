from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

EntryKind = Literal["value", "cidr", "suffix", "regex"]


class LocalWarninglist(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    enabled: bool
    entry_count: int = 0
    org_id: int
    # A plain list the entries are synced from (daily), and how it went.
    source_url: Optional[str] = None
    synced_at: Optional[datetime] = None
    sync_error: Optional[str] = None
    updated_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


class LocalWarninglistCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=2000)
    source_url: Optional[str] = Field(None, max_length=2000)
    # Admins only: another organisation's list.
    org_id: Optional[int] = None


class LocalWarninglistUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=2000)
    enabled: Optional[bool] = None
    source_url: Optional[str] = Field(None, max_length=2000)


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
