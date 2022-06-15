import time

from sqlalchemy.orm import Session

from ..models import object as object_models
from ..schemas import object as object_schemas


def get_objects(db: Session, skip: int = 0, limit: int = 100):
    return db.query(object_models.Object).offset(skip).limit(limit).all()


def get_object_by_id(db: Session, object_id: int):
    return (
        db.query(object_models.Object)
        .filter(object_models.Object.id == object_id)
        .first()
    )


def create_object(db: Session, object: object_schemas.ObjectCreate):
    db_object = object_models.Object(
        event_id=object.event_id,
        name=object.name,
        meta_category=object.meta_category,
        description=object.description,
        template_uuid=object.template_uuid,
        template_version=object.template_version,
        uuid=object.uuid,
        timestamp=object.timestamp or time.time(),
        distribution=object.distribution,
        sharing_group_id=object.sharing_group_id,
        comment=object.comment,
        deleted=object.deleted,
        first_seen=object.first_seen,
        last_seen=object.last_seen,
    )

    db.add(db_object)
    db.commit()
    db.refresh(db_object)

    return db_object
