from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict

ExportFormat = Literal["json", "csv", "stix"]
ExportIndexTarget = Literal["attributes", "events"]
ExportStatus = Literal["queued", "running", "completed", "failed"]


class ExportQueryParams(BaseModel):
    filter: Optional[str] = None


class ExportBase(BaseModel):
    name: str
    query: str
    index_target: ExportIndexTarget = "attributes"
    format: ExportFormat = "json"


class ExportCreate(ExportBase):
    pass


class Export(ExportBase):
    id: int
    user_id: int
    status: ExportStatus
    storage_key: Optional[str] = None
    file_size: Optional[int] = None
    record_count: Optional[int] = None
    error: Optional[str] = None
    celery_task_id: Optional[str] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)
