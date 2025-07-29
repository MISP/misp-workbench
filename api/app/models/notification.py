from app.database import Base
from sqlalchemy import (
    Boolean,
    Column,
    ForeignKey,
    Integer,
    String,
    DateTime,
    JSON,
)
from sqlalchemy.dialects.postgresql import UUID

class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    type = Column(String, nullable=False)
    entity_type = Column(String(255))
    entity_uuid = Column(UUID(as_uuid=True), unique=False, nullable=False)
    read = Column(Boolean, default=False)
    title = Column(String(255), nullable=False)
    payload = Column(JSON, nullable=False, default={})
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=True)
