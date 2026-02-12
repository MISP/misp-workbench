import logging
import time
from datetime import datetime
from uuid import UUID
from typing import Union, Iterable
from app.worker import tasks
from app.services.opensearch import get_opensearch_client
from app.services.vulnerability_lookup import lookup as vulnerability_lookup
from app.services.rulezet import lookup as rulezet_lookup
from app.models import event as event_models
from app.models import feed as feed_models
from app.models import tag as tag_models
from app.repositories import tags as tags_repository
from app.repositories import attributes as attributes_repository
from app.schemas import event as event_schemas
from app.schemas import user as user_schemas
import app.schemas.attribute as attribute_schemas
import app.schemas.vulnerability as vulnerability_schemas
from fastapi import HTTPException, status, Query
from fastapi_pagination.ext.sqlalchemy import paginate
from pymisp import MISPEvent, MISPOrganisation
from sqlalchemy.orm import Session, noload
from sqlalchemy.sql import select

logger = logging.getLogger(__name__)


def get_events(db: Session, info: str = Query(None), deleted: bool = Query(None), uuid: str = Query(None), include_attributes: bool = Query(False)):
    query = select(event_models.Event)

    if include_attributes:
        query = select(event_models.Event)
    else:   
        # avoid loading child relationships (attributes/objects) to keep the query lightweight
        query = select(event_models.Event).options(
            noload(event_models.Event.attributes), noload(event_models.Event.objects)
        )

    if info is not None:
        search = f"%{info}%"
        query = query.where(event_models.Event.info.like(search))

    if deleted is not None:
        query = query.where(event_models.Event.deleted == deleted)

    if uuid is not None:
        query = query.where(event_models.Event.uuid == uuid)

    # Sort the query by timestamp in descending order
    query = query.order_by(event_models.Event.timestamp.desc())

    return paginate(db, query)


def search_events(
    query: str = None,
    page: int = 0,
    from_value: int = 0,
    size: int = 10,
):
    OpenSearchClient = get_opensearch_client()

    search_body = {
        "query": {"query_string": {"query": query, "default_field": "info"}},
        "from": from_value,
        "size": size,
    }
    response = OpenSearchClient.search(index="misp-events", body=search_body)

    return {
        "page": page,
        "size": size,
        "total": response["hits"]["total"]["value"],
        "took": response["took"],
        "timed_out": response["timed_out"],
        "max_score": response["hits"]["max_score"],
        "results": response["hits"]["hits"],
    }


def export_events(
    query: str = None,
    format: str = "json",
    page_size: int = 1000,
) -> Iterable:
    client = get_opensearch_client()

    index = "misp-events"
    default_field = "info"

    search_body = {
        "query": {
            "query_string": {
                "query": query or "*",
                "default_field": default_field,
            }
        },
        "size": page_size,
        "sort": [{"_id": "asc"}],
    }

    search_after = None

    while True:
        if search_after:
            search_body["search_after"] = search_after

        response = client.search(index=index, body=search_body)
        hits = response["hits"]["hits"]

        if not hits:
            break

        for hit in hits:
            if format == "json":
                yield hit

        search_after = hits[-1].get("sort")


def get_event_by_id(db: Session, event_id: int):
    return (
        db.query(event_models.Event).filter(event_models.Event.id == event_id).first()
    )


def get_event_by_uuid(db: Session, event_uuid: str):
    return (
        db.query(event_models.Event)
        .filter(event_models.Event.uuid == event_uuid)
        .first()
    )


def get_user_by_info(db: Session, info: str):
    return db.query(event_models.Event).filter(event_models.Event.info == info).first()


def create_event(db: Session, event: event_schemas.EventCreate) -> event_models.Event:
    # TODO: Event::beforeValidate() && Event::$validate
    db_event = event_models.Event(
        org_id=event.org_id,
        date=event.date or datetime.now(),
        info=event.info,
        user_id=event.user_id,
        uuid=event.uuid,
        published=event.published,
        analysis=event_models.AnalysisLevel(event.analysis),
        attribute_count=event.attribute_count,
        object_count=event.object_count,
        orgc_id=event.orgc_id or event.org_id,
        timestamp=event.timestamp or time.time(),
        distribution=event_models.DistributionLevel(event.distribution),
        sharing_group_id=event.sharing_group_id,
        proposal_email_lock=event.proposal_email_lock,
        locked=event.locked,
        threat_level=event_models.ThreatLevel(event.threat_level),
        publish_timestamp=event.publish_timestamp,
        sighting_timestamp=event.sighting_timestamp,
        disable_correlation=event.disable_correlation,
        extends_uuid=event.extends_uuid,
        protected=event.protected,
        deleted=event.deleted,
    )
    db.add(db_event)
    db.commit()
    db.flush()
    db.refresh(db_event)

    tasks.handle_created_event.delay(db_event.uuid)

    return db_event


