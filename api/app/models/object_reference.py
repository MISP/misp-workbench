import uuid

from sqlalchemy import Boolean, Column, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID

from .database import Base


class ObjectReference(Base):
    __tablename__ = "object_references"

    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(UUID(as_uuid=True), unique=True, default=uuid.uuid4)
    timestamp = Column(Integer, nullable=False)
    object_id = Column(Integer, ForeignKey("objects.id"), nullable=False)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False)
    source_uuid = Column(UUID(as_uuid=True))
    referenced_uuid = Column(UUID(as_uuid=True))
    referenced_id = Column(Integer, nullable=False)
    referenced_type = Column(Integer, nullable=False)
    relationship_type = Column(String)
    comment = Column(String, nullable=False)
    deleted = Column(Boolean, nullable=False, default=False)
