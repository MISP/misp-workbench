from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

Granularity = Literal["indicators", "attributes"]
Tlp = Literal["tlp:clear", "tlp:green", "tlp:amber", "tlp:amber+strict", "tlp:red"]


class ProfileRules(BaseModel):
    """Which consolidated indicators a profile selects. Every rule narrows.

    Empty lists and None leave a rule out.
    """

    model_config = ConfigDict(extra="forbid")

    # Attribute types and categories (any of).
    types: list[str] = []
    categories: list[str] = []
    # The most restrictive TLP let through: tlp:amber keeps clear, green and
    # amber, and leaves out amber+strict and red. Indicators without a TLP
    # are kept.
    tlp_ceiling: Optional[Tlp] = None
    # Tags, shell-style patterns (misp-galaxy:threat-actor=*): keep indicators
    # with at least one of tags, leave out those with any of exclude_tags.
    tags: list[str] = []
    exclude_tags: list[str] = []
    min_score: Optional[int] = Field(None, ge=0, le=100)
    # Last seen at most this many days ago.
    max_age_days: Optional[int] = Field(None, ge=1)
    # Source keys (feed:3, server:2, local, unknown): keep indicators reported
    # by one of sources; leave out those reported *only* by excluded ones (a
    # value a noisy feed and a trusted partner both report stays).
    sources: list[str] = []
    exclude_sources: list[str] = []
    # Organisation ids, the same way.
    organisations: list[int] = []
    exclude_organisations: list[int] = []
    # Keep indicators with at least one source (feed or server) whose score
    # modifier is at least this; local and unknown sources count as 0.
    min_source_trust: Optional[int] = Field(None, ge=-100, le=100)
    # Only indicators with at least one attribute flagged for IDS.
    to_ids: bool = True
    exclude_warninglisted: bool = True
    exclude_validation_issues: bool = True
    # The review queue: only indicators approved by an analyst or by an
    # auto-approve profile (require_approval), or everything but those an
    # analyst rejected (exclude_rejected). Requiring approval leaves rejected
    # ones out too.
    require_approval: bool = False
    exclude_rejected: bool = False

    @field_validator("sources", "exclude_sources")
    @classmethod
    def _source_keys(cls, keys: list[str]) -> list[str]:
        for key in keys:
            kind, _, ident = key.partition(":")
            if key in ("local", "unknown"):
                continue
            if kind not in ("feed", "server") or not ident.isdigit():
                raise ValueError(
                    f"{key!r} is not a source key (feed:<id>, server:<id>, local, unknown)"
                )
        return keys

    @field_validator("types", "categories", "tags", "exclude_tags")
    @classmethod
    def _non_empty(cls, values: list[str]) -> list[str]:
        cleaned = [v.strip() for v in values]
        if any(not v for v in cleaned):
            raise ValueError("entries can't be empty")
        return cleaned


RiskFlag = Literal[
    "popular_domain",
    "shared_infrastructure",
    "warninglisted",
    "new_source",
    "low_score",
]


class ProfileGate(BaseModel):
    """When a run's changes wait for approval instead of going out.

    Changes are what the profile selects now against what it last released.
    """

    model_config = ConfigDict(extra="forbid")

    enabled: bool = False
    # Hold a run adding or removing more than this many indicators.
    max_additions: Optional[int] = Field(None, ge=0)
    max_removals: Optional[int] = Field(None, ge=0)
    # Hold a run with any addition flagged so.
    hold_on_risk: list[RiskFlag] = []
    # Hold a run adding this many times its usual (the median of the last
    # runs), from 20 additions up.
    spike_factor: Optional[float] = Field(None, ge=1.5, le=100)
    # What counts as a low score, and a very new source (days since added).
    low_score: int = Field(40, ge=0, le=100)
    new_source_days: int = Field(7, ge=1, le=365)


