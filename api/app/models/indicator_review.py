from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from app.database import Base


class IndicatorReview(Base):
    """An analyst's decision on an indicator: approved, rejected or snoozed.

    Keyed by the indicator's uuid, which derives from its type and value: a
    decision holds for the value whichever sources report it, and outlives
    the indicator (a rejected value that comes back is still rejected).
    ``pending`` is a decision taken back. Every decision is also in the
    audit log (``indicator_review.*``).
    """

    __tablename__ = "indicator_reviews"

    id = Column(Integer, primary_key=True, index=True)
    indicator_uuid = Column(String(36), nullable=False, unique=True, index=True)
    type = Column(String(128), nullable=False)
    value = Column(Text, nullable=False)
    status = Column(String(16), nullable=False, index=True)
    reason = Column(Text, nullable=True)
    snoozed_until = Column(DateTime(timezone=True), nullable=True)
    # Rejected with an entry in the local allowlist warninglist.
    allowlisted = Column(Boolean, nullable=False, default=False, server_default="false")
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    decided_at = Column(DateTime(timezone=True), nullable=False, index=True)

    user = relationship("User", foreign_keys=[user_id])
