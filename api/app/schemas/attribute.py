from typing import Optional
from uuid import UUID

from app.models.event import DistributionLevel
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

    class Config:
        orm_mode = True


class AttributeCreate(AttributeBase):
    pass