def create_event_from_pulled_event(db: Session, pulled_event: MISPEvent):
    event = event_models.Event(
        org_id=pulled_event.org_id,
        date=pulled_event.date,
        info=pulled_event.info,
        user_id=pulled_event.user_id,
        uuid=pulled_event.uuid,
        published=pulled_event.published,
        analysis=event_models.AnalysisLevel(pulled_event.analysis),
        attribute_count=pulled_event.attribute_count,
        object_count=len(pulled_event.objects),
        orgc_id=pulled_event.orgc_id,
        timestamp=pulled_event.timestamp.timestamp(),
        distribution=event_models.DistributionLevel(pulled_event.distribution),
        sharing_group_id=(
            pulled_event.sharing_group_id
            if pulled_event.sharing_group_id is not None
            and int(pulled_event.sharing_group_id) > 0
            else None
        ),
        proposal_email_lock=pulled_event.proposal_email_lock,
        locked=pulled_event.locked,
        threat_level=event_models.ThreatLevel(pulled_event.threat_level_id),
        publish_timestamp=pulled_event.publish_timestamp.timestamp(),
        # sighting_timestamp=pulled_event.sighting_timestamp, # TODO: add sighting_timestamp
        disable_correlation=pulled_event.disable_correlation,
        extends_uuid=pulled_event.extends_uuid or None,
        # protected=pulled_event.protected # TODO: add protected [pymisp]
    )
    db.add(event)
    db.commit()
    db.refresh(event)

    tasks.handle_created_event.delay(event.uuid)

    return event


def update_event_from_pulled_event(
    db: Session, existing_event: event_models.Event, pulled_event: MISPEvent
):
    existing_event.date = pulled_event.date
    existing_event.info = pulled_event.info
    existing_event.uuid = pulled_event.uuid
    existing_event.published = pulled_event.published
    existing_event.attribute_count = pulled_event.attribute_count
    existing_event.object_count = len(pulled_event.objects)
    existing_event.analysis = event_models.AnalysisLevel(pulled_event.analysis)
    existing_event.timestamp = pulled_event.timestamp.timestamp() or time.time()
    existing_event.distribution = event_models.DistributionLevel(
        pulled_event.distribution
    )
    existing_event.sharing_group_id = (
        pulled_event.sharing_group_id
        if int(pulled_event.sharing_group_id) > 0
        else None
    )
    existing_event.threat_level = event_models.ThreatLevel(pulled_event.threat_level_id)
    existing_event.disable_correlation = pulled_event.disable_correlation
    existing_event.extends_uuid = pulled_event.extends_uuid or None
    db.commit()
    db.refresh(existing_event)

    tasks.handle_updated_event.delay(existing_event.uuid)

    return existing_event


def update_event(db: Session, event_id: int, event: event_schemas.EventUpdate):
    # TODO: Event::beforeValidate() && Event::$validate
    db_event = get_event_by_id(db, event_id=event_id)

    if db_event is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Event not found"
        )

    event_patch = event.model_dump(exclude_unset=True)
    for key, value in event_patch.items():
        setattr(db_event, key, value)

    db.commit()
    db.refresh(db_event)

    tasks.handle_updated_event.delay(db_event.uuid)

    return db_event


def delete_event(db: Session, event_id: Union[int, UUID], force: bool = False) -> None:

    if isinstance(event_id, int):
        db_event = get_event_by_id(db, event_id=event_id)
    else:
        db_event = get_event_by_uuid(db, event_uuid=event_id)

    if db_event is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Event not found"
        )

    db_event.deleted = True

    if force:
        db.delete(db_event)
        db.commit()
        return

    db.commit()
    db.refresh(db_event)

    tasks.handle_deleted_event.delay(db_event.uuid)


