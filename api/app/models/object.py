import uuid

from sqlalchemy import Boolean, Column, Enum, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from .database import Base
from .event import DistributionLevel


class Object(Base):
    __tablename__ = "objects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    meta_category = Column(String)
    description = Column(String)
    template_uuid = Column(UUID(as_uuid=True), unique=True)
    template_version = Column(Integer, nullable=False)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False)
    uuid = Column(UUID(as_uuid=True), unique=True, default=uuid.uuid4)
    timestamp = Column(Integer, nullable=False)
    distribution = Column(
        Enum(DistributionLevel),
        nullable=False,
        default=DistributionLevel.INHERIT_EVENT,
    )
    sharing_group_id = Column(Integer)
    comment = Column(String)
    deleted = Column(Boolean, nullable=False, default=False)
    first_seen = Column(Integer)
    last_seen = Column(Integer)

    attributes = relationship("Attribute")
    object_references = relationship("ObjectReference")
