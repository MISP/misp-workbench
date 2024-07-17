import time

from app.models import object as object_models
from app.repositories import attributes as attributes_repository
from app.repositories import object_references as object_references_repository
from app.schemas import event as event_schemas
from app.schemas import object as object_schemas
from fastapi import HTTPException, status
from pymisp import MISPObject
from sqlalchemy.orm import Session


def get_objects(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    event_id: int = None,
    deleted: bool = False,
) -> list[object_models.Object]:
    query = db.query(object_models.Object)

    if event_id is not None:
        query = query.filter(object_models.Object.event_id == event_id)

    query = query.filter(object_models.Object.deleted.is_(bool(deleted)))

    return query.offset(skip).limit(limit).all()


def get_object_by_id(db: Session, object_id: int):
    return (
        db.query(object_models.Object)
        .filter(object_models.Object.id == object_id)
        .first()
    )


def create_object(
    db: Session, object: object_schemas.ObjectCreate
) -> object_models.Object:
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
        distribution=(
            object.distribution
            if object.distribution is None
            else event_schemas.DistributionLevel(object.distribution)
        ),
        sharing_group_id=object.sharing_group_id,
        comment=object.comment,
        deleted=object.deleted,
        first_seen=object.first_seen,
        last_seen=object.last_seen,
    )

    db.add(db_object)
    db.commit()
    db.refresh(db_object)

    for attribute in object.attributes:
        attribute.object_id = db_object.id
        attribute.event_id = object.event_id
        attributes_repository.create_attribute(db, attribute)

    db.refresh(db_object)

    return db_object


def create_object_from_pulled_object(
    db: Session, pulled_object: MISPObject, local_event_id: int
) -> MISPObject:
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
            sharing_group_id=(
                pulled_object.sharing_group_id
                if int(pulled_object.sharing_group_id) > 0
                else None
            ),
            comment=pulled_object.comment,
            deleted=pulled_object.deleted,
            first_seen=(
                pulled_object.first_seen.timestamp()
                if hasattr(pulled_object, "first_seen")
                else None
            ),
            last_seen=(
                pulled_object.last_seen.timestamp()
                if hasattr(pulled_object, "last_seen")
                else None
            ),
        ),
    )

    db.add(db_object)
    db.commit()
    db.refresh(db_object)

    pulled_object.id = db_object.id

    for pulled_attribute in pulled_object.attributes:
        pulled_attribute.object_id = db_object.id
        pulled_attribute.event_id = local_event_id
        db_attribute = attributes_repository.create_attribute_from_pulled_attribute(
            db, pulled_attribute, local_event_id
        )
        pulled_attribute.id = db_attribute.id

    for pulled_object_reference in pulled_object.ObjectReference:
        pulled_object_reference.object_id = db_object.id
        object_references_repository.create_object_reference_from_pulled_object_reference(
            db, pulled_object_reference, local_event_id
        )

    return pulled_object


def update_object(
    db: Session, object_id: int, object: object_schemas.ObjectUpdate
) -> object_models.Object:
    # TODO: MISPObject::beforeValidate() && MISPObject::$validate
    db_object = get_object_by_id(db, object_id=object_id)

    if db_object is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Object not found"
        )

    object_patch = object.model_dump(exclude_unset=True)
    for key, value in object_patch.items():
        setattr(db_object, key, value)

    db.add(db_object)
    db.commit()
    db.refresh(db_object)

    return db_object


def delete_object(db: Session, object_id: int) -> object_models.Object:
    db_object = get_object_by_id(db, object_id=object_id)

    if db_object is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Object not found"
        )

    db_object.deleted = True

    db.add(db_object)
    db.commit()
    db.refresh(db_object)

    return db_object
