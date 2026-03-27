import enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ReferencedType(enum.Enum):
    ATTRIBUTE = 0
    OBJECT = 1


class ObjectReferenceBase(BaseModel):
    uuid: UUID
    object_uuid: Optional[UUID] = None
    event_uuid: Optional[UUID] = None
    source_uuid: Optional[UUID] = None
    referenced_uuid: Optional[UUID] = None
    timestamp: Optional[int] = None
    referenced_id: Optional[int] = None
    referenced_type: Optional[ReferencedType] = None
    relationship_type: Optional[str] = None
    comment: Optional[str] = None
    deleted: bool = False
    model_config = ConfigDict(use_enum_values=True)


class ObjectReference(ObjectReferenceBase):
    model_config = ConfigDict(from_attributes=True)

    def to_misp_format(self) -> dict:
        ref_type = self.referenced_type
        if isinstance(ref_type, ReferencedType):
            ref_type_name = ref_type.name
        elif ref_type is not None:
            try:
                ref_type_name = ReferencedType(ref_type).name
            except ValueError:
                ref_type_name = str(ref_type)
        else:
            ref_type_name = None

        return {
            "id": None,
            "uuid": str(self.uuid),
            "timestamp": self.timestamp,
            "object_uuid": str(self.object_uuid) if self.object_uuid else None,
            "event_uuid": str(self.event_uuid) if self.event_uuid else None,
            "source_uuid": str(self.source_uuid) if self.source_uuid else None,
            "referenced_uuid": str(self.referenced_uuid) if self.referenced_uuid else None,
            "referenced_id": self.referenced_id,
            "referenced_type": ref_type_name,
            "relationship_type": self.relationship_type,
            "comment": self.comment,
            "deleted": self.deleted,
        }


class ObjectReferenceCreate(ObjectReferenceBase):
    referenced_type: Optional[ReferencedType] = None
    comment: Optional[str] = ""


class ObjectReferenceUpdate(ObjectReferenceBase):
    object_uuid: Optional[UUID] = None
    source_uuid: Optional[UUID] = None
    referenced_uuid: Optional[UUID] = None
    timestamp: Optional[int] = None
    referenced_id: Optional[int] = None
    referenced_type: Optional[ReferencedType] = None
    relationship_type: Optional[str] = None
    comment: Optional[str] = None
    deleted: Optional[bool] = None
