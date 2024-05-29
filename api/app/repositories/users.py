import logging

from app.auth import auth
from app.models import user as user_models
from app.schemas import user as user_schemas
from app.worker import tasks
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


def get_users(db: Session, skip: int = 0, limit: int = 100):
    return db.query(user_models.User).offset(skip).limit(limit).all()


def get_user_by_id(db: Session, user_id: int):
    return db.query(user_models.User).filter(user_models.User.id == user_id).first()


def get_user_by_email(db: Session, email: str):
    return db.query(user_models.User).filter(user_models.User.email == email).first()


def create_user(db: Session, user: user_schemas.UserCreate):

    if user.password is None:
        user.password = auth.get_random_password()

    hashed_password = auth.get_password_hash(user.password)
    db_user = user_models.User(
        org_id=user.org_id,
        role_id=user.role_id,
        email=user.email,
        hashed_password=hashed_password,
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    tasks.send_email(
        {
            "subject": "misp-lite password",
            "body": f"your password is: {user.password}",
            "to": user.email,
            "from": "info@misp-lite.com",
        }
    )

    return db_user


def update_user(
    db: Session,
    user_id: int,
    user: user_schemas.UserUpdate,
) -> user_models.User:
    # TODO: User::beforeValidate() && User::$validate
    db_user = get_user_by_id(db, user_id=user_id)

    if db_user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    user_patch = user.model_dump(exclude_unset=True)
    for key, value in user_patch.items():
        setattr(db_user, key, value)

    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    return db_user


def delete_user(db: Session, user_id: int) -> None:
    db_user = get_user_by_id(db, user_id=user_id)

    if db_user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    db.delete(db_user)
    db.commit()
