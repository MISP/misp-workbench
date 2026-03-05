from typing import Any, Optional
from pydantic import BaseModel


# ── Query parameter schemas ───────────────────────────────────────────────────

class SightingQueryParams(BaseModel):
    attribute_uuid: Optional[str] = None
    type: Optional[str] = None


class SightingActivityParams(BaseModel):
    value: str
    period: str = "7d"
    interval: str = "1h"


# ── Request schemas ───────────────────────────────────────────────────────────

class SightingCreate(BaseModel):
    value: str
    type: str = "positive"
    timestamp: Optional[float] = None
    attribute_uuid: Optional[str] = None
    observer: Optional[dict[str, Any]] = None


# ── Response schemas ──────────────────────────────────────────────────────────

class SightingListResponse(BaseModel):
    page: int
    size: int
    total: int
    took: int
    timed_out: bool
    max_score: Optional[float] = None
    results: list[dict[str, Any]]


class SightingCreateResponse(BaseModel):
    result: str
    response: Optional[Any] = None


class SightingHistogramBucket(BaseModel):
    key_as_string: str
    key: int
    doc_count: int


class SightingHistogramAggregation(BaseModel):
    buckets: list[SightingHistogramBucket]


class SightingHistogramResponse(BaseModel):
    sightings_over_time: SightingHistogramAggregation


class SightingStatsResponse(BaseModel):
    total: int
    previous_total: int
