from sqlalchemy import Column, Integer, String, Boolean, JSON

from .database import Base


class Server(Base):
    __tablename__ = "servers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True)
    url = Column(String, nullable=False)
    authkey = Column(String, nullable=False)  # TODO: encrypted
    org_id = Column(Integer, nullable=False)  # TODO: foreign key to organisations
    push = Column(Boolean, nullable=False, default=False)
    pull = Column(Boolean, nullable=False, default=False)
    push_sightings = Column(Boolean, nullable=False, default=False)
    push_galaxy_clusters = Column(Boolean, nullable=False, default=False)
    pull_galaxy_clusters = Column(Boolean, nullable=False, default=False)
    lastpulledid = Column(Integer, nullable=True)
    lastpushedid = Column(Integer, nullable=True)
    organisation = Column(String)
    remote_org_id = Column(Integer, nullable=False)
    publish_without_email = Column(Boolean, nullable=False, default=False)
    unpublish_event = Column(Boolean, nullable=False, default=False)
    self_signed = Column(Boolean, nullable=False, default=False)
    pull_rules = Column(JSON, nullable=False, default={})
    push_rules = Column(JSON, nullable=False, default={})
    cert_file = Column(String)
    client_cert_file = Column(String)
    internal = Column(Boolean, nullable=False, default=False)
    skip_proxy = Column(Boolean, nullable=False, default=False)
    caching_enabled = Column(Boolean, nullable=False, default=False)
    priority = Column(Integer, nullable=False, default=0)
