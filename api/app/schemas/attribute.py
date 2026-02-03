from typing import Optional
from uuid import UUID

from app.models.event import DistributionLevel
from app.schemas.tag import Tag
from pydantic import BaseModel, ConfigDict, computed_field


class AttributeBase(BaseModel):
    event_id: Optional[int] = None
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
    model_config = ConfigDict(use_enum_values=True)


class Attribute(AttributeBase):
    id: int
    tags: list[Tag] = []
    correlations: list[dict] = None
    model_config = ConfigDict(from_attributes=True)

    @computed_field
    @property
    def event_uuid(self) -> Optional[UUID]:
        event = getattr(self, "event", None)
        return event.uuid if event else None


class AttributeCreate(AttributeBase):
    event_uuid: Optional[UUID] = None
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
