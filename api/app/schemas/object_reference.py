from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ObjectReferenceBase(BaseModel):
    uuid: UUID
    object_id: int
    event_id: int
    source_uuid: Optional[UUID] = None
    referenced_uuid: Optional[UUID] = None
    timestamp: int
    referenced_id: int
    referenced_type: int
    relationship_type: Optional[str] = None
    comment: str
    deleted: bool


class ObjectReference(ObjectReferenceBase):
    id: int
    model_config = ConfigDict(from_attributes=True)


class ObjectReferenceCreate(ObjectReferenceBase):
    pass


class ObjectReferenceUpdate(ObjectReferenceBase):
    object_id: Optional[int] = None
    source_uuid: Optional[UUID] = None
    referenced_uuid: Optional[UUID] = None
    timestamp: Optional[int] = None
    referenced_id: Optional[int] = None
    referenced_type: Optional[int] = None
    relationship_type: Optional[str] = None
    comment: Optional[str] = None
    deleted: Optional[bool] = None
