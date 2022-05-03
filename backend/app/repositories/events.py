from datetime import date
from datetime import datetime
import time
from ..models import event as event_models
from ..schemas import event as event_schemas
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
    return db.query(event_models.Event).filter(event_models.Event.id == event_id).first()


def create_event(db: Session, event: event_schemas.EventCreate):
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
        protected=event.protected
    )
    db.add(db_event)
    db.commit()
    db.refresh(db_event)
    return db_event
