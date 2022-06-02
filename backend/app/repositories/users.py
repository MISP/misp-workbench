import logging
from ..models import user as user_models
from ..schemas import user as user_schemas
from sqlalchemy.orm import Session
from hashlib import sha256
from ..auth import auth

logger = logging.getLogger(__name__)


def get_users(db: Session, skip: int = 0, limit: int = 100):
    return db.query(user_models.User).offset(skip).limit(limit).all()


def get_user_by_id(db: Session, user_id: int):
    return db.query(user_models.User).filter(user_models.User.id == user_id).first()


def get_user_by_email(db: Session, email: str):
    return db.query(user_models.User).filter(user_models.User.email == email).first()


def get_user_by_token(db: Session, token: str):
    # TODO: FIXME
    return db.query(user_models.User).filter(user_models.User.email == token).first()


def create_user(db: Session, user: user_schemas.UserCreate):
    hashed_password = auth.get_password_hash(user.password)
    db_user = user_models.User(
        org_id=user.org_id,
        role_id=user.role_id,
        email=user.email,
        hashed_password=hashed_password)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    return db_user
