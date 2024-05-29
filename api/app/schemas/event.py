from datetime import datetime
from typing import Optional
from uuid import UUID

from app.models.event import AnalysisLevel, DistributionLevel, ThreatLevel
from app.schemas.attribute import Attribute
from app.schemas.object import Object
from app.schemas.sharing_groups import SharingGroup
from app.schemas.tag import Tag
from pydantic import BaseModel, ConfigDict


class EventBase(BaseModel):
    org_id: Optional[int] = None
    date: Optional[datetime] = None
    info: str
    user_id: Optional[int] = None
    uuid: Optional[UUID] = None
    published: Optional[bool] = None
    analysis: Optional[AnalysisLevel] = None
    attribute_count: Optional[int] = None
    object_count: Optional[int] = None
    orgc_id: Optional[int] = None
    timestamp: Optional[int] = None
    distribution: Optional[DistributionLevel] = None
    sharing_group_id: Optional[int] = None
    proposal_email_lock: Optional[bool] = None
    locked: Optional[bool] = None
    threat_level: Optional[ThreatLevel] = None
    publish_timestamp: Optional[int] = None
    sighting_timestamp: Optional[int] = None
    disable_correlation: Optional[bool] = None
    extends_uuid: Optional[UUID] = None
    protected: Optional[bool] = None
    deleted: Optional[bool] = None
    model_config = ConfigDict(use_enum_values=True)


class Event(EventBase):
    id: int
    attributes: list[Attribute] = []
    objects: list[Object] = []
    sharing_group: Optional[SharingGroup] = None
    tags: list[Tag] = []
    model_config = ConfigDict(from_attributes=True)


class EventCreate(EventBase):
    pass


class EventUpdate(BaseModel):
    date: Optional[datetime] = None
    info: Optional[str] = None
    published: Optional[bool] = None
    analysis: Optional[AnalysisLevel] = None
    timestamp: Optional[int] = None
    distribution: Optional[DistributionLevel] = None
    sharing_group_id: Optional[int] = None
    proposal_email_lock: Optional[bool] = None
    locked: Optional[bool] = None
    threat_level: Optional[ThreatLevel] = None
    publish_timestamp: Optional[int] = None
    sighting_timestamp: Optional[int] = None
    disable_correlation: Optional[bool] = None
    extends_uuid: Optional[UUID] = None
    protected: Optional[bool] = None
