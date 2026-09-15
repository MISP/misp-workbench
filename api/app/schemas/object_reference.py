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
        # MISP serializes referenced_type as the numeric level ("0" for an
        # Attribute, "1" for an Object), not the enum name - see the pulled
        # payloads in app/tests/scenarios. Consumers key off the number, so
        # emitting "OBJECT"/"ATTRIBUTE" here made every reference unreadable.
        ref_type = self.referenced_type
        if isinstance(ref_type, ReferencedType):
            ref_type_value = ref_type.value
        elif ref_type is not None:
            try:
                ref_type_value = ReferencedType(int(ref_type)).value
            except (ValueError, TypeError):
                ref_type_value = None
        else:
            ref_type_value = None

        return {
            "id": None,
            "uuid": str(self.uuid),
            "timestamp": self.timestamp,
            "object_uuid": str(self.object_uuid) if self.object_uuid else None,
            "event_uuid": str(self.event_uuid) if self.event_uuid else None,
            "source_uuid": str(self.source_uuid) if self.source_uuid else None,
            "referenced_uuid": str(self.referenced_uuid) if self.referenced_uuid else None,
            "referenced_id": self.referenced_id,
            "referenced_type": str(ref_type_value) if ref_type_value is not None else None,
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
