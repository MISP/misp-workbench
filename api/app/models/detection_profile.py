from sqlalchemy import JSON, Boolean, Column, DateTime, Integer, String, Text

from app.database import Base


class DetectionProfile(Base):
    """What goes to a kind of security control, defined once.

    ``rules`` select consolidated indicators (types, TLP ceiling, tags, score,
    age, sources, trust, to_ids, warninglists, validation issues; see
    ``app.schemas.detection_profile.ProfileRules``). ``granularity`` says
    whether outputs referencing the profile send those indicators or the
    attributes behind them. An ``auto_approve`` profile is a rule of the
    review queue: what it selects is approved without a review.
    """

    __tablename__ = "detection_profiles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    granularity = Column(
        String(16), nullable=False, default="indicators", server_default="indicators"
    )
    rules = Column(JSON, nullable=False, default=dict)
    auto_approve = Column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    # The approval gate: when a run's changes need approving (see
    # app.repositories.profile_gate). None: never held.
    gate = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False)
    updated_at = Column(DateTime(timezone=True), nullable=True)
