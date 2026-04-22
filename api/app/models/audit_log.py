from datetime import datetime, timezone

from app.database import Base
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import INET, JSONB
from sqlalchemy.orm import relationship


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
        default=lambda: datetime.now(timezone.utc),
    )
    # Who performed the action. Null means the system (e.g. a scheduled task).
    actor_user_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    # How the actor authenticated: "user", "api_key", "system".
    actor_type = Column(String(32), nullable=False)
    # Optional pointer to the authenticating credential (e.g. api_key.id).
    actor_credential_id = Column(Integer, nullable=True)

    # Generic resource addressing: resource_type is a free-form tag
    # (e.g. "api_key", "event"); resource_id is the numeric PK when applicable.
    resource_type = Column(String(64), nullable=False, index=True)
    resource_id = Column(Integer, nullable=True, index=True)

    # Action verb, namespaced by resource (e.g. "api_key.created",
    # "api_key.authenticated"). Namespacing lets consumers filter by feature.
    action = Column(String(128), nullable=False, index=True)

    ip_address = Column(INET, nullable=True)
    user_agent = Column(String(512), nullable=True)

    # Action-specific payload. Never include raw credentials.
    metadata_ = Column("metadata", JSONB, nullable=True)

    actor = relationship("User", foreign_keys=[actor_user_id])
