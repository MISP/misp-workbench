import enum
import uuid

from app.database import Base
from sqlalchemy import Boolean, Column, Enum, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column


class ReferencedType(enum.Enum):
    """
    Enum for the Referenced Entity Type
    """

    ATTRIBUTE = 0
    OBJECT = 1


class ObjectReference(Base):
    __tablename__ = "object_references"

    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(UUID(as_uuid=True), unique=True, default=uuid.uuid4)
    timestamp = Column(Integer, nullable=False)
    object_id = Column(Integer, ForeignKey("objects.id"), nullable=False)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False)
    source_uuid = Column(UUID(as_uuid=True))
    referenced_uuid = Column(UUID(as_uuid=True))
    referenced_id = Column(Integer, nullable=True)
    referenced_type: Mapped[ReferencedType] = mapped_column(
        Enum(ReferencedType, name="referenced_type"), nullable=False
    )
    relationship_type = Column(String)
    comment = Column(String, nullable=False)
    deleted = Column(Boolean, nullable=False, default=False)

    def to_misp_format(self):
        """Convert the ObjectReference to a MISP-compatible dictionary representation."""
        return {
            "id": self.id,
            "uuid": str(self.uuid),
            "timestamp": self.timestamp,
            "object_id": self.object_id,
            "event_id": self.event_id,
            "source_uuid": str(self.source_uuid) if self.source_uuid else None,
            "referenced_uuid": str(self.referenced_uuid) if self.referenced_uuid else None,
            "referenced_id": self.referenced_id,
            "referenced_type": self.referenced_type.name if self.referenced_type else None,
            "relationship_type": self.relationship_type,
            "comment": self.comment,
            "deleted": self.deleted,
        }