class DetectionProfileBase(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: Optional[str] = None
    granularity: Granularity = "indicators"
    rules: ProfileRules = ProfileRules()
    # What this profile selects is approved without a review.
    auto_approve: bool = False
    gate: Optional[ProfileGate] = None

    @model_validator(mode="after")
    def _not_circular(self):
        check_auto_approve(self.auto_approve, self.rules)
        return self


def check_auto_approve(auto_approve: bool, rules: Optional[ProfileRules]) -> None:
    """An auto-approve profile can't itself require approval: it would only
    approve what is approved already."""
    if auto_approve and rules is not None and rules.require_approval:
        raise ValueError("an auto-approve profile can't require approval")


class DetectionProfileCreate(DetectionProfileBase):
    pass


class DetectionProfileUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    granularity: Optional[Granularity] = None
    rules: Optional[ProfileRules] = None
    auto_approve: Optional[bool] = None
    gate: Optional[ProfileGate] = None


class DetectionProfile(DetectionProfileBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    # Changes are held back from its outputs, waiting for approval.
    held: bool = False
    model_config = ConfigDict(from_attributes=True)


class ProfilePreviewRequest(BaseModel):
    rules: ProfileRules


class ProfileQuery(BaseModel):
    """The rules as a Lucene query on the indicators index (Explore)."""

    query: str
    # Some rules (sources and organisations to leave out, source trust) are
    # written listing the sources present now: ones added later aren't
    # covered by this query, though they are by the profile.
    snapshot: bool = False


class ProfilePreview(BaseModel):
    """How many live indicators the rules select, and a few of them."""

    count: int
    sample: list[dict] = []


class SourceCount(BaseModel):
    key: str
    name: str
    count: int


class ChangeSample(BaseModel):
    uuid: str
    type: Optional[str] = None
    value: Optional[str] = None
    score: Optional[int] = None
    # Why it is flagged, or why it leaves.
    detail: Optional[str] = None


class RiskSummary(BaseModel):
    count: int = 0
    sample: list[ChangeSample] = []


class ChangeSummary(BaseModel):
    """What a profile's next run changes, against its last release."""

    # Nothing released yet: the next run sets the baseline.
    first: bool = False
    members: int = 0
    previous_members: int = 0
    added: int = 0
    removed: int = 0
    added_by_type: dict[str, int] = {}
    added_by_source: list[SourceCount] = []
    removed_by_type: dict[str, int] = {}
    removed_by_reason: dict[str, int] = {}
    risks: dict[str, RiskSummary] = {}
    added_sample: list[ChangeSample] = []
    removed_sample: list[ChangeSample] = []
    # The median additions of the last runs that changed something.
    usual_added: Optional[float] = None


class ProfileRelease(BaseModel):
    id: int
    status: str
    members: int
    added: int
    removed: int
    reasons: list[str] = []
    user_email: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None


class ProfileConsumer(BaseModel):
    kind: str
    id: int
    name: str
    # export: its last status; sink: whether it keeps in step (gated) or
    # sends published events (not gated).
    status: Optional[str] = None
    gated: bool = True


class ChangePreview(BaseModel):
    generated_at: datetime
    # Name it to approve these changes, and no others.
    fingerprint: str
    gate: ProfileGate
    # Changes are held back from its outputs, waiting for approval.
    held: bool = False
    held_since: Optional[datetime] = None
    # Why the next run holds changes back (empty: everything goes out), and
    # how many additions and removals it holds.
    reasons: list[str] = []
    held_added: int = 0
    held_removed: int = 0
    changes: ChangeSummary
    releases: list[ProfileRelease] = []
    consumers: list[ProfileConsumer] = []


class ApproveChangesRequest(BaseModel):
    # The fingerprint of the previewed changes being approved.
    fingerprint: str = Field(min_length=64, max_length=64)


class ChangePreviewRequest(BaseModel):
    """Rules to preview instead of the profile's own (a dry run of an edit)."""

    rules: Optional[ProfileRules] = None
