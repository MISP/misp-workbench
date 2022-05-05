from .database import Base
from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Date
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid


class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True,
                autoincrement=True, nullable=False)
    org_id = Column(Integer, index=True, nullable=False)
    date = Column(Date, nullable=False)
    info = Column(String, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    uuid = Column(UUID(as_uuid=True), unique=True, default=uuid.uuid4)
    published = Column(Boolean, default=False, nullable=False)
    analysis = Column(Integer)
    attribute_count = Column(Integer, default=0)
    # TODO: ForeignKey("organisations.id"),
    orgc_id = Column(Integer, index=True, nullable=False)
    timestamp = Column(Integer, nullable=False, default=0)
    distribution = Column(Integer, nullable=False, default=0)
    # TODO: ForeignKey("sharing_groups.id"),
    sharing_group_id = Column(Integer, index=True, nullable=True)
    proposal_email_lock = Column(Boolean, nullable=False, default=False)
    locked = Column(Boolean, nullable=False, default=False)
    threat_level_id = Column(Integer, nullable=False, default=0)
    publish_timestamp = Column(Integer, nullable=False, default=0)
    sighting_timestamp = Column(Integer)
    disable_correlation = Column(Boolean, default=False)
    # TODO: ForeignKey("organisations.uuid"),
    extends_uuid = Column(UUID(as_uuid=True), index=True, nullable=True)
    protected = Column(Boolean, nullable=False, default=False)

    attributes = relationship("Attribute")
