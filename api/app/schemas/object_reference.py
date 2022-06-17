from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class ObjectReferenceBase(BaseModel):
    uuid: UUID
    object_id: int
    event_id: int
    source_uuid: Optional[UUID]
    referenced_uuid: Optional[UUID]
    timestamp: int
    referenced_id: int
    referenced_type: int
    relationship_type: Optional[str]
    comment: str
    deleted: bool


class ObjectReference(ObjectReferenceBase):
    id: int

    class Config:
        orm_mode = True


class ObjectReferenceCreate(ObjectReferenceBase):
    pass
