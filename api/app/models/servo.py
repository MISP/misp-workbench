from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB

from app.database import Base


class Servo(Base):
    """A user-authored OpenSearch ingest pipeline (Tech Lab transformation servo).

    Postgres is the source of truth: ``processors`` is compiled into an
    ``_ingest/pipeline`` named ``servo_<slug>`` and referenced from the
    API-owned chain pipeline. See ``app.services.tech_lab.servos.chain``.
    """

    __tablename__ = "servos"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    name = Column(String(255), nullable=False)
    slug = Column(String(255), nullable=False, unique=True, index=True)
    description = Column(Text, nullable=True)
    processors = Column(JSONB, nullable=False, default=list, server_default="[]")
    target_index = Column(String(255), nullable=False, default="misp-attributes")
    enabled = Column(Boolean, nullable=False, default=True, server_default="true")
    position = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), nullable=False)
    updated_at = Column(DateTime(timezone=True), nullable=True)
    last_synced_at = Column(DateTime(timezone=True), nullable=True)
