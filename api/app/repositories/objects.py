import logging
import time

from app.models import attribute as attribute_models
from app.models import event as event_models
from app.models import object as object_models
from app.models import object_reference as object_reference_models
from app.repositories import attributes as attributes_repository
from app.repositories import object_references as object_references_repository
from app.schemas import event as event_schemas
from app.schemas import object as object_schemas
from app.worker import tasks
from fastapi import HTTPException, status
from pymisp import MISPObject
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


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
            event_schemas.DistributionLevel(object.distribution)
            if object.distribution is not None
            else event_schemas.DistributionLevel.INHERIT_EVENT
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

    for object_reference in object.object_references:
        object_reference.object_id = db_object.id
        object_reference.event_id = db_object.event_id
        object_references_repository.create_object_reference(db, object_reference)

    db.refresh(db_object)

    tasks.handle_created_object.delay(db_object.id, db_object.event_id)

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

    # delete attributes
    for attribute in db_object.attributes:
        attributes_repository.delete_attribute(db, attribute.id)

    db.add(db_object)
    db.commit()
    db.refresh(db_object)

    tasks.handle_deleted_object.delay(db_object.id, db_object.event_id)

    return db_object


def create_event_objects_from_fetched_event(
    db: Session, local_event_id: int, event: event_schemas.Event
) -> int:

    object_count = 0
    attribute_count = 0

    for object in event.objects:
        db_object = object_models.Object(
            event_id=local_event_id,
            name=object.name,
            meta_category=object["meta-category"],
            description=object.description,
            template_uuid=object.template_uuid,
            template_version=object.template_version,
            uuid=object.uuid,
            timestamp=object.timestamp.timestamp(),
            distribution=event_schemas.DistributionLevel.INHERIT_EVENT,
            sharing_group_id=None,
            comment=object.comment,
            deleted=object.deleted,
            first_seen=(
                int(object.first_seen.timestamp())
                if hasattr(object, "first_seen")
                else None
            ),
            last_seen=(
                int(object.last_seen.timestamp())
                if hasattr(object, "last_seen")
                else None
            ),
        )

        db.add(db_object)
        db.commit()
        db.refresh(db_object)
        object_count += 1

        for object_attribute in object.attributes:
            db_attribute = attribute_models.Attribute(
                event_id=local_event_id,
                object_id=db_object.id,
                category=object_attribute.category,
                type=object_attribute.type,
                value=str(object_attribute.value),
                to_ids=object_attribute.to_ids,
                uuid=object_attribute.uuid,
                timestamp=int(object_attribute.timestamp.timestamp()),
                distribution=event_models.DistributionLevel.INHERIT_EVENT,
                comment=object_attribute.comment,
                sharing_group_id=None,
                deleted=object_attribute.deleted,
                disable_correlation=object_attribute.disable_correlation,
                object_relation=getattr(object_attribute, "object_relation", None),
                first_seen=(
                    int(object_attribute.first_seen.timestamp())
                    if hasattr(object_attribute, "first_seen")
                    else None
                ),
                last_seen=(
                    int(object_attribute.last_seen.timestamp())
                    if hasattr(object_attribute, "last_seen")
                    else None
                ),
            )
            db.add(db_attribute)
            attribute_count += 1

        db.commit()

    # process object references
    for object in event.objects:
        for reference in object.references:
            referenced = (
                db.query(object_models.Object)
                .filter_by(uuid=reference.referenced_uuid)
                .first()
            )
            if referenced is None:
                referenced = (
                    db.query(attribute_models.Attribute)
                    .filter_by(uuid=reference.referenced_uuid)
                    .first()
                )
            if referenced is None:
                logger.error(
                    f"Referenced entity not found, skipping object reference uuid: {reference.uuid}"
                )
                break

            db_object_reference = object_reference_models.ObjectReference(
                uuid=reference.uuid,
                event_id=local_event_id,
                object_id=db_object.id,
                referenced_uuid=referenced.uuid,
                referenced_id=referenced.id,
                relationship_type=reference.relationship_type,
                timestamp=int(reference.timestamp),
                referenced_type=(
                    object_reference_models.ReferencedType.ATTRIBUTE
                    if referenced.__class__.__name__ == "Attribute"
                    else object_reference_models.ReferencedType.OBJECT
                ),
                comment=reference.comment,
                deleted=referenced.deleted,
            )
            db.add(db_object_reference)
        db.commit()

    return {"object_count": object_count, "attribute_count": attribute_count}
