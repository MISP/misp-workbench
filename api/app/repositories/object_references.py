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
    db_object_refence = object_reference_models.ObjectReference(
        uuid=pulled_object_reference.uuid,
        event_id=local_event_id,
        source_uuid=pulled_object_reference.object_uuid,
        referenced_uuid=pulled_object_reference.referenced_uuid,
        timestamp=pulled_object_reference.timestamp,
        relationship_type=pulled_object_reference.relationship_type,
        comment=pulled_object_reference.comment,
    )

    return db_object_refence

def get_object_reference_by_uuid(
    db: Session, object_reference_uuid: int
) -> object_reference_models.ObjectReference:
    return (
        db.query(object_reference_models.ObjectReference)
        .filter(object_reference_models.ObjectReference.uuid == object_reference_uuid)
        .first()
    )

def update_object_reference_from_pulled_object_reference(
    db: Session,
    db_object_reference: object_reference_models.ObjectReference,
    pulled_object_reference: MISPObjectReference,
    local_event_id: int,
):
    db_object_reference.event_id = local_event_id
    db_object_reference.source_uuid = pulled_object_reference.object_uuid
    db_object_reference.referenced_uuid = pulled_object_reference.referenced_uuid
    db_object_reference.timestamp = pulled_object_reference.timestamp
    db_object_reference.relationship_type = pulled_object_reference.relationship_type
    db_object_reference.comment = pulled_object_reference.comment

    return db_object_reference