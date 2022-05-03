from typing import List, Optional
from pydantic import BaseModel
from uuid import UUID
from datetime import date
from .attribute import Attribute


class EventBase(BaseModel):
    org_id: int
    date: Optional[date]
    info: str
    user_id: int
    uuid: Optional[UUID]
    published: Optional[bool]
    analysis: Optional[int]
    attribute_count: Optional[int]
    orgc_id: Optional[int]
    timestamp: Optional[int]
    distribution: Optional[int]
    sharing_group_id: Optional[int]
    proposal_email_lock: Optional[bool]
    locked: Optional[bool]
    threat_level_id: Optional[int]
    publish_timestamp: Optional[int]
    sighting_timestamp: Optional[int]
    disable_correlation: Optional[bool]
    extends_uuid: Optional[UUID]
    protected: Optional[bool]


class Event(EventBase):
    id: int
    class Config:
        orm_mode = True

    attributes: List[Attribute] = []


class EventCreate(EventBase):
    pass