from typing import Any, Optional, Literal
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class HuntQueryParams(BaseModel):
    filter: Optional[str] = None


class HuntBase(BaseModel):
    name: str
    description: Optional[str] = None
    query: str
    hunt_type: Literal["opensearch", "rulezet", "cpe"] = "opensearch"
    index_target: Optional[Literal["attributes", "events", "correlations"]] = "attributes"
    status: Literal["active", "paused"] = "active"


class HuntCreate(HuntBase):
    pass


class HuntUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    query: Optional[str] = None
    hunt_type: Optional[Literal["opensearch", "rulezet", "cpe"]] = None
    index_target: Optional[Literal["attributes", "events", "correlations"]] = None
    status: Optional[Literal["active", "paused"]] = None


class Hunt(HuntBase):
    id: int
    user_id: int
    last_run_at: Optional[datetime] = None
    last_match_count: Optional[int] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


class HuntRunHistoryEntry(BaseModel):
    run_at: datetime
    match_count: int
    model_config = ConfigDict(from_attributes=True)


class HuntResults(BaseModel):
    total: int
    hits: list[dict[str, Any]]


class HuntRunResult(BaseModel):
    hunt: Hunt
    total: int
    hits: list[dict[str, Any]]
