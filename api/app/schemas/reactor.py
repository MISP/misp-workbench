from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

ReactorResourceType = Literal[
    "event", "attribute", "object", "correlation", "sighting"
]
ReactorAction = Literal[
    "created", "updated", "deleted", "published", "unpublished"
]
ReactorScriptStatus = Literal["active", "paused"]
ReactorRunStatus = Literal[
    "queued", "running", "success", "failed", "timed_out"
]


class ReactorTrigger(BaseModel):
    resource_type: ReactorResourceType
    action: ReactorAction
    filters: Optional[dict[str, Any]] = None


class ReactorScriptBase(BaseModel):
    name: str
    description: Optional[str] = None
    entrypoint: str = "handle"
    triggers: list[ReactorTrigger] = Field(default_factory=list)
    status: ReactorScriptStatus = "active"
    timeout_seconds: int = 60
    max_writes: int = 100


class ReactorScriptCreate(ReactorScriptBase):
    source: str


class ReactorScriptUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    entrypoint: Optional[str] = None
    triggers: Optional[list[ReactorTrigger]] = None
    status: Optional[ReactorScriptStatus] = None
    timeout_seconds: Optional[int] = None
    max_writes: Optional[int] = None
    source: Optional[str] = None


class ReactorScript(ReactorScriptBase):
    id: int
    user_id: int
    language: str = "python"
    source_sha256: str
    last_run_at: Optional[datetime] = None
    last_run_status: Optional[str] = None
    last_run_id: Optional[int] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


class ReactorRun(BaseModel):
    id: int
    script_id: int
    triggered_by: dict[str, Any]
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    status: ReactorRunStatus
    error: Optional[str] = None
    writes_count: int
    celery_task_id: Optional[str] = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class ReactorRunLog(BaseModel):
    run_id: int
    log: str


class ReactorTestRequest(BaseModel):
    payload: dict[str, Any] = Field(default_factory=dict)
    resource_type: Optional[ReactorResourceType] = None
    action: Optional[ReactorAction] = None


class ReactorQueryParams(BaseModel):
    filter: Optional[str] = None
