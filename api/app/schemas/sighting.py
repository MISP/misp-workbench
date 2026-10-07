from typing import Any, Optional
from pydantic import BaseModel, ConfigDict


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


class MispSightingAdd(BaseModel):
    """MISP's ``/sightings/add`` body: what PyMISP and SIEM connectors send.

    Sightings target a value (``value``/``values``) or an attribute
    (``uuid``/``id``, or the URL's attribute id). ``type`` is MISP's 0
    (sighting), 1 (false positive) or 2 (expiration); names are accepted too.
    """

    value: Optional[str] = None
    values: Optional[list[str]] = None
    uuid: Optional[str] = None
    id: Optional[str] = None
    type: Optional[Any] = 0
    source: Optional[str] = None
    timestamp: Optional[float] = None
    model_config = ConfigDict(extra="allow")


class MispSightingAddResponse(BaseModel):
    saved: bool
    success: bool
    name: str
    message: str
    url: str


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
