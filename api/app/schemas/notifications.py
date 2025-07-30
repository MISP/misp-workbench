from typing import Optional
from uuid import UUID
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class NotificationBase(BaseModel):
    user_id: int
    type: str
    entity_type: str
    entity_uuid: UUID
    read: bool = False
    title: str
    payload: Optional[dict] = {}
    created_at: datetime = datetime.now()
    updated_at: Optional[datetime] = None


class Notification(NotificationBase):
    id: int
    model_config = ConfigDict(from_attributes=True)
