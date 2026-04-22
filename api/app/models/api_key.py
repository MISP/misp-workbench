from datetime import datetime, timezone

from app.database import Base
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import backref, relationship


class ApiKey(Base):
    __tablename__ = "api_keys"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    hashed_token = Column(String(64), unique=True, index=True, nullable=False)
    name = Column(String(255), nullable=False)
    comment = Column(String, nullable=True)
    scopes = Column(JSONB, nullable=False, default=list, server_default="[]")
    expires_at = Column(DateTime(timezone=True), nullable=True)
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    disabled = Column(Boolean, nullable=False, default=False, server_default="false")
    admin_disabled = Column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    user = relationship(
        "User",
        backref=backref("api_keys", cascade="all, delete-orphan"),
    )
