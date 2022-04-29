from typing import Optional
from pydantic import BaseModel
from uuid import UUID
from datetime import date


class EventBase(BaseModel):
    id: int
    org_id: int
    date: date
    info: str
    user_id: int
    uuid: UUID
    published: bool
    analysis: int
    attribute_count: int
    orgc_id: int
    timestamp: int
    distribution: int
    sharing_group_id: int
    proposal_email_lock: bool
    locked: bool
    threat_level_id: int
    publish_timestamp: int
    sighting_timestamp: int
    disable_correlation: bool
    extends_uuid: Optional[UUID]
    protected: bool


class Event(EventBase):
    class Config:
        orm_mode = True
