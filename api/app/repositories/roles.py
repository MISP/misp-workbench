from sqlalchemy.orm import Session

from ..models import role as role_models


def get_roles(db: Session, skip: int = 0, limit: int = 100):
    return db.query(role_models.Role).offset(skip).limit(limit).all()
