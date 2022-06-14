from sqlalchemy import Boolean, Column, DateTime, Integer, String

from .database import Base


class Role(Base):
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True)
    created = Column(DateTime)
    modified = Column(DateTime)
    perm_add = Column(Boolean, nullable=False, default=False)
    perm_modify = Column(Boolean, nullable=False, default=False)
    perm_modify_org = Column(Boolean, nullable=False, default=False)
    perm_publish = Column(Boolean, nullable=False, default=False)
    perm_delegate = Column(Boolean, nullable=False, default=False)
    perm_sync = Column(Boolean, nullable=False, default=False)
    perm_admin = Column(Boolean, nullable=False, default=False)
    perm_audit = Column(Boolean, nullable=False, default=False)
    perm_full = Column(Boolean, nullable=False, default=False)
    perm_auth = Column(Boolean, nullable=False, default=False)
    perm_site_admin = Column(Boolean, nullable=False, default=False)
    perm_regexp_access = Column(Boolean, nullable=False, default=False)
    perm_tagger = Column(Boolean, nullable=False, default=False)
    perm_template = Column(Boolean, nullable=False, default=False)
    perm_sharing_group = Column(Boolean, nullable=False, default=False)
    perm_tag_editor = Column(Boolean, nullable=False, default=False)
    perm_sighting = Column(Boolean, nullable=False, default=False)
    perm_object_template = Column(Boolean, nullable=False, default=False)
    perm_galaxy_editor = Column(Boolean, nullable=False, default=False)
    perm_warninglist = Column(Boolean, nullable=False, default=False)
    perm_publish_zmq = Column(Boolean, nullable=False, default=False)
    perm_publish_kafka = Column(Boolean, nullable=False, default=False)
    perm_decaying = Column(Boolean, nullable=False, default=False)
    default_role = Column(Boolean, nullable=False, default=False)
    restricted_to_site_admin = Column(Boolean, nullable=False, default=False)
    enforce_rate_limit = Column(Boolean, nullable=False, default=False)
    rate_limit_count = Column(Integer, nullable=False, default=0)
    memory_limit = Column(String, nullable=False, default="")
    max_execution_time = Column(String, nullable=False, default="")
