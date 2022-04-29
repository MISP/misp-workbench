from ..models import user
from sqlalchemy.orm import Session


def get_users(db: Session, skip: int = 0, limit: int = 100):
    return db.query(user.User).offset(skip).limit(limit).all()


def get_user_by_id(db: Session, user_id: int):
    return db.query(user.User).filter(user.User.id == user_id).first()