def increment_attribute_count(
    db: Session, event_id: int, attributes_count: int = 1
) -> None:
    db_event = get_event_by_id(db, event_id=event_id)

    if db_event is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Event not found"
        )

    db_event.attribute_count += attributes_count

    db.commit()
    db.refresh(db_event)


def decrement_attribute_count(
    db: Session, event_id: int, attributes_count: int = 1
) -> None:
    db_event = get_event_by_id(db, event_id=event_id)

    if db_event is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Event not found"
        )

    if db_event.attribute_count > 0:
        db_event.attribute_count -= attributes_count
        db.commit()
        db.refresh(db_event)


def increment_object_count(db: Session, event_id: int, objects_count: int = 1) -> None:
    db_event = get_event_by_id(db, event_id=event_id)

    if db_event is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Event not found"
        )

    db_event.object_count += objects_count

    db.commit()
    db.refresh(db_event)


def decrement_object_count(db: Session, event_id: int, objects_count: int = 1) -> None:
    db_event = get_event_by_id(db, event_id=event_id)

    if db_event is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Event not found"
        )

    db_event.object_count -= objects_count

    if db_event.object_count < 0:
        db_event.object_count = 0

    db.commit()
    db.refresh(db_event)


def create_event_from_fetched_event(
    db: Session,
    fetched_event: MISPEvent,
    Orgc: MISPOrganisation,
    feed: feed_models.Feed,
    user: user_schemas.User,
) -> event_models.Event:
    db_event = event_models.Event(
        org_id=user.org_id,
        date=fetched_event.date,
        info=fetched_event.info,
        user_id=user.id,
        uuid=fetched_event.uuid,
        published=fetched_event.published,
        analysis=event_models.AnalysisLevel(fetched_event.analysis),
        object_count=len(fetched_event.objects),
        orgc_id=Orgc.id,
        timestamp=fetched_event.timestamp.timestamp(),
        distribution=feed.distribution,
        sharing_group_id=feed.sharing_group_id,
        locked=(fetched_event.locked if hasattr(fetched_event, "locked") else False),
        threat_level=event_models.ThreatLevel(fetched_event.threat_level_id),
        publish_timestamp=fetched_event.publish_timestamp.timestamp(),
        # sighting_timestamp=fetched_event.sighting_timestamp, # TODO: add sighting_timestamp
        disable_correlation=getattr(fetched_event, "disable_correlation", False),
        extends_uuid=(
            fetched_event.extends_uuid
            if hasattr(fetched_event, "extends_uuid")
            and fetched_event.extends_uuid != ""
            else None
        ),
        # protected=fetched_event.protected # TODO: add protected [pymisp]
    )

    db.add(db_event)

    # process tags
    for tag in fetched_event.tags:
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

        db_event_tag = tag_models.EventTag(
            event=db_event,
            tag=db_tag,
            local=tag.local,
        )
        db.add(db_event_tag)

    # TODO: process galaxies
    # TODO: process reports
    # TODO: process analyst notes

    db.commit()
    db.flush()
    db.refresh(db_event)

    return db_event


def update_event_from_fetched_event(
    db: Session,
    fetched_event: MISPEvent,
    Orgc: MISPOrganisation,
    feed: feed_models.Feed,
    user: user_schemas.User,
) -> event_models.Event:
    db_event = get_event_by_uuid(db, fetched_event.uuid)

    if db_event is None:
        logger.error(f"Event {fetched_event.uuid} not found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Event not found"
        )

    db_event.date = fetched_event.date
    db_event.info = fetched_event.info
    db_event.published = fetched_event.published
    db_event.analysis = event_models.AnalysisLevel(fetched_event.analysis)
    db_event.object_count = len(fetched_event.objects)
    db_event.orgc_id = Orgc.id
    db_event.timestamp = fetched_event.timestamp.timestamp()
    db_event.distribution = feed.distribution
    db_event.sharing_group_id = feed.sharing_group_id
    db_event.locked = (
        fetched_event.locked if hasattr(fetched_event, "locked") else False
    )
    db_event.threat_level = event_models.ThreatLevel(fetched_event.threat_level_id)
    db_event.publish_timestamp = fetched_event.publish_timestamp.timestamp()
    db_event.disable_correlation = getattr(fetched_event, "disable_correlation", False)
    db_event.extends_uuid = (
        fetched_event.extends_uuid
        if hasattr(fetched_event, "extends_uuid") and fetched_event.extends_uuid != ""
        else None
    )

    # process tags
    for tag in fetched_event.tags:
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

        db_event_tag = tag_models.EventTag(
            event=db_event,
            tag=db_tag,
            local=tag.local,
        )
        db.add(db_event_tag)

    # remove tags that are not in fetched event
    event_tags = db.query(tag_models.EventTag).filter(
        tag_models.EventTag.event_id == db_event.id
    )
    for event_tag in event_tags:
        if event_tag.tag.name not in [tag.name in fetched_event.tags]:
            db.delete(event_tag)

    # TODO: process galaxies
    # TODO: process reports
    # TODO: process analyst notes

    db.commit()
    db.flush()
    db.refresh(db_event)

    return db_event


