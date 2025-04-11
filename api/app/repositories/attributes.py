import time
from typing import Union
from uuid import UUID

from app.models import attribute as attribute_models
from app.models import event as event_models
from app.models import feed as feed_models
from app.models import tag as tag_models
from app.models import user as user_models
from app.repositories import tags as tags_repository
from app.repositories import attachments as attachments_repository
from app.schemas import attribute as attribute_schemas
from app.schemas import event as event_schemas
from app.worker import tasks
from fastapi import HTTPException, status
from fastapi_pagination.ext.sqlalchemy import paginate
from pymisp import MISPAttribute, MISPTag
from sqlalchemy.orm import Session
from sqlalchemy.sql import select
from fastapi_pagination import Page

tags_name_id_map = {}


def get_attributes(
    db: Session, event_id: int = None, deleted: bool = None, object_id: int = None
) -> Page[attribute_schemas.Attribute]:
    query = select(attribute_models.Attribute)

    if event_id is not None:
        query = query.where(attribute_models.Attribute.event_id == event_id)

    if deleted is not None:
        query = query.where(attribute_models.Attribute.deleted == deleted)

    query = query.where(attribute_models.Attribute.object_id == object_id)

    return paginate(db, query)


def get_attribute_by_id(
    db: Session, attribute_id: int
) -> Union[attribute_models.Attribute, None]:
    return (
        db.query(attribute_models.Attribute)
        .filter(attribute_models.Attribute.id == attribute_id)
        .first()
    )


def get_attribute_by_uuid(
    db: Session, attribute_uuid: UUID
) -> Union[attribute_models.Attribute, None]:
    return (
        db.query(attribute_models.Attribute)
        .filter(attribute_models.Attribute.uuid == attribute_uuid)
        .first()
    )


def create_attribute(
    db: Session, attribute: attribute_schemas.AttributeCreate
) -> attribute_models.Attribute:
    # TODO: Attribute::beforeValidate() && Attribute::$validate
    db_attribute = attribute_models.Attribute(
        event_id=attribute.event_id,
        object_id=(
            attribute.object_id
            if attribute.object_id is not None and attribute.object_id > 0
            else None
        ),
        object_relation=attribute.object_relation,
        category=attribute.category,
        type=attribute.type,
        value=attribute.value,
        to_ids=attribute.to_ids,
        uuid=attribute.uuid,
        timestamp=attribute.timestamp or time.time(),
        distribution=(
            event_schemas.DistributionLevel(attribute.distribution)
            if attribute.distribution is not None
            else event_schemas.DistributionLevel.INHERIT_EVENT
        ),
        sharing_group_id=attribute.sharing_group_id,
        comment=attribute.comment,
        deleted=attribute.deleted,
        disable_correlation=attribute.disable_correlation,
        first_seen=attribute.first_seen,
        last_seen=attribute.last_seen,
    )
    db.add(db_attribute)
    db.commit()
    db.refresh(db_attribute)

    tasks.handle_created_attribute.delay(
        db_attribute.id, db_attribute.object_id, db_attribute.event_id
    )

    return db_attribute


def create_attribute_from_pulled_attribute(
    db: Session,
    pulled_attribute: MISPAttribute,
    local_event_id: int,
    user: user_models.User,
) -> attribute_models.Attribute:
    # TODO: process sharing group // captureSG
    # TODO: enforce warninglist

    local_attribute = attribute_models.Attribute(
        event_id=local_event_id,
        category=pulled_attribute.category,
        type=pulled_attribute.type,
        value=pulled_attribute.value,
        to_ids=pulled_attribute.to_ids,
        uuid=pulled_attribute.uuid,
        timestamp=pulled_attribute.timestamp.timestamp(),
        distribution=event_schemas.DistributionLevel(pulled_attribute.distribution),
        comment=pulled_attribute.comment,
        sharing_group_id=(
            pulled_attribute.sharing_group_id
            if int(pulled_attribute.sharing_group_id) > 0
            else None
        ),
        deleted=pulled_attribute.deleted,
        disable_correlation=pulled_attribute.disable_correlation,
        object_relation=getattr(pulled_attribute, "object_relation", None),
        first_seen=(
            pulled_attribute.first_seen.timestamp()
            if hasattr(pulled_attribute, "first_seen")
            else None
        ),
        last_seen=(
            pulled_attribute.last_seen.timestamp()
            if hasattr(pulled_attribute, "last_seen")
            else None
        ),
    )

    if pulled_attribute.data is not None:
        # store file
        attachments_repository.store_attachment(pulled_attribute.data.getvalue())

    # TODO: process sigthings
    # TODO: process galaxies

    capture_attribute_tags(
        db, local_attribute, pulled_attribute.tags, local_event_id, user
    )

    return local_attribute


