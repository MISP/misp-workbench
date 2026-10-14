from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.database import Base


class AlertReceiver(Base):
    """An inbound alert webhook: a SIEM or SOAR posts its alerts, in its own
    shape, to /webhooks/alerts/{token}, and ``mapping`` (JMESPath) reads the
    values they hit out of them, reported as sightings by its organisation.
    """

    __tablename__ = "alert_receivers"
    __table_args__ = (UniqueConstraint("org_id", "name"),)

    id = Column(Integer, primary_key=True, index=True)
    org_id = Column(
        Integer,
        ForeignKey("organisations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    # The sender it was set up for (splunk, elastic, ...), or generic.
    preset = Column(String(32), nullable=False, default="generic")
    # JMESPath expressions: records, values, type, source, timestamp,
    # attribute_uuid (see app.repositories.alert_receivers).
    mapping = Column(JSON, nullable=False)
    # Only values some attribute holds are reported: an alert also carries
    # the internal hosts it was raised for.
    only_known = Column(Boolean, nullable=False, default=True)
    # Requests a minute; past it the sender gets a 429.
    rate_limit = Column(Integer, nullable=False, default=120)
    enabled = Column(Boolean, nullable=False, default=True)
    # Addresses or networks it accepts alerts from; empty: anywhere.
    allowed_ips = Column(JSON, nullable=False, default=list)

    # The token is in the URL; only its SHA-256 is kept.
    token_prefix = Column(String(16), nullable=False)
    token_hash = Column(String(64), nullable=False, unique=True, index=True)

    last_received_at = Column(DateTime(timezone=True), nullable=True)
    last_ip = Column(String(64), nullable=True)
    received_count = Column(Integer, nullable=False, default=0)
    sightings_count = Column(Integer, nullable=False, default=0)
    # Why the last request was refused (mapping, size, JSON), if it was.
    last_error = Column(Text, nullable=True)
    last_error_at = Column(DateTime(timezone=True), nullable=True)
    # The last body received, cut short, to test the mapping against.
    last_payload = Column(Text, nullable=True)

    created_by = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at = Column(DateTime(timezone=True), nullable=False)
    updated_at = Column(DateTime(timezone=True), nullable=True)

    # Sightings are reported as this organisation's.
    organisation = relationship("Organisation", lazy="joined")
