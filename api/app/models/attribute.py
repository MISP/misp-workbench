from email.policy import default

from .database import Base
from sqlalchemy import BigInteger, Boolean, Column, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid


class Attribute(Base):
    __tablename__ = "attributes"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True, nullable=False)
    event_id = Column(Integer, ForeignKey("events.id"), index=True, nullable=False)
    # TODO: ForeignKey("objects.id")
    object_id = Column(Integer, index=True, nullable=True)
    object_relation = Column(String(255), index=True)
    category = Column(String(255), index=True)
    type = Column(String(100), index=True)
    value = Column(String(), index=True)
    to_ids = Column(Boolean, default=True)
    uuid = Column(UUID(as_uuid=True), unique=True, default=uuid.uuid4)
    timestamp = Column(Integer, nullable=False, default=0)
    distribution = Column(Integer, nullable=False, default=0)
    # TODO: ForeignKey("sharing_groups.id"),
    sharing_group_id = Column(Integer, index=True, nullable=True)
    comment = Column(String())
    deleted = Column(Boolean, default=False)
    disable_correlation = Column(Boolean, default=False)
    first_seen = Column(BigInteger(), index=True)
    last_seen = Column(BigInteger(), index=True)
