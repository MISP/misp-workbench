from typing import Optional
from uuid import UUID
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class NotificationBase(BaseModel):
    user_id: int
    type: str
    entity_type: Optional[str] = None
    entity_uuid: UUID
    read: bool = False
    title: str
    payload: dict = {}
    created_at: datetime
    updated_at: datetime


class Notification(NotificationBase):
    id: int
    model_config = ConfigDict(from_attributes=True)
