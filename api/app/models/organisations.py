import uuid

from sqlalchemy import Boolean, Column, DateTime, Integer, String
from sqlalchemy.dialects.postgresql import UUID

from .database import Base


class Organisation(Base):
    __tablename__ = "organisations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    description = Column(String)
    date_created = Column(DateTime, nullable=False)
    date_modified = Column(DateTime, nullable=False)
    type = Column(String(255), nullable=False)
    nationality = Column(String(255), nullable=False)
    sector = Column(String(255), nullable=False)
    created_by = Column(Integer, nullable=False)
    uuid = Column(UUID(as_uuid=True), unique=True, default=uuid.uuid4)
    contacts = Column(String)
    local = Column(Boolean, nullable=False)
    restricted_to_domain = Column(String)
    landing_page = Column(String)
