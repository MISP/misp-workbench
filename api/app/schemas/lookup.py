from typing import Any, Optional

from pydantic import BaseModel, Field

from app.schemas.indicator import Indicator


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
    include_warninglisted: bool = Field(
        False,
        description="Also match attributes on an enabled warninglist (left out by default)",
    )
    min_score: Optional[int] = Field(
        None,
        ge=0,
        le=100,
        description=(
            "Leave out values whose consolidated indicator scores below this "
            "(0-100). Values too new to have an indicator are kept"
        ),
    )
    profile: Optional[str] = Field(
        None,
        description=(
            "Only values a detection profile (id or name) selects: their "
            "indicator, or for a value too new to have one its attribute, passes"
        ),
    )
    include_indicators: bool = Field(
        False,
        description=(
            "Add each matched value's consolidated indicators: one per type, "
            "with sources, seen dates, merged tags and sightings across events"
        ),
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
    warninglist_hits: list[str] = []
    event: LookupEvent


class LookupMatch(BaseModel):
    value: str
    attribute_count: int
    attributes: list[LookupAttribute]
    # The best confidence among the value's indicators, when asked for.
    score: Optional[int] = None
    indicators: list[Indicator] = []


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
    score: Optional[int] = None
    indicators: list[Indicator] = []


class LookupCacheStatus(BaseModel):
    built: bool
    built_at: Optional[int] = None
    synced_at: Optional[int] = None
    values: int
    intact: bool
