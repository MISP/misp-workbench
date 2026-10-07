from typing import Any, Optional

from pydantic import BaseModel, Field


class LookupRequest(BaseModel):
    values: list[str] = Field(..., description="Values to check, up to 10,000")
    to_ids_only: bool = Field(
        True,
        description=(
            "Only IDS attributes count as matches (uses the Redis prefilter). "
            "False matches any live attribute and asks OpenSearch about every value."
        ),
    )
    max_attributes: int = Field(
        10, ge=1, le=100, description="Attributes returned per matched value"
    )


class LookupEvent(BaseModel):
    uuid: Optional[str] = None
    info: Optional[str] = None
    threat_level_id: Optional[int] = None
    published: Optional[bool] = None
    org: Optional[str] = None
    tags: list[str] = []


class LookupAttribute(BaseModel):
    uuid: Optional[str] = None
    type: Optional[str] = None
    category: Optional[str] = None
    to_ids: bool = False
    comment: str = ""
    timestamp: Optional[int] = None
    first_seen: Optional[Any] = None
    last_seen: Optional[Any] = None
    tags: list[str] = []
    event: LookupEvent


class LookupMatch(BaseModel):
    value: str
    attribute_count: int
    attributes: list[LookupAttribute]


class LookupResponse(BaseModel):
    checked: int
    matched: int
    candidates: int
    source: str
    took_ms: float
    matches: list[LookupMatch]


class SingleLookupResponse(BaseModel):
    value: str
    match: bool
    attribute_count: int = 0
    attributes: list[LookupAttribute] = []


class LookupCacheStatus(BaseModel):
    built: bool
    built_at: Optional[int] = None
    synced_at: Optional[int] = None
    values: int
