from app.models import tag as tag_models
from sqlalchemy.orm import Session


def get_tags(db: Session, skip: int = 0, limit: int = 100):
    return db.query(tag_models.Tag).offset(skip).limit(limit).all()
