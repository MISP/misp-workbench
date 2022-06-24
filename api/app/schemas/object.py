from typing import Optional
from uuid import UUID

from app.models.event import DistributionLevel
from app.schemas.attribute import Attribute
from pydantic import BaseModel


class ObjectBase(BaseModel):
    name: str
    meta_category: Optional[str]
    description: Optional[str]
    template_uuid: Optional[UUID]
    template_version: int
    event_id: int
    uuid: Optional[UUID]
    timestamp: int
    distribution: Optional[DistributionLevel]
    sharing_group_id: Optional[int]
    comment: Optional[str]
    deleted: bool
    first_seen: Optional[int]
    last_seen: Optional[int]


class Object(ObjectBase):
    id: int

    attributes: list[Attribute] = []

    class Config:
        orm_mode = True


class ObjectCreate(ObjectBase):
    pass


class ObjectUpdate(BaseModel):
    name: Optional[str]
    meta_category: Optional[str]
    description: Optional[str]
    template_uuid: Optional[UUID]
    template_version: Optional[int]
    timestamp: Optional[int]
    distribution: Optional[DistributionLevel]
    sharing_group_id: Optional[int]
    comment: Optional[str]
    deleted: Optional[bool]
    first_seen: Optional[int]
    last_seen: Optional[int]
