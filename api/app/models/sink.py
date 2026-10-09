from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    Column,
    DateTime,
    Integer,
    String,
    Text,
)

from app.database import Base


class Sink(Base):
    """An outbound destination indicators are pushed to when an event is published.

    ``type`` selects the protocol (Splunk HEC, GELF, syslog/CEF, webhook) and
    the shape of ``config``; ``filters`` selects which attributes of a
    published event are sent. Delivery runs on the dedicated ``sinks`` Celery
    queue, and its outcome is kept on the row so it can be shown in the UI.
    """

    __tablename__ = "sinks"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    type = Column(String(32), nullable=False)
    enabled = Column(Boolean, nullable=False, default=True, server_default="true")
    config = Column(JSON, nullable=False, default=dict)
    filters = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), nullable=False)
    updated_at = Column(DateTime(timezone=True), nullable=True)

    # Delivery status.
    last_attempt_at = Column(DateTime(timezone=True), nullable=True)
    last_success_at = Column(DateTime(timezone=True), nullable=True)
    last_error = Column(Text, nullable=True)
    last_error_at = Column(DateTime(timezone=True), nullable=True)
    # Attributes delivered over the sink's lifetime.
    delivered_count = Column(BigInteger, nullable=False, default=0, server_default="0")
    # Deliveries that failed for good, after their retries ran out.
    failed_count = Column(Integer, nullable=False, default=0, server_default="0")
