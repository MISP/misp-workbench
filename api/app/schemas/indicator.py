from typing import Optional

from pydantic import BaseModel, Field


class IndicatorSource(BaseModel):
    # local, feed, server, or unknown (events from before sources were recorded)
    type: Optional[str] = None
    id: Optional[int] = None
    name: Optional[str] = None
    event_count: int = 0


class IndicatorOrganisation(BaseModel):
    id: Optional[int] = None
    name: str
    event_count: int = 0


class IndicatorSightings(BaseModel):
    positive: int = 0
    false_positive: int = 0
    expiration: int = 0
    first_at: Optional[int] = None
    last_at: Optional[int] = None
    last_positive_at: Optional[int] = None
    last_expiration_at: Optional[int] = None
    last_false_positive_at: Optional[int] = None


class ScoreComponent(BaseModel):
    """One step of a score: base, corroboration, decay, sightings, ..."""

    factor: str
    points: int
    detail: str


class IndicatorReviewState(BaseModel):
    """An analyst's decision, as the indicator carries it."""

    # approved, rejected or snoozed
    status: str
    # Snoozed until (epoch seconds).
    until: Optional[int] = None
    # Decided at (epoch seconds).
    at: Optional[int] = None


class Indicator(BaseModel):
    """One type + value, merged from every live attribute carrying it."""

    uuid: str
    type: str
    value: str
    categories: list[str] = []
    to_ids: bool = False
    deleted: bool = False
    attribute_count: int = 0
    ids_attribute_count: int = 0
    event_count: int = 0
    # Newest first, at most 50; event_count counts them all.
    events: list[str] = []
    first_seen: Optional[int] = None
    last_seen: Optional[int] = None
    sources: list[IndicatorSource] = []
    organisations: list[IndicatorOrganisation] = []
    # One key per source (feed:3, server:2, local), for queries such as
    # source_keys:"feed:3", and the organisations' ids.
    source_keys: list[str] = []
    source_count: int = 0
    organisation_ids: list[int] = []
    organisation_count: int = 0
    # Merged attribute and event tags, keeping only the most restrictive TLP.
    tags: list[str] = []
    tlp: Optional[str] = None
    galaxies: list[str] = []
    sightings: IndicatorSightings = IndicatorSightings()
    warninglist_hits: list[str] = []
    # Organisations' own warninglists it matches (ids); only the profiles
    # attaching one leave its matches out.
    local_list_hits: list[int] = []
    # Problems normalisation found on its attributes (private-ip, invalid-hash...).
    validation_issues: list[str] = []
    # Confidence, 0-100 (None when scoring is off), and how it was reached.
    score: Optional[int] = None
    score_breakdown: list[ScoreComponent] = []
    scored_at: Optional[int] = None
    # The review queue's decision on it; none while undecided.
    review: Optional[IndicatorReviewState] = None
    updated_at: Optional[int] = None


class IndicatorKey(BaseModel):
    type: str
    value: str


class ScoresRequest(BaseModel):
    attributes: list[IndicatorKey] = Field(..., max_length=1000)


class IndicatorScore(BaseModel):
    uuid: str
    score: Optional[int] = None
    score_breakdown: list[ScoreComponent] = []
    scored_at: Optional[int] = None


class ScoresResponse(BaseModel):
    # In request order; null where the type + value has no live indicator.
    scores: list[Optional[IndicatorScore]]


class SourceOverlap(BaseModel):
    key: str
    name: str
    indicators: int


class SourceQuality(BaseModel):
    """How good one source's (or organisation's) indicators are."""

    # feed:3, server:2, local, unknown; or the organisation's id.
    key: str
    kind: str
    id: Optional[int] = None
    name: str
    indicators: int
    # Reported by no other source; overlap_rate is the share that is.
    exclusive: int
    overlap_rate: float
    top_overlaps: list[SourceOverlap] = []
    # Shares of its indicators sighted / reported benign within the window.
    hit_rate: float
    false_positive_rate: float
    average_score: Optional[float] = None
    decayed_rate: float
    score_modifier: int = 0
    score_cap: Optional[int] = None
    # What adaptive trust takes off (shown even when it is off) and the
    # modifier scoring uses.
    adaptive_penalty: int = 0
    effective_modifier: int = 0


class SourceQualityReport(BaseModel):
    window_days: float
    adaptive_trust: bool
    sources: list[SourceQuality] = []
    organisations: list[SourceQuality] = []


class IndicatorPage(BaseModel):
    total: int
    page: int
    size: int
    items: list[Indicator]


class IndicatorsStatus(BaseModel):
    built: bool
    built_at: Optional[int] = None
    synced_at: Optional[int] = None
    indicators: int
    tombstones: int
    pending_sighted_values: int
    pending_events: int = 0
