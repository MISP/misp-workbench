from typing import Optional
from uuid import UUID

from app.models.event import DistributionLevel
from app.schemas.tag import Tag
from pydantic import BaseModel, ConfigDict


class AttributeBase(BaseModel):
    event_id: int
    object_id: Optional[int] = None
    object_relation: Optional[str] = None
    category: str
    type: str
    value: str
    to_ids: Optional[bool] = None
    uuid: Optional[UUID] = None
    timestamp: Optional[int] = None
    distribution: Optional[DistributionLevel] = None
    sharing_group_id: Optional[int] = None
    comment: Optional[str] = None
    deleted: Optional[bool] = None
    disable_correlation: Optional[bool] = None
    first_seen: Optional[int] = None
    last_seen: Optional[int] = None


class Attribute(AttributeBase):
    id: int
    tags: list[Tag] = []
    model_config = ConfigDict(from_attributes=True)


class AttributeCreate(AttributeBase):
    pass


class AttributeUpdate(BaseModel):
    object_id: Optional[int] = None
    object_relation: Optional[str] = None
    category: Optional[str] = None
    type: Optional[str] = None
    value: Optional[str] = None
    to_ids: Optional[bool] = None
    timestamp: Optional[int] = None
    distribution: Optional[DistributionLevel] = None
    sharing_group_id: Optional[int] = None
    comment: Optional[str] = None
    deleted: Optional[bool] = None
    disable_correlation: Optional[bool] = None
    first_seen: Optional[int] = None
    last_seen: Optional[int] = None
