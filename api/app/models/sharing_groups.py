import uuid

from app.database import Base
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID


class SharingGroup(Base):
    __tablename__ = "sharing_groups"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    releasability = Column(String)
    description = Column(String)
    uuid = Column(UUID(as_uuid=True), unique=True, default=uuid.uuid4)
    organisation_uuid = Column(UUID(as_uuid=True))
    org_id = Column(Integer, ForeignKey("organisations.id"), nullable=False)
    sync_user_id = Column(Integer, ForeignKey("users.id"))
    active = Column(Boolean, nullable=False, default=True)
    created = Column(DateTime, nullable=False)
    modified = Column(DateTime, nullable=False)
    local = Column(Boolean, nullable=False, default=False)
    roaming = Column(Boolean, nullable=False, default=False)


class SharingGroupOrg:
    __tablename__ = "sharing_group_orgs"

    id = Column(Integer, primary_key=True, index=True)
    sharing_group_id = Column(Integer, ForeignKey("sharing_groups.id"), nullable=False)
    org_id = Column(Integer, ForeignKey("organisations.id"), nullable=False)
    extend = Column(Boolean, nullable=False, default=False)


class SharingGroupServers:
    __tablename__ = "sharing_group_servers"

    id = Column(Integer, primary_key=True, index=True)
    sharing_group_id = Column(Integer, ForeignKey("sharing_groups.id"), nullable=False)
    server_id = Column(Integer, ForeignKey("servers.id"), nullable=False)
    all_orgs = Column(Boolean, nullable=False, default=False)