def update_attribute_from_pulled_attribute(
    db: Session,
    local_attribute: attribute_models.Attribute,
    pulled_attribute: MISPAttribute,
    local_event_id: int,
    user: user_models.User,
) -> attribute_models.Attribute:

    pulled_attribute.id = local_attribute.id
    pulled_attribute.event_id = local_event_id

    if local_attribute.timestamp < pulled_attribute.timestamp.timestamp():
        attribute_patch = attribute_schemas.AttributeUpdate(
            event_id=local_event_id,
            category=pulled_attribute.category,
            type=pulled_attribute.type,
            value=pulled_attribute.value,
            to_ids=pulled_attribute.to_ids,
            timestamp=pulled_attribute.timestamp.timestamp(),
            distribution=event_schemas.DistributionLevel(pulled_attribute.distribution),
            comment=pulled_attribute.comment,
            sharing_group_id=(
                pulled_attribute.sharing_group_id
                if int(pulled_attribute.sharing_group_id) > 0
                else local_attribute.sharing_group_id
            ),
            deleted=pulled_attribute.deleted,
            disable_correlation=pulled_attribute.disable_correlation,
            object_relation=getattr(
                pulled_attribute, "object_relation", local_attribute.object_relation
            ),
            first_seen=(
                pulled_attribute.first_seen.timestamp()
                if hasattr(pulled_attribute, "first_seen")
                else local_attribute.first_seen
            ),
            last_seen=(
                pulled_attribute.last_seen.timestamp()
                if hasattr(pulled_attribute, "last_seen")
                else local_attribute.last_seen
            ),
        )
        update_attribute(db, local_attribute.id, attribute_patch)

    if pulled_attribute.data is not None:
        # store file
        attachments_repository.store_attachment(pulled_attribute.data.getvalue())

    capture_attribute_tags(
        db, local_attribute, pulled_attribute.tags, local_event_id, user
    )

    # TODO: process sigthings
    # TODO: process galaxies

    return local_attribute


def update_attribute(
    db: Session, attribute_id: int, attribute: attribute_schemas.AttributeUpdate
) -> attribute_models.Attribute:
    # TODO: Attribute::beforeValidate() && Attribute::$validate
    db_attribute = get_attribute_by_id(db, attribute_id=attribute_id)

    if db_attribute is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Attribute not found"
        )

    attribute_patch = attribute.model_dump(exclude_unset=True)
    for key, value in attribute_patch.items():
        setattr(db_attribute, key, value)

    db.add(db_attribute)
    db.commit()
    db.refresh(db_attribute)

    return db_attribute


def delete_attribute(db: Session, attribute_id: int | str) -> None:

    if isinstance(attribute_id, str):
        db_attribute = get_attribute_by_uuid(db, attribute_uuid=UUID(attribute_id))
    else:
        db_attribute = get_attribute_by_id(db, attribute_id=attribute_id)

    if db_attribute is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Attribute not found"
        )

    db_attribute.deleted = True

    db.add(db_attribute)
    db.commit()
    db.refresh(db_attribute)

    tasks.handle_deleted_attribute.delay(
        db_attribute.id, db_attribute.object_id, db_attribute.event_id
    )


def capture_attribute_tags(
    db: Session,
    db_attribute: attribute_models.Attribute,
    tags: list[MISPTag],
    local_event_id: int,
    user: user_models.User,
):
    for tag in tags:
        if tag.local:
            # if tag is local, skip it
            continue

        if tags_name_id_map.get(tag.name):
            # if tag name is already in the map, use it
            db_tag = tags_name_id_map[tag.name]
        else:
            # get tag from DB
            db_tag = tags_repository.get_tag_by_name(db, tag.name)

            if db_tag is None:
                # create tag if not exists
                db_tag = tag_models.Tag(
                    name=tag.name,
                    colour=tag.colour,
                    org_id=user.org_id,
                    user_id=user.id,
                    local_only=False,
                    # exportable=tag.exportable,
                    # hide_tag=tag.hide_tag,
                    # numerical_value=tag.numerical_value,
                    # is_galaxy=tag.is_galaxy,
                    # is_custom_galaxy=tag.is_custom_galaxy,
                )
                db.add(db_tag)

            # store tag id in the map
            tags_name_id_map[tag.name] = db_tag

        db_attribute_tag = tag_models.AttributeTag(
            attribute=db_attribute,
            event_id=local_event_id,
            tag=db_tag,
            local=tag.local,
        )
        db.add(db_attribute_tag)


