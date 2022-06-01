import logging
from ..models import user as user_models
from ..schemas import user as user_schemas
from sqlalchemy.orm import Session
from hashlib import sha256

logger = logging.getLogger(__name__)

def get_users(db: Session, skip: int = 0, limit: int = 100):
    return db.query(user_models.User).offset(skip).limit(limit).all()


def get_user_by_id(db: Session, user_id: int):
    return db.query(user_models.User).filter(user_models.User.id == user_id).first()


def get_user_by_email(db: Session, email: str):
    return db.query(user_models.User).filter(user_models.User.email == email).first()


def create_user(db: Session, user: user_schemas.UserCreate):
    # TODO set salt via env variable
    hashed_password = sha256((user.password + "salt").encode()).hexdigest()
    db_user = user_models.User(
        org_id=user.org_id,
        role_id=user.role_id,
        email=user.email,
        hashed_password=hashed_password)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    return db_user
