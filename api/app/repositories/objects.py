import logging
import time

from app.models import attribute as attribute_models
from app.models import event as event_models
from app.models import feed as feed_models
from app.models import object as object_models
from app.models import object_reference as object_reference_models
from app.repositories import attributes as attributes_repository
from app.repositories import object_references as object_references_repository
from app.schemas import event as event_schemas
from app.schemas import object as object_schemas
from app.schemas import user as user_schemas
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
    db_object = get_object_by_id(db, object_id=object_id)

    if db_object is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Object not found"
        )

    object_patch = object.model_dump(exclude_unset=True)
    for key, value in object_patch.items():
        setattr(db_object, key, value)
        
    for attribute in object.attributes:
        if attribute.id is None:
            # new attribute
            attribute.object_id = db_object.id
            attribute.event_id = db_object.event_id
        else:
            # existing attribute
            attributes_repository.update_attribute(db, attribute.id, attribute)
        

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


# def create_attributes_from_fetched_object(
#     db: Session,
#     local_event: event_models.Event,
#     object: object_models.Object,
#     attributes: list[MISPAttribute],
#     feed: feed_models.Feed,
#     user: user_schemas.User,
# ) -> event_models.Event:

#     for object_attribute in attributes:
#         db_attribute = attribute_models.Attribute(
#             event_id=local_event.id,
#             object_id=object.id,
#             category=object_attribute.category,
#             type=object_attribute.type,
#             value=str(object_attribute.value),
#             to_ids=object_attribute.to_ids,
#             uuid=object_attribute.uuid,
#             timestamp=int(object_attribute.timestamp.timestamp()),
#             distribution=event_models.DistributionLevel.INHERIT_EVENT,
#             sharing_group_id=None,
#             comment=object_attribute.comment,
#             deleted=object_attribute.deleted,
#             disable_correlation=object_attribute.disable_correlation,
#             object_relation=getattr(object_attribute, "object_relation", None),
#             first_seen=(
#                 int(object_attribute.first_seen.timestamp())
#                 if hasattr(object_attribute, "first_seen")
#                 else None
#             ),
#             last_seen=(
#                 int(object_attribute.last_seen.timestamp())
#                 if hasattr(object_attribute, "last_seen")
#                 else None
#             ),
#         )
#         db.add(db_attribute)
#         local_event.attribute_count += 1

#         # process tags
#         attributes_repository.capture_attribute_tags(
#             db, db_attribute, object_attribute.tags, local_event, user
#         )

#         # TODO: process shadow_attributes
#         # TODO: process attribute sightings
#         # TODO: process galaxies
#         # TODO: process analyst notes

#     return local_event


def create_objects_from_fetched_event(
    db: Session,
    local_event: event_models.Event,
    objects: list[MISPObject],
    feed: feed_models.Feed,
    user: user_schemas.User,
) -> event_models.Event:

    for object in objects:
        db_object = object_models.Object(
            event_id=local_event.id,
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

        # TODO: process shadow_objects
        # TODO: process analyst notes

        db.add(db_object)
        db.commit()
        db.refresh(db_object)
        local_event.object_count += 1

        for attribute in object.attributes:
            attribute.object_id = db_object.id
            attribute.event_id = local_event.id

        local_event = attributes_repository.create_attributes_from_fetched_event(
            db, local_event, object.attributes, feed, user
        )

        # TODO: process galaxies
        # TODO: process analyst notes

        db.commit()

    # process object references
    for object in objects:
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
                event_id=local_event.id,
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

    return local_event


def update_objects_from_fetched_event(
    db: Session,
    local_event: event_models.Event,
    event: event_schemas.Event,
    feed: feed_models.Feed,
    user: user_schemas.User,
) -> event_models.Event:
    local_event_objects = (
        db.query(object_models.Object.uuid, object_models.Object.timestamp)
        .filter(object_models.Object.event_id == local_event.id)
        .all()
    )
    local_event_dict = {str(uuid): timestamp for uuid, timestamp in local_event_objects}

    new_objects = [
        object for object in event.objects if object.uuid not in local_event_dict.keys()
    ]

    updated_objects = [
        object
        for object in event.objects
        if object.uuid in local_event_dict
        and object.timestamp.timestamp() > local_event_dict[object.uuid]
    ]

    # add new objects
    local_event = create_objects_from_fetched_event(
        db, local_event, new_objects, feed, user
    )

    # update existing attributes
    batch_size = 100  # TODO: set the batch size via configuration
    updated_uuids = [object.uuid for object in updated_objects]

    for batch_start in range(0, len(updated_uuids), batch_size):
        batch_uuids = updated_uuids[batch_start : batch_start + batch_size]

        db_objects = (
            db.query(object_models.Object)
            .filter(object_models.Object.uuid.in_(batch_uuids))
            .enable_eagerloads(False)
            .yield_per(batch_size)
        )

        updated_objects_dict = {object.uuid: object for object in updated_objects}

        for db_object in db_objects:
            updated_object = updated_objects_dict[str(db_object.uuid)]
            db_object.name = updated_object.name
            db_object.meta_category = updated_object["meta-category"]
            db_object.description = updated_object.description
            db_object.template_uuid = updated_object.template_uuid
            db_object.template_version = updated_object.template_version
            db_object.timestamp = (updated_object.timestamp.timestamp(),)
            db_object.comment = (updated_object.comment,)
            db_object.deleted = updated_object.deleted
            db_object.first_seen = (
                (
                    updated_object.first_seen.timestamp()
                    if hasattr(updated_object, "first_seen")
                    else None
                ),
            )
            db_object.last_seen = (
                (
                    updated_object.last_seen.timestamp()
                    if hasattr(updated_object, "last_seen")
                    else None
                ),
            )

            for attribute in updated_object.attributes:
                attribute.object_id = db_object.id
                attribute.event_id = local_event.id

            # process attributes
            local_event = attributes_repository.update_attributes_from_fetched_event(
                db, local_event, updated_object.attributes, feed, user
            )

            # TODO: process galaxies
            # TODO: process attribute sightings
            # TODO: process analyst notes

        # process object references
        for updated_object in updated_objects:
            for reference in updated_object.references:
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
                    event_id=local_event.id,
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

    db.commit()

    # # TODO: process shadow_attributes

    # db.commit()

    return local_event
