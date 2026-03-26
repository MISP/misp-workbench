import time
from typing import Optional
from uuid import UUID

from app.schemas import object_reference as object_reference_schemas
from app.services.opensearch import get_opensearch_client
from opensearchpy.exceptions import NotFoundError
from pymisp import MISPObjectReference
from sqlalchemy.orm import Session


def create_object_reference(
    db: Session, object_reference: object_reference_schemas.ObjectReferenceCreate
) -> object_reference_schemas.ObjectReference:
    client = get_opensearch_client()
    ref_uuid = str(object_reference.uuid)

    ref_doc = {
        "uuid": ref_uuid,
        "object_id": object_reference.object_id,
        "event_uuid": str(object_reference.event_uuid) if object_reference.event_uuid else None,
        "source_uuid": str(object_reference.source_uuid) if object_reference.source_uuid else None,
        "referenced_uuid": str(object_reference.referenced_uuid) if object_reference.referenced_uuid else None,
        "timestamp": object_reference.timestamp or int(time.time()),
        "referenced_id": object_reference.referenced_id,
        "referenced_type": object_reference.referenced_type,
        "relationship_type": object_reference.relationship_type,
        "comment": object_reference.comment or "",
        "deleted": object_reference.deleted or False,
    }

    client.index(index="misp-object-references", id=ref_uuid, body=ref_doc, refresh=True)

    return object_reference_schemas.ObjectReference.model_validate(ref_doc)


def create_object_reference_from_pulled_object_reference(
    db: Session, pulled_object_reference: MISPObjectReference, event_uuid: UUID
) -> object_reference_schemas.ObjectReference:
    client = get_opensearch_client()
    ref_uuid = str(pulled_object_reference.uuid)

    ref_doc = {
        "uuid": ref_uuid,
        "event_uuid": str(event_uuid),
        "source_uuid": str(pulled_object_reference.object_uuid),
        "referenced_uuid": str(pulled_object_reference.referenced_uuid),
        "timestamp": pulled_object_reference.timestamp,
        "relationship_type": pulled_object_reference.relationship_type,
        "comment": pulled_object_reference.comment or "",
        "deleted": False,
    }

    client.index(index="misp-object-references", id=ref_uuid, body=ref_doc, refresh=True)

    return object_reference_schemas.ObjectReference.model_validate(ref_doc)


def get_object_reference_by_uuid(
    db: Session, object_reference_uuid
) -> Optional[object_reference_schemas.ObjectReference]:
    client = get_opensearch_client()
    try:
        doc = client.get(index="misp-object-references", id=str(object_reference_uuid))
        return object_reference_schemas.ObjectReference.model_validate(doc["_source"])
    except NotFoundError:
        return None


def update_object_reference_from_pulled_object_reference(
    db: Session,
    db_object_reference: object_reference_schemas.ObjectReference,
    pulled_object_reference: MISPObjectReference,
    event_uuid: UUID,
) -> object_reference_schemas.ObjectReference:
    client = get_opensearch_client()
    patch = {
        "event_uuid": str(event_uuid),
        "source_uuid": str(pulled_object_reference.object_uuid),
        "referenced_uuid": str(pulled_object_reference.referenced_uuid),
        "timestamp": pulled_object_reference.timestamp,
        "relationship_type": pulled_object_reference.relationship_type,
        "comment": pulled_object_reference.comment or "",
    }
    client.update(
        index="misp-object-references",
        id=str(db_object_reference.uuid),
        body={"doc": patch},
        refresh=True,
    )
    return get_object_reference_by_uuid(db, db_object_reference.uuid)
