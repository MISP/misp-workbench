import enum
import uuid

from app.database import Base
from sqlalchemy import Boolean, Column, Date, Enum, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship


class DistributionLevel(enum.Enum):
    """
    Enum for the Event distribution level
    """

    ORGANISATION_ONLY = 0
    COMMUNITY_ONLY = 1
    CONNECTED_COMMUNITIES = 2
    ALL_COMMUNITIES = 3
    SHARING_GROUP = 4
    INHERIT_EVENT = 5


class Event(Base):
    __tablename__ = "events"

    id = Column(
        Integer, primary_key=True, index=True, autoincrement=True, nullable=False
    )
    org_id = Column(Integer, ForeignKey("organisations.id"), index=True, nullable=False)
    date = Column(Date, nullable=False)
    info = Column(String, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    uuid = Column(UUID(as_uuid=True), unique=True, default=uuid.uuid4)
    published = Column(Boolean, default=False, nullable=False)
    analysis = Column(Integer)
    attribute_count = Column(Integer, default=0)
    orgc_id = Column(
        Integer, ForeignKey("organisations.id"), index=True, nullable=False
    )
    timestamp = Column(Integer, nullable=False, default=0)
    distribution = Column(
        Enum(DistributionLevel),
        nullable=False,
        default=DistributionLevel.ORGANISATION_ONLY,
    )
    sharing_group_id = Column(
        Integer, ForeignKey("sharing_groups.id"), index=True, nullable=True
    )
    proposal_email_lock = Column(Boolean, nullable=False, default=False)
    locked = Column(Boolean, nullable=False, default=False)
    threat_level_id = Column(Integer, nullable=False, default=0)
    publish_timestamp = Column(Integer, nullable=False, default=0)
    sighting_timestamp = Column(Integer, nullable=True)
    disable_correlation = Column(Boolean, default=False)
    extends_uuid = Column(UUID(as_uuid=True), index=True, nullable=True)
    protected = Column(Boolean, nullable=False, default=False)

    attributes = relationship("Attribute")
    objects = relationship("Object")
