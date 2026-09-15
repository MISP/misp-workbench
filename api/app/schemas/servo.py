"""Pydantic models for Tech Lab transformation servos."""

import re
from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

# Pipelines shipped in ``opensearch/pipelines/`` all carry this prefix. A servo
# may never use it, so a servo can never shadow (or be mistaken for) one.
SYSTEM_PREFIX = "misp-"
SERVO_PREFIX = "servo_"

SLUG_RE = re.compile(r"^[a-z0-9]+(?:[_-][a-z0-9]+)*$")

PipelineKind = Literal["system", "servo", "external"]


def _validate_processors(value: list[Any]) -> list[dict]:
    if not value:
        raise ValueError("at least one processor is required")
    for index, processor in enumerate(value):
        if not isinstance(processor, dict):
            raise ValueError(f"processor {index} must be an object")
        if len(processor) != 1:
            raise ValueError(
                f"processor {index} must have exactly one key naming the "
                f"processor type, got {sorted(processor)}"
            )
    return value


class ServoBase(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: Optional[str] = None
    enabled: bool = True
    position: int = 0


class ServoCreate(ServoBase):
    slug: str = Field(min_length=1, max_length=200)
    processors: list[dict]

    @field_validator("slug")
    @classmethod
    def check_slug(cls, value: str) -> str:
        value = value.strip().lower()
        if value.startswith(SYSTEM_PREFIX):
            raise ValueError(
                f"'{SYSTEM_PREFIX}' is reserved for system pipelines shipped with "
                "misp-workbench; pick another slug"
            )
        if not SLUG_RE.match(value):
            raise ValueError(
                "slug must be lowercase alphanumerics separated by '-' or '_'"
            )
        return value

    @field_validator("processors")
    @classmethod
    def check_processors(cls, value: list[Any]) -> list[dict]:
        return _validate_processors(value)


class ServoUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    description: Optional[str] = None
    processors: Optional[list[dict]] = None
    enabled: Optional[bool] = None
    position: Optional[int] = None

    @field_validator("processors")
    @classmethod
    def check_processors(cls, value: Optional[list[Any]]) -> Optional[list[dict]]:
        if value is None:
            return None
        return _validate_processors(value)


class Servo(ServoBase):
    id: int
    user_id: int
    slug: str
    processors: list[dict]
    target_index: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    last_synced_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)

    @property
    def pipeline_name(self) -> str:
        return f"{SERVO_PREFIX}{self.slug}"


class ServoQueryParams(BaseModel):
    filter: Optional[str] = None


class PipelineSummary(BaseModel):
    """One entry of the cluster-wide ingest pipeline inventory."""

    name: str
    kind: PipelineKind
    description: Optional[str] = None
    processor_types: list[str] = Field(default_factory=list)
    processor_count: int = 0
    read_only: bool = True
    # OpenSearch keeps no modification time for pipelines, so this is only ever
    # set for servos, where the DB knows.
    updated_at: Optional[datetime] = None
    servo_id: Optional[int] = None
    enabled: Optional[bool] = None


class PipelineDetail(PipelineSummary):
    definition: dict


class ServoSimulateRequest(BaseModel):
    processors: list[dict]
    docs: Optional[list[dict]] = None
    attribute_uuids: Optional[list[str]] = None

    @field_validator("processors")
    @classmethod
    def check_processors(cls, value: list[Any]) -> list[dict]:
        return _validate_processors(value)


class ServoSimulateResponse(BaseModel):
    ok: bool
    docs: list[dict] = Field(default_factory=list)
    error: Optional[str] = None


class ServoTemplate(BaseModel):
    slug: str
    name: str
    # One line for the editor's template picker. `description` is the long
    # form, copied onto the servo when the template is applied.
    summary: str
    description: str
    processors: list[dict]
    sample_doc: dict = Field(default_factory=dict)
