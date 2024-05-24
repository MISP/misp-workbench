from typing import Optional
from uuid import UUID

from app.models.event import DistributionLevel
from app.schemas.attribute import Attribute
from pydantic import BaseModel, ConfigDict


class ObjectBase(BaseModel):
    name: str
    meta_category: Optional[str] = None
    description: Optional[str] = None
    template_uuid: Optional[UUID] = None
    template_version: int
    event_id: int
    uuid: Optional[UUID] = None
    timestamp: int
    distribution: Optional[DistributionLevel] = None
    sharing_group_id: Optional[int] = None
    comment: Optional[str] = None
    deleted: bool
    first_seen: Optional[int] = None
    last_seen: Optional[int] = None


class Object(ObjectBase):
    id: int

    attributes: list[Attribute] = []
    model_config = ConfigDict(from_attributes=True)


class ObjectCreate(ObjectBase):
    pass


class ObjectUpdate(BaseModel):
    name: Optional[str] = None
    meta_category: Optional[str] = None
    description: Optional[str] = None
    template_uuid: Optional[UUID] = None
    template_version: Optional[int] = None
    timestamp: Optional[int] = None
    distribution: Optional[DistributionLevel] = None
    sharing_group_id: Optional[int] = None
    comment: Optional[str] = None
    deleted: Optional[bool] = None
    first_seen: Optional[int] = None
    last_seen: Optional[int] = None
