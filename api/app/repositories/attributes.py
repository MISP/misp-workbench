import time
from typing import Union

from app.models import attribute as attribute_models
from app.models import event as event_models
from app.models import tag as tag_models
from app.models import user as user_models
from app.repositories import tags as tags_repository
from app.schemas import attribute as attribute_schemas
from app.schemas import event as event_schemas
from app.worker import tasks
from fastapi import HTTPException, status
from fastapi_pagination.ext.sqlalchemy import paginate
from pymisp import MISPAttribute
from sqlalchemy.orm import Session


def get_attributes(
    db: Session, event_id: int = None, deleted: bool = None, object_id: int = None
):
    query = db.query(attribute_models.Attribute)

    if event_id is not None:
        query = query.filter(attribute_models.Attribute.event_id == event_id)

    if deleted is not None:
        query = query.filter(attribute_models.Attribute.deleted == deleted)

    query = query.filter(attribute_models.Attribute.object_id == object_id)

    return paginate(query)


def get_attribute_by_id(
    db: Session, attribute_id: int
) -> Union[attribute_models.Attribute, None]:
    return (
        db.query(attribute_models.Attribute)
        .filter(attribute_models.Attribute.id == attribute_id)
        .first()
    )


def create_attribute(
    db: Session, attribute: attribute_schemas.AttributeCreate
) -> attribute_models.Attribute:
    # TODO: Attribute::beforeValidate() && Attribute::$validate
    db_attribute = attribute_models.Attribute(
        event_id=attribute.event_id,
        object_id=attribute.object_id,
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

    tasks.handle_created_attribute.delay(db_attribute.id, db_attribute.event_id)

    return db_attribute


def create_attribute_from_pulled_attribute(
    db: Session, pulled_attribute: MISPAttribute, local_event_id: int
) -> MISPAttribute:
    # TODO: process sharing group // captureSG
    # TODO: enforce warninglist

    db_attribute = create_attribute(
        db,
        attribute_models.Attribute(
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
            object_id=pulled_attribute.object_id,
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
        ),
    )

    # TODO: process sigthings

    db.add(db_attribute)
    db.commit()
    db.refresh(db_attribute)

    pulled_attribute.id = db_attribute.id
    pulled_attribute.event_id = local_event_id

    tasks.handle_created_attribute.delay(pulled_attribute.id, pulled_attribute.event_id)

    return pulled_attribute


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


def delete_attribute(db: Session, attribute_id: int) -> None:
    db_attribute = get_attribute_by_id(db, attribute_id=attribute_id)

    if db_attribute is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Attribute not found"
        )

    db_attribute.deleted = True

    db.add(db_attribute)
    db.commit()
    db.refresh(db_attribute)

    tasks.handle_deleted_attribute.delay(db_attribute.id, db_attribute.event_id)


def create_event_attributes_from_fetched_event(
    db: Session, local_event_id: int, event: event_schemas.Event, user: user_models.User
) -> int:

    attribute_count = 0

    for attribute in event.attributes:

        db_attribute = attribute_models.Attribute(
            event_id=local_event_id,
            category=attribute.category,
            type=attribute.type,
            value=str(attribute.value),
            to_ids=attribute.to_ids,
            uuid=attribute.uuid,
            timestamp=attribute.timestamp.timestamp(),
            distribution=event_models.DistributionLevel.INHERIT_EVENT,
            comment=attribute.comment,
            sharing_group_id=None,
            deleted=attribute.deleted,
            disable_correlation=attribute.disable_correlation,
            object_id=None,
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

        db.add(db_attribute)
        attribute_count += 1

        for tag in attribute.tags:
            db_tag = tags_repository.get_tag_by_name(db, tag.name)

            if db_tag is None:
                # create tag if not exists
                db_tag = tag_models.Tag(
                    name=tag.name,
                    colour=tag.colour,
                    org_id=user.org_id,
                    user_id=user.id,
                    local_only=tag.local,
                    # exportable=tag.exportable,
                    # hide_tag=tag.hide_tag,
                    # numerical_value=tag.numerical_value,
                    # is_galaxy=tag.is_galaxy,
                    # is_custom_galaxy=tag.is_custom_galaxy,
                )
                db.add(db_tag)

            db_attribute_tag = tag_models.AttributeTag(
                attribute=db_attribute,
                event_id=local_event_id,
                tag=db_tag,
                local=tag.local,
            )
            db.add(db_attribute_tag)

        # TODO: process sharing group

    db.commit()

    return attribute_count
