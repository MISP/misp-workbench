import time
from datetime import datetime

from app.models import event as event_models
from app.schemas import event as event_schemas
from fastapi import HTTPException, status
from pymisp import MISPEvent
from sqlalchemy.orm import Session


def get_events(db: Session, skip: int = 0, limit: int = 100, filters: dict = {}):
    query = db.query(event_models.Event)

    if filters["id"]:
        query = query.filter(event_models.Event.id == filters["id"])

    if filters["info"]:
        search = "%{}%".format(filters["info"])
        query = query.filter(event_models.Event.info.like(search))

    return query.offset(skip).limit(limit).all()


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


def create_event(db: Session, event: event_schemas.EventCreate):
    # TODO: Event::beforeValidate() && Event::$validate
    db_event = event_models.Event(
        org_id=event.org_id,
        date=event.date or datetime.now(),
        info=event.info,
        user_id=event.user_id,
        uuid=event.uuid,
        published=event.published,
        analysis=event.analysis,
        attribute_count=event.attribute_count,
        orgc_id=event.orgc_id or event.org_id,
        timestamp=event.timestamp or time.time(),
        distribution=event.distribution,
        sharing_group_id=event.sharing_group_id,
        proposal_email_lock=event.proposal_email_lock,
        locked=event.locked,
        threat_level_id=event.threat_level_id,
        publish_timestamp=event.publish_timestamp,
        sighting_timestamp=event.sighting_timestamp,
        disable_correlation=event.disable_correlation,
        extends_uuid=event.extends_uuid,
        protected=event.protected,
    )
    db.add(db_event)
    db.commit()
    db.refresh(db_event)

    return db_event


def create_event_from_pulled_event(db: Session, pulled_event: MISPEvent):
    event = event_models.Event(
        org_id=pulled_event.org_id,
        date=pulled_event.date,
        info=pulled_event.info,
        user_id=pulled_event.user_id,
        uuid=pulled_event.uuid,
        published=pulled_event.published,
        analysis=pulled_event.analysis,
        attribute_count=pulled_event.attribute_count,
        orgc_id=pulled_event.orgc_id,
        timestamp=pulled_event.timestamp.timestamp(),
        distribution=event_models.DistributionLevel(pulled_event.distribution),
        sharing_group_id=pulled_event.sharing_group_id
        if int(pulled_event.sharing_group_id) > 0
        else None,
        proposal_email_lock=pulled_event.proposal_email_lock,
        locked=pulled_event.locked,
        threat_level_id=pulled_event.threat_level_id,
        publish_timestamp=pulled_event.publish_timestamp.timestamp(),
        # sighting_timestamp=pulled_event.sighting_timestamp, # TODO: add sighting_timestamp
        disable_correlation=pulled_event.disable_correlation,
        extends_uuid=pulled_event.extends_uuid or None,
        # protected=pulled_event.protected # TODO: add protected
    )
    db.add(event)
    db.commit()
    db.refresh(event)

    return event


def update_event_from_pulled_event(
    db: Session, existing_event: event_models.Event, pulled_event: MISPEvent
):
    existing_event.date = pulled_event.date
    existing_event.info = pulled_event.info
    existing_event.uuid = pulled_event.uuid
    existing_event.published = pulled_event.published
    existing_event.analysis = pulled_event.analysis
    existing_event.timestamp = pulled_event.timestamp.timestamp() or time.time()
    existing_event.distribution = event_models.DistributionLevel(
        pulled_event.distribution
    )
    existing_event.sharing_group_id = pulled_event.sharing_group_id
    existing_event.threat_level_id = pulled_event.threat_level_id
    existing_event.disable_correlation = pulled_event.disable_correlation
    existing_event.extends_uuid = pulled_event.extends_uuid or None
    db.add(existing_event)  # updates if exists
    db.commit()
    db.refresh(existing_event)

    return existing_event


def update_event(db: Session, event_id: int, event: event_schemas.EventUpdate):
    # TODO: Event::beforeValidate() && Event::$validate
    db_event = get_event_by_id(db, event_id=event_id)

    if db_event is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Event not found"
        )

    event_patch = event.dict(exclude_unset=True)
    for key, value in event_patch.items():
        setattr(db_event, key, value)

    db.add(db_event)
    db.commit()
    db.refresh(db_event)

    return db_event


def delete_event(db: Session, event_id: int) -> None:
    db_event = get_event_by_id(db, event_id=event_id)

    if db_event is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Event not found"
        )

    db_event.deleted = True

    db.add(db_event)
    db.commit()
    db.refresh(db_event)
