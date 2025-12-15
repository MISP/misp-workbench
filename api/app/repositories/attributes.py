import time
from typing import Union
from uuid import UUID
from app.models.event import DistributionLevel
from app.services.opensearch import get_opensearch_client
from app.models import attribute as attribute_models
from app.models import tag as tag_models
from app.models import user as user_models
from app.repositories import attachments as attachments_repository
from app.repositories import events as events_repository
from app.schemas import attribute as attribute_schemas
from app.schemas import event as event_schemas
from app.worker import tasks
from fastapi import HTTPException, status
from fastapi_pagination.ext.sqlalchemy import paginate
from pymisp import MISPAttribute, MISPTag
from sqlalchemy.orm import Session
from sqlalchemy.sql import select
from fastapi_pagination import Page
from collections import defaultdict
from opensearchpy.exceptions import NotFoundError

def enrich_attributes_page_with_correlations(
    attributes_page: Page[attribute_schemas.Attribute],
) -> Page[attribute_schemas.Attribute]:
    OpenSearchClient = get_opensearch_client()

    uuids = [attr.uuid for attr in attributes_page.items]
    if not uuids:
        return attributes_page

    query = {
        "query": {"terms": {"source_attribute_uuid.keyword": uuids}},
        "size": 10000,  # results should be less than MAX_CORRELATIONS_PER_DOC * page_size
    }

    try:
        response = OpenSearchClient.search(index="misp-attribute-correlations", body=query)
        hits = response["hits"]["hits"]
    except NotFoundError:
        for attr in attributes_page.items:
            attr.correlations = []
        return attributes_page

    correlation_map = defaultdict(list)
    for hit in hits:
        source_attribute_uuid = hit["_source"]["source_attribute_uuid"]
        correlation_map[source_attribute_uuid].append(hit)

    for attr in attributes_page.items:
        attr.correlations = correlation_map.get(str(attr.uuid), [])

    return attributes_page


def get_attributes(
    db: Session, event_uuid: str = None, deleted: bool = None, object_id: int = None
) -> Page[attribute_schemas.Attribute]:
    query = select(attribute_models.Attribute)

    if event_uuid is not None:
        db_event = events_repository.get_event_by_uuid(event_uuid=event_uuid, db=db)
        if db_event is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Event not found"
            )
        query = query.where(attribute_models.Attribute.event_id == db_event.id)

    if deleted is not None:
        query = query.where(attribute_models.Attribute.deleted == deleted)

    query = query.where(attribute_models.Attribute.object_id == object_id)

    page_results = paginate(db, query)

    return enrich_attributes_page_with_correlations(page_results)


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

    if db_attribute is not None:
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
        value=pulled_attribute.value if isinstance(pulled_attribute.value, str) else str(pulled_attribute.value),
        to_ids=pulled_attribute.to_ids,
        uuid=pulled_attribute.uuid,
        timestamp=pulled_attribute.timestamp.timestamp(),
        distribution=event_schemas.DistributionLevel(
            event_schemas.DistributionLevel(pulled_attribute.distribution)
            if pulled_attribute.distribution is not None
            else event_schemas.DistributionLevel.INHERIT_EVENT
        ),
        comment=pulled_attribute.comment,
        sharing_group_id=None,
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
            value=pulled_attribute.value if isinstance(pulled_attribute.value, str) else str(pulled_attribute.value),
            to_ids=pulled_attribute.to_ids,
            timestamp=pulled_attribute.timestamp.timestamp(),
            distribution=event_schemas.DistributionLevel(
                pulled_attribute.distribution or DistributionLevel.INHERIT_EVENT
            ),
            comment=pulled_attribute.comment,
            sharing_group_id=None,
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

    tasks.handle_updated_attribute.delay(
        local_attribute.id, local_attribute.object_id, local_attribute.event_id
    )

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

    tasks.handle_updated_attribute.delay(
        db_attribute.id, db_attribute.object_id, db_attribute.event_id
    )

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
    tag_name_to_db_tag = {}

    tag_names = [tag.name for tag in tags if not tag.local]

    existing_tags = (
        db.query(tag_models.Tag).filter(tag_models.Tag.name.in_(tag_names)).all()
    )

    for tag in existing_tags:
        tag_name_to_db_tag[tag.name] = tag

    new_tags = []
    for tag in tags:
        if tag.local:
            continue

        if tag.name not in tag_name_to_db_tag:
            new_tag = tag_models.Tag(
                name=tag.name,
                colour=tag.colour,
                org_id=user.org_id,
                user_id=user.id,
                local_only=False,
            )
            new_tags.append(new_tag)
            tag_name_to_db_tag[tag.name] = new_tag

    if new_tags:
        db.add_all(new_tags)
        db.commit()

    for tag in tags:
        if tag.local:
            continue

        db_tag = tag_name_to_db_tag[tag.name]

        db_attribute_tag = tag_models.AttributeTag(
            attribute=db_attribute,
            event_id=local_event_id,
            tag_id=db_tag.id,
            local=tag.local,
        )
        db.add(db_attribute_tag)

    db.commit()
