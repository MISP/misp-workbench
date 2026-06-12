from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, model_validator

from app.schemas.task import ScheduleTaskSchedule

ExportFormat = Literal["json", "csv", "stix", "misp"]
ExportIndexTarget = Literal["attributes", "events"]
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


class ExportCreate(ExportBase):
    schedule: Optional[ScheduleTaskSchedule] = None
    schedule_enabled: bool = False

    @model_validator(mode="after")
    def _require_distribution_for_misp(self):
        if self.format == "misp" and self.distribution is None:
            raise ValueError("distribution is required for MISP-format exports")
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
    created_at: datetime
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)
