import time

from pymisp import MISPObject
from sqlalchemy.orm import Session

from ..models import object as object_models
from ..repositories import attributes as attributes_repository
from ..repositories import object_references as object_references_repository
from ..schemas import event as event_schemas
from ..schemas import object as object_schemas


def get_objects(db: Session, skip: int = 0, limit: int = 100):
    return db.query(object_models.Object).offset(skip).limit(limit).all()


def get_object_by_id(db: Session, object_id: int):
    return (
        db.query(object_models.Object)
        .filter(object_models.Object.id == object_id)
        .first()
    )


def create_object(db: Session, object: object_schemas.ObjectCreate):
    # TODO: MispObject::beforeValidate() && MispObject::$validate
    db_object = object_models.Object(
        event_id=object.event_id,
        name=object.name,
        meta_category=object.meta_category,
        description=object.description,
        template_uuid=object.template_uuid,
        template_version=object.template_version,
        uuid=object.uuid,
        timestamp=object.timestamp or time.time(),
        distribution=object.distribution,
        sharing_group_id=object.sharing_group_id,
        comment=object.comment,
        deleted=object.deleted,
        first_seen=object.first_seen,
        last_seen=object.last_seen,
    )

    db.add(db_object)
    db.commit()
    db.refresh(db_object)

    return db_object


def create_object_from_pulled_object(
    db: Session, pulled_object: MISPObject, local_event_id: int
):
    # TODO: process sharing group // captureSG
    # TODO: enforce warninglist

    db_object = create_object(
        db,
        object_models.Object(
            event_id=local_event_id,
            name=pulled_object.name,
            meta_category=pulled_object["meta-category"],
            description=pulled_object.description,
            template_uuid=pulled_object.template_uuid,
            template_version=pulled_object.template_version,
            uuid=pulled_object.uuid,
            timestamp=pulled_object.timestamp.timestamp(),
            distribution=event_schemas.DistributionLevel(pulled_object.distribution),
            sharing_group_id=pulled_object.sharing_group_id,
            comment=pulled_object.comment,
            deleted=pulled_object.deleted,
            first_seen=pulled_object.first_seen.timestamp()
            if hasattr(pulled_object, "first_seen")
            else None,
            last_seen=pulled_object.last_seen.timestamp()
            if hasattr(pulled_object, "last_seen")
            else None,
        ),
    )

    db.add(db_object)
    db.commit()
    db.refresh(db_object)

    for pulled_attribute in pulled_object.attributes:
        pulled_attribute.object_id = db_object.id
        attributes_repository.create_attribute_from_pulled_attribute(
            db, pulled_attribute, local_event_id
        )

    for pulled_object_reference in pulled_object.ObjectReference:
        pulled_object_reference.object_id = db_object.id
        object_references_repository.create_object_reference_from_pulled_object_reference(
            db, pulled_object_reference, local_event_id
        )

    return db_object