def get_event_uuids(db: Session) -> list[UUID]:
    return db.query(event_models.Event.uuid).all()


def get_events_by_uuids(db: Session, uuids: list[UUID]) -> list[event_models.Event]:
    return (
        db.query(event_models.Event)
        .options(noload("*"))
        .filter(event_models.Event.uuid.in_(uuids))
        .all()
    )


def publish_event(db: Session, db_event: event_models.Event) -> event_models.Event:

    if db_event.published:
        return db_event

    db_event.published = True
    db_event.publish_timestamp = time.time()

    db.commit()
    db.refresh(db_event)

    tasks.handle_published_event.delay(db_event.uuid)

    return db_event


def unpublish_event(db: Session, db_event: event_models.Event) -> event_models.Event:

    if not db_event.published:
        return db_event

    db_event.published = False

    db.commit()
    db.refresh(db_event)

    tasks.handle_unpublished_event.delay(db_event.uuid)

    return db_event


def toggle_event_correlation(
    db: Session, db_event: event_models.Event
) -> event_models.Event:
    db_event.disable_correlation = not db_event.disable_correlation

    db.commit()
    db.refresh(db_event)

    tasks.handle_toggled_event_correlation.delay(
        db_event.uuid, db_event.disable_correlation
    )

    return db_event


def import_data(db: Session, event: event_models.Event, data: dict):

    total_imported_attributes = 0
    total_attributes = 0

    if "attributes" in data:
        total_attributes = len(data["attributes"])

        for raw_attribute in data["attributes"]:
            try:
                attribute = attribute_schemas.AttributeCreate(
                    event_id=event.id,
                    category=raw_attribute.get("category", "External analysis"),
                    type=raw_attribute["type"],
                    value=raw_attribute["value"],
                    distribution=event_schemas.DistributionLevel.INHERIT_EVENT,
                )
                attributes_repository.create_attribute(db, attribute)
                total_imported_attributes += 1
            except Exception as e:
                logger.error(f"Error importing attribute: {e}")
                continue

    return {
        "message": f"Imported {total_imported_attributes} out of {total_attributes} attributes.",
        "imported_attributes": total_imported_attributes,
        "total_attributes": total_attributes,
        "failed_attributes": total_attributes - total_imported_attributes,
        "event_uuid": str(event.uuid),
    }


def get_event_vulnerabilities(
    db: Session,
    event_uuid: str,
) -> list[vulnerability_schemas.Vulnerability]:

    vulnerability_attributes = attributes_repository.get_vulnerability_attributes(
        db, event_uuid=event_uuid
    )

    vulnerabilities = []
    for attribute in vulnerability_attributes:
        vuln_meta = vulnerability_lookup(attribute.value)
        detection_rules = rulezet_lookup(attribute.value)

        vulnerability = vulnerability_schemas.Vulnerability(
            vuln_id=attribute.value,
            attribute_uuid=attribute.uuid,
            description=vuln_meta.get("description", attribute.comment),
            severity=vuln_meta.get("severity", None),
            references=vuln_meta.get("references", None),
            impacted_products=vuln_meta.get("impacted_products", None),
            detection_rules=detection_rules if detection_rules else None,
        )
        vulnerabilities.append(vulnerability)

    return vulnerabilities
