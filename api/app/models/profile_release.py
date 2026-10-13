from sqlalchemy import JSON, Column, DateTime, ForeignKey, Integer, String

from app.database import Base


class ProfileRelease(Base):
    """One run of a detection profile's change check (see profile_gate).

    ``baseline``: the first members ever released; ``released``: changes let
    through; ``approved``: changes an analyst approved; ``held``: changes
    waiting for approval; ``lifted``: a hold that no longer applies.
    ``summary`` is the change preview at the time.
    """

    __tablename__ = "profile_releases"

    id = Column(Integer, primary_key=True, index=True)
    profile_id = Column(
        Integer,
        ForeignKey("detection_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status = Column(String(16), nullable=False)
    members = Column(Integer, nullable=False, default=0)
    added = Column(Integer, nullable=False, default=0)
    removed = Column(Integer, nullable=False, default=0)
    reasons = Column(JSON, nullable=False, default=list)
    summary = Column(JSON, nullable=False, default=dict)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at = Column(DateTime(timezone=True), nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), nullable=True)
