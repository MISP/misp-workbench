from typing import Optional

from pydantic import BaseModel, Field


class IndicatorSource(BaseModel):
    # local, feed, server, or unknown (events from before sources were recorded)
    type: Optional[str] = None
    id: Optional[int] = None
    name: Optional[str] = None
    event_count: int = 0


class IndicatorOrganisation(BaseModel):
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


class ScoreComponent(BaseModel):
    """One step of a score: base, corroboration, decay, sightings, ..."""

    factor: str
    points: int
    detail: str


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
    # Merged attribute and event tags, keeping only the most restrictive TLP.
    tags: list[str] = []
    tlp: Optional[str] = None
    galaxies: list[str] = []
    sightings: IndicatorSightings = IndicatorSightings()
    warninglist_hits: list[str] = []
    # Confidence, 0-100 (None when scoring is off), and how it was reached.
    score: Optional[int] = None
    score_breakdown: list[ScoreComponent] = []
    scored_at: Optional[int] = None
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
