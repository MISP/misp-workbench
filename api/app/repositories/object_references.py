import time

from app.models import object_reference as object_reference_models
from app.schemas import object_reference as object_reference_schemas
from pymisp import MISPObjectReference
from sqlalchemy.orm import Session


def create_object_reference(
    db: Session, object_reference: object_reference_schemas.ObjectReferenceCreate
):
    # TODO: ObjectReference::beforeValidate() && ObjectReference::$validate
    db_object_reference = object_reference_models.ObjectReference(
        uuid=object_reference.uuid,
        object_id=object_reference.object_id,
        event_id=object_reference.event_id,
        source_uuid=object_reference.source_uuid,
        referenced_uuid=object_reference.referenced_uuid,
        timestamp=object_reference.timestamp or time.time(),
        referenced_id=object_reference.referenced_id,
        referenced_type=object_reference.referenced_type,
        relationship_type=object_reference.relationship_type,
        comment=object_reference.comment,
        deleted=object_reference.deleted,
    )

    db.add(db_object_reference)
    db.commit()
    db.refresh(db_object_reference)

    return db_object_reference


def create_object_reference_from_pulled_object_reference(
    db: Session, pulled_object_reference: MISPObjectReference, local_event_id: int
):
    db_object_refence = create_object_reference(
        db,
        object_reference_models.ObjectReference(
            uuid=pulled_object_reference.uuid,
            object_id=pulled_object_reference.object_id,
            event_id=local_event_id,
            source_uuid=pulled_object_reference.source_uuid,
            referenced_uuid=pulled_object_reference.referenced_uuid,
            timestamp=pulled_object_reference.timestamp,
            referenced_id=pulled_object_reference.referenced_id,
            referenced_type=(
                object_reference_schemas.ReferencedType(
                    int(pulled_object_reference.referenced_type)
                )
            ),
            relationship_type=pulled_object_reference.relationship_type,
            comment=pulled_object_reference.comment,
            deleted=pulled_object_reference.deleted,
        ),
    )

    db.add(db_object_refence)
    db.commit()
    db.refresh(db_object_refence)

    return db_object_refence
