from typing import Optional
from uuid import UUID
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class NotificationBase(BaseModel):
    user_id: int
    type: str
    entity_type: str
    entity_uuid: Optional[UUID] = None
    read: bool = False
    payload: Optional[dict] = {}
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: Optional[datetime] = None


class Notification(NotificationBase):
    id: int
    model_config = ConfigDict(from_attributes=True)


class StatusResponse(BaseModel):
    status: str
