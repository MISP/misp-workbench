from ..models import attribute as attribute_models
from ..schemas import attribute as attribute_schemas
from sqlalchemy.orm import Session
import time


def get_attributes(db: Session, skip: int = 0, limit: int = 100):
    return db.query(attribute_models.Attribute).offset(skip).limit(limit).all()


def get_attribute_by_id(db: Session, attribute_id: int):
    return db.query(attribute_models.Attribute).filter(attribute_models.Attribute.id == attribute_id).first()


def create_attribute(db: Session, attribute: attribute_schemas.AttributeCreate):
    db_attribute = attribute_models.Attribute(
        event_id=attribute.event_id,
        object_id=attribute.object_id,
        object_relation=attribute.object_relation,
        category=attribute.category,
        type=attribute.type,
        value1=attribute.value1,
        value2=attribute.value2,
        to_ids=attribute.to_ids,
        uuid=attribute.uuid,
        timestamp=attribute.timestamp or time.time(),
        distribution=attribute.distribution,
        sharing_group_id=attribute.sharing_group_id,
        comment=attribute.comment,
        deleted=attribute.deleted,
        disable_correlation=attribute.disable_correlation,
        first_seen=attribute.first_seen,
        last_seen=attribute.last_seen
    )
    db.add(db_attribute)
    db.commit()
    db.refresh(db_attribute)
    return db_attribute
