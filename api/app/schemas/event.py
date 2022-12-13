from datetime import date
from typing import Optional
from uuid import UUID

from app.models.event import AnalysisLevel, DistributionLevel, ThreatLevel
from app.schemas.attribute import Attribute
from app.schemas.object import Object
from app.schemas.sharing_groups import SharingGroup
from app.schemas.tag import Tag
from pydantic import BaseModel


class EventBase(BaseModel):
    org_id: Optional[int]
    date: Optional[date]
    info: str
    user_id: Optional[int]
    uuid: Optional[UUID]
    published: Optional[bool]
    analysis: Optional[AnalysisLevel]
    attribute_count: Optional[int]
    object_count: Optional[int]
    orgc_id: Optional[int]
    timestamp: Optional[int]
    distribution: Optional[DistributionLevel]
    sharing_group_id: Optional[int]
    proposal_email_lock: Optional[bool]
    locked: Optional[bool]
    threat_level: Optional[ThreatLevel]
    publish_timestamp: Optional[int]
    sighting_timestamp: Optional[int]
    disable_correlation: Optional[bool]
    extends_uuid: Optional[UUID]
    protected: Optional[bool]

    class Config:
        use_enum_values = True


class Event(EventBase):
    id: int
    attributes: list[Attribute] = []
    objects: list[Object] = []
    sharing_group: Optional[SharingGroup] = None
    tags: list[Tag] = []

    class Config:
        orm_mode = True


class EventCreate(EventBase):
    pass


class EventUpdate(BaseModel):
    date: Optional[date]
    info: Optional[str]
    published: Optional[bool]
    analysis: Optional[AnalysisLevel]
    timestamp: Optional[int]
    distribution: Optional[DistributionLevel]
    sharing_group_id: Optional[int]
    proposal_email_lock: Optional[bool]
    locked: Optional[bool]
    threat_level: Optional[ThreatLevel]
    publish_timestamp: Optional[int]
    sighting_timestamp: Optional[int]
    disable_correlation: Optional[bool]
    extends_uuid: Optional[UUID]
    protected: Optional[bool]
