import uuid

from app.database import Base
from app.models.event import DistributionLevel
from sqlalchemy import Boolean, Column, Enum, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship


class Object(Base):
    __tablename__ = "objects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    meta_category = Column(String)
    description = Column(String)
    template_uuid = Column(String)
    template_version = Column(Integer, nullable=False)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False)
    uuid = Column(UUID(as_uuid=True), unique=True, default=uuid.uuid4)
    timestamp = Column(Integer, nullable=False)
    distribution: Mapped[DistributionLevel] = mapped_column(
        Enum(DistributionLevel, name="distribution_level"),
        nullable=False,
        default=DistributionLevel.INHERIT_EVENT,
    )
    sharing_group_id = Column(Integer, ForeignKey("sharing_groups.id"))
    comment = Column(String)
    deleted = Column(Boolean, nullable=False, default=False)
    first_seen = Column(Integer)
    last_seen = Column(Integer)

    attributes = relationship("Attribute", lazy="subquery", cascade="all, delete-orphan")
    object_references = relationship("ObjectReference", lazy="subquery", cascade="all, delete-orphan")

    def to_misp_format(self):
        """Convert the Object to a MISP-compatible dictionary representation."""
        return {
            "id": self.id,
            "name": self.name,
            "meta_category": self.meta_category,
            "description": self.description,
            "template_uuid": self.template_uuid,
            "template_version": self.template_version,
            "event_id": self.event_id,
            "uuid": str(self.uuid),
            "timestamp": self.timestamp,
            "distribution": self.distribution.name if self.distribution else None,
            "sharing_group_id": self.sharing_group_id,
            "comment": self.comment,
            "deleted": self.deleted,
            "first_seen": self.first_seen,
            "last_seen": self.last_seen,
            "Attributes": [attribute.to_misp_format() for attribute in self.attributes],
            "ObjectReference": [ref.to_misp_format() for ref in self.object_references],
        }