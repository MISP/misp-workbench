from typing import Any, Optional
from pydantic import BaseModel


# ── Query parameter schemas ───────────────────────────────────────────────────

class CorrelationQueryParams(BaseModel):
    source_attribute_uuid: Optional[str] = None
    source_event_uuid: Optional[str] = None
    target_attribute_uuid: Optional[str] = None
    target_event_uuid: Optional[str] = None
    match_type: Optional[str] = None


# ── Response schemas ──────────────────────────────────────────────────────────

class CorrelationListResponse(BaseModel):
    page: int
    size: int
    total: int
    took: int
    timed_out: bool
    max_score: Optional[float] = None
    results: list[dict[str, Any]]


class CorrelationEventBucket(BaseModel):
    key: str
    doc_count: int


class CorrelationAttributeTopHit(BaseModel):
    target_attribute_type: Optional[str] = None
    target_attribute_value: Optional[str] = None
    target_event_uuid: Optional[str] = None


class CorrelationAttributeBucket(BaseModel):
    key: str
    doc_count: int
    top_attribute_info: Optional[dict[str, Any]] = None


class CorrelationStatsResponse(BaseModel):
    top_correlated_events: list[dict[str, Any]]
    top_correlated_attributes: list[dict[str, Any]]
    total_correlations: int


class CorrelationDeleteResponse(BaseModel):
    message: str
