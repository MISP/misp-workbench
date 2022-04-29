from ..models import event
from sqlalchemy.orm import Session


def get_events(db: Session, skip: int = 0, limit: int = 100, filters: dict = {}):
    query = db.query(event.Event)

    if filters["id"]:
        query = query.filter(event.Event.id == filters["id"])

    if filters["info"]:
        search = "%{}%".format(filters["info"])
        query = query.filter(event.Event.info.like(search))

    return query.offset(skip).limit(limit).all()


def get_event_by_id(db: Session, event_id: int):
    return db.query(event.Event).filter(event.Event.id == event_id).first()
