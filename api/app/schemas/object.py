from typing import Optional
from uuid import UUID

from app.models.event import DistributionLevel
from app.schemas.attribute import Attribute, AttributeCreate
from app.schemas.object_reference import ObjectReference, ObjectReferenceCreate
from pydantic import BaseModel, ConfigDict, computed_field


class ObjectBase(BaseModel):
    name: str
    meta_category: Optional[str] = None
    description: Optional[str] = None
    template_uuid: Optional[str] = None
    template_version: int
    event_id: Optional[int] = None
    uuid: Optional[UUID] = None
    timestamp: int
    distribution: Optional[DistributionLevel] = None
    sharing_group_id: Optional[int] = None
    comment: Optional[str] = None
    deleted: Optional[bool] = False
    first_seen: Optional[int] = None
    last_seen: Optional[int] = None
    model_config = ConfigDict(use_enum_values=True)


class Object(ObjectBase):
    id: int
    attributes: list[Attribute] = []
    object_references: list[ObjectReference] = []
    model_config = ConfigDict(from_attributes=True)

    @computed_field
    @property
    def event_uuid(self) -> Optional[UUID]:
        event = getattr(self, "event", None)
        return event.uuid if event else None


class ObjectCreate(ObjectBase):
    event_uuid: Optional[UUID] = None
    attributes: Optional[list[AttributeCreate]] = []
    object_references: list[ObjectReferenceCreate] = []


class ObjectUpdate(BaseModel):
    name: Optional[str] = None
    meta_category: Optional[str] = None
    description: Optional[str] = None
    template_uuid: Optional[str] = None
    template_version: Optional[int] = None
    timestamp: Optional[int] = None
    distribution: Optional[DistributionLevel] = None
    sharing_group_id: Optional[int] = None
    comment: Optional[str] = None
    deleted: Optional[bool] = None
    first_seen: Optional[int] = None
    last_seen: Optional[int] = None
    new_attributes: Optional[list[AttributeCreate]] = []
    update_attributes: Optional[list[AttributeCreate]] = []
    delete_attributes: Optional[list[str]] = []
