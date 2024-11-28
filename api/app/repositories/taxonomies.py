from app.models import taxonomy as taxonomies_models
from sqlalchemy.orm import Session


def get_taxonomies(db: Session, skip: int = 0, limit: int = 100):
    return db.query(taxonomies_models.Taxonomy).offset(skip).limit(limit).all()
