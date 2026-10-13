from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

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


class DetectionProfileBase(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: Optional[str] = None
    granularity: Granularity = "indicators"
    rules: ProfileRules = ProfileRules()


class DetectionProfileCreate(DetectionProfileBase):
    pass


class DetectionProfileUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    granularity: Optional[Granularity] = None
    rules: Optional[ProfileRules] = None


class DetectionProfile(DetectionProfileBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


class ProfilePreviewRequest(BaseModel):
    rules: ProfileRules


class ProfilePreview(BaseModel):
    """How many live indicators the rules select, and a few of them."""

    count: int
    sample: list[dict] = []
