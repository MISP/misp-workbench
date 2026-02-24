from typing import Optional, Literal
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class HuntBase(BaseModel):
    name: str
    description: Optional[str] = None
    query: str
    index_target: Literal["attributes", "events"] = "attributes"
    status: Literal["active", "paused"] = "active"


class HuntCreate(HuntBase):
    pass


class HuntUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    query: Optional[str] = None
    index_target: Optional[Literal["attributes", "events"]] = None
    status: Optional[Literal["active", "paused"]] = None


class Hunt(HuntBase):
    id: int
    user_id: int
    last_run_at: Optional[datetime] = None
    last_match_count: Optional[int] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)
