from datetime import datetime, timezone

from app.database import Base
from sqlalchemy import JSON, Boolean, Column, DateTime, ForeignKey, Integer, String


class Server(Base):
    __tablename__ = "servers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True)
    # When it was added; unknown for servers added before this was recorded.
    created_at = Column(
        DateTime(timezone=True),
        nullable=True,
        default=lambda: datetime.now(timezone.utc),
    )
    url = Column(String, nullable=False)
    authkey = Column(String, nullable=False)  # TODO: encrypted
    org_id = Column(Integer, ForeignKey("organisations.id"), nullable=False)
    push = Column(Boolean, nullable=False, default=False)
    pull = Column(Boolean, nullable=False, default=False)
    push_sightings = Column(Boolean, nullable=False, default=False)
    push_galaxy_clusters = Column(Boolean, nullable=False, default=False)
    pull_galaxy_clusters = Column(Boolean, nullable=False, default=False)
    last_pulled_id = Column(Integer, nullable=True)
    last_pushed_id = Column(Integer, nullable=True)
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
    # Indicator scoring: points added to (or taken off) the score of what
    # this source reports, and an optional ceiling for it.
    score_modifier = Column(Integer, nullable=False, default=0, server_default="0")
    score_cap = Column(Integer, nullable=True)