def create_attributes_from_fetched_event(
    db: Session,
    local_event: event_models.Event,
    attributes: list[MISPAttribute],
    object_id: int | None,
    feed: feed_models.Feed,
    user: user_models.User,
) -> event_models.Event:

    for attribute in attributes:
        db_attribute = attribute_models.Attribute(
            event_id=local_event.id,
            category=attribute.category,
            type=attribute.type,
            value=str(attribute.value),
            to_ids=attribute.to_ids,
            uuid=attribute.uuid,
            timestamp=attribute.timestamp.timestamp(),
            distribution=event_models.DistributionLevel.INHERIT_EVENT,
            sharing_group_id=None,
            comment=attribute.comment,
            deleted=attribute.deleted,
            disable_correlation=attribute.disable_correlation,
            object_id=object_id,
            object_relation=getattr(attribute, "object_relation", None),
            first_seen=(
                int(attribute.first_seen.timestamp())
                if hasattr(attribute, "first_seen")
                else None
            ),
            last_seen=(
                int(attribute.last_seen.timestamp())
                if hasattr(attribute, "last_seen")
                else None
            ),
        )

        # store attachments
        if attribute.data is not None:
            # store file
            attachments_repository.store_attachment(attribute.data.getvalue())

        # TODO: process galaxies
        # TODO: process attribute sightings
        # TODO: process analyst notes

        # process tags
        capture_attribute_tags(db, db_attribute, attribute.tags, local_event.id, user)

        db.add(db_attribute)
        local_event.attribute_count += 1

        # TODO: process shadow_attributes

    db.commit()

    return local_event


def update_attributes_from_fetched_event(
    db: Session,
    local_event: event_models.Event,
    attributes: list[MISPAttribute],
    feed: feed_models.Feed,
    user: user_models.User,
) -> event_models.Event:

    local_event_attributes = (
        db.query(attribute_models.Attribute.uuid, attribute_models.Attribute.timestamp)
        .filter(attribute_models.Attribute.event_id == local_event.id)
        .all()
    )
    local_event_dict = {
        str(uuid): timestamp for uuid, timestamp in local_event_attributes
    }

    new_attributes = [
        attribute
        for attribute in attributes
        if attribute.uuid not in local_event_dict.keys()
    ]

    updated_attributes = [
        attribute
        for attribute in attributes
        if attribute.uuid in local_event_dict
        and attribute.timestamp.timestamp() > local_event_dict[attribute.uuid]
    ]

    # add new attributes
    local_event = create_attributes_from_fetched_event(
        db, local_event, new_attributes, None, feed, user
    )

    # update existing attributes
    batch_size = 100  # TODO: set the batch size via configuration
    updated_uuids = [attribute.uuid for attribute in updated_attributes]

    for batch_start in range(0, len(updated_uuids), batch_size):
        batch_uuids = updated_uuids[batch_start : batch_start + batch_size]

        db_attributes = (
            db.query(attribute_models.Attribute)
            .filter(attribute_models.Attribute.uuid.in_(batch_uuids))
            .enable_eagerloads(False)
            .yield_per(batch_size)
        )

        updated_attributes_dict = {
            attribute.uuid: attribute for attribute in updated_attributes
        }

        for db_attribute in db_attributes:
            updated_attribute = updated_attributes_dict[str(db_attribute.uuid)]
            db_attribute.category = updated_attribute.category
            db_attribute.type = updated_attribute.type
            db_attribute.value = str(updated_attribute.value)
            db_attribute.to_ids = updated_attribute.to_ids
            db_attribute.uuid = updated_attribute.uuid
            db_attribute.timestamp = updated_attribute.timestamp.timestamp()
            db_attribute.comment = updated_attribute.comment
            db_attribute.deleted = updated_attribute.deleted
            db_attribute.disable_correlation = updated_attribute.disable_correlation
            db_attribute.object_id = getattr(updated_attribute, "object_id", None)
            db_attribute.object_relation = getattr(
                updated_attribute, "object_relation", None
            )
            db_attribute.first_seen = (
                int(updated_attribute.first_seen.timestamp())
                if hasattr(updated_attribute, "first_seen")
                else None
            )
            db_attribute.last_seen = (
                int(updated_attribute.last_seen.timestamp())
                if hasattr(updated_attribute, "last_seen")
                else None
            )

            # process tags
            capture_attribute_tags(
                db, db_attribute, updated_attribute.tags, local_event.id, user
            )

            if updated_attribute.data is not None:
                # store file
                attachments_repository.store_attachment(
                    updated_attribute.data.getvalue()
                )

            # TODO: process galaxies
            # TODO: process attribute sightings
            # TODO: process analyst notes

        db.commit()

    db.commit()

    # TODO: process shadow_attributes

    db.commit()

    return local_event
