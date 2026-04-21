import hashlib
import secrets
from datetime import datetime, timezone
from typing import Optional

from app.models import api_key as api_key_models
from sqlalchemy.orm import Session

TOKEN_BYTES = 20  # 40 hex chars, MISP-compatible auth key format


def generate_token() -> str:
    return secrets.token_hex(TOKEN_BYTES)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def list_keys_for_user(db: Session, user_id: int) -> list[api_key_models.ApiKey]:
    return (
        db.query(api_key_models.ApiKey)
        .filter(api_key_models.ApiKey.user_id == user_id)
        .order_by(api_key_models.ApiKey.created_at.desc())
        .all()
    )


def get_key_by_id(
    db: Session, key_id: int, user_id: Optional[int] = None
) -> Optional[api_key_models.ApiKey]:
    q = db.query(api_key_models.ApiKey).filter(api_key_models.ApiKey.id == key_id)
    if user_id is not None:
        q = q.filter(api_key_models.ApiKey.user_id == user_id)
    return q.first()


def get_key_by_token(
    db: Session, token: str
) -> Optional[api_key_models.ApiKey]:
    return (
        db.query(api_key_models.ApiKey)
        .filter(api_key_models.ApiKey.hashed_token == hash_token(token))
        .first()
    )


def create_key(
    db: Session,
    user_id: int,
    name: str,
    scopes: list[str],
    comment: Optional[str] = None,
    expires_at: Optional[datetime] = None,
) -> tuple[api_key_models.ApiKey, str]:
    raw_token = generate_token()
    db_key = api_key_models.ApiKey(
        user_id=user_id,
        hashed_token=hash_token(raw_token),
        name=name,
        comment=comment,
        scopes=scopes,
        expires_at=expires_at,
    )
    db.add(db_key)
    db.commit()
    db.refresh(db_key)
    return db_key, raw_token


def delete_key(db: Session, db_key: api_key_models.ApiKey) -> None:
    db.delete(db_key)
    db.commit()


def touch_last_used(db: Session, db_key: api_key_models.ApiKey) -> None:
    db_key.last_used_at = datetime.now(timezone.utc)
    db.add(db_key)
    db.commit()
