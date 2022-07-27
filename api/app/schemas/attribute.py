from typing import Optional
from uuid import UUID

from app.models.event import DistributionLevel
from app.schemas.tag import Tag
from pydantic import BaseModel


class AttributeBase(BaseModel):
    event_id: int
    object_id: Optional[int]
    object_relation: Optional[str]
    category: str
    type: str
    value: str
    to_ids: Optional[bool]
    uuid: Optional[UUID]
    timestamp: Optional[int]
    distribution: Optional[DistributionLevel]
    sharing_group_id: Optional[int]
    comment: Optional[str]
    deleted: Optional[bool]
    disable_correlation: Optional[bool]
    first_seen: Optional[int]
    last_seen: Optional[int]


class Attribute(AttributeBase):
    id: int
    tags: list[Tag] = []

    class Config:
        orm_mode = True


class AttributeCreate(AttributeBase):
    pass


class AttributeUpdate(BaseModel):
    object_id: Optional[int]
    object_relation: Optional[str]
    category: Optional[str]
    type: Optional[str]
    value: Optional[str]
    to_ids: Optional[bool]
    timestamp: Optional[int]
    distribution: Optional[DistributionLevel]
    sharing_group_id: Optional[int]
    comment: Optional[str]
    deleted: Optional[bool]
    disable_correlation: Optional[bool]
    first_seen: Optional[int]
    last_seen: Optional[int]
