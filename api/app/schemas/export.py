from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, model_validator

from app.schemas.task import ScheduleTaskSchedule

ExportFormat = Literal["json", "csv", "stix", "misp", "ndjson", "text", "cdb"]

# Streamed straight out of OpenSearch into storage, without the in-memory
# record cap the other formats need.
STREAMED_FORMATS = ("ndjson", "text", "cdb")
# One value per line: only meaningful for attributes.
ATTRIBUTE_ONLY_FORMATS = ("text", "cdb")
# Deltas carry deletions as tombstones, which needs a structured record.
INCREMENTAL_FORMATS = ("ndjson",)
ExportIndexTarget = Literal["attributes", "events", "indicators"]
# Indicators are written by the streamed exporter only.
INDICATOR_FORMATS = STREAMED_FORMATS
ExportStatus = Literal["queued", "running", "completed", "failed"]


class ExportQueryParams(BaseModel):
    filter: Optional[str] = None


class ExportBase(BaseModel):
    name: str
    query: str
    index_target: ExportIndexTarget = "attributes"
    format: ExportFormat = "json"
    # Event distribution level (0–4) — required for MISP-format exports.
    distribution: Optional[int] = None
    # Also write a delta of what changed since the previous run on every run.
    incremental: bool = False
    # A detection profile selecting what the export holds (combined with
    # query; "*" for all of it). Its granularity decides between indicators
    # and attributes, in place of index_target.
    profile_id: Optional[int] = None


class ExportCreate(ExportBase):
    schedule: Optional[ScheduleTaskSchedule] = None
    schedule_enabled: bool = False

    @model_validator(mode="after")
    def _require_distribution_for_misp(self):
        if self.format == "misp" and self.distribution is None:
            raise ValueError("distribution is required for MISP-format exports")
        return self

    @model_validator(mode="after")
    def _check_profile_format(self):
        if self.profile_id is not None and self.format not in STREAMED_FORMATS:
            raise ValueError(
                "profile exports are available as " + ", ".join(STREAMED_FORMATS)
            )
        return self

    @model_validator(mode="after")
    def _check_format_target(self):
        if self.format in ATTRIBUTE_ONLY_FORMATS and self.index_target == "events":
            raise ValueError(
                f"{self.format} exports are only available for attributes and indicators"
            )
        if self.index_target == "indicators" and self.format not in INDICATOR_FORMATS:
            raise ValueError(
                "indicator exports are available as " + ", ".join(INDICATOR_FORMATS)
            )
        if self.incremental:
            if self.format not in INCREMENTAL_FORMATS:
                raise ValueError(
                    "incremental exports need a format that can carry deletions: "
                    + ", ".join(INCREMENTAL_FORMATS)
                )
            # Deltas key off updated_at, which events aren't stamped with.
            if self.index_target == "events":
                raise ValueError(
                    "incremental exports are only available for attributes and indicators"
                )
        return self


class ExportScheduleUpdate(BaseModel):
    # ``schedule=None`` clears the schedule (unschedule). ``schedule_enabled``
    # toggles pause/resume without changing the cadence.
    schedule: Optional[ScheduleTaskSchedule] = None
    schedule_enabled: Optional[bool] = None


class Export(ExportBase):
    id: int
    user_id: int
    status: ExportStatus
    storage_key: Optional[str] = None
    file_size: Optional[int] = None
    record_count: Optional[int] = None
    error: Optional[str] = None
    celery_task_id: Optional[str] = None
    schedule: Optional[ScheduleTaskSchedule] = None
    schedule_enabled: bool = False
    scheduled_task_name: Optional[str] = None
    last_run_at: Optional[datetime] = None
    checksum: Optional[str] = None
    cursor: Optional[int] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)
