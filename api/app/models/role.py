from app.database import Base
from sqlalchemy import Boolean, Column, DateTime, Integer, String
from sqlalchemy.dialects.postgresql import JSONB


class Role(Base):
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True)
    created = Column(DateTime)
    modified = Column(DateTime)
    scopes = Column(JSONB, nullable=False, default=list, server_default="[]")
    default_role = Column(Boolean, nullable=False, default=False)
