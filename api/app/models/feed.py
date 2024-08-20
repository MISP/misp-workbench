from app.database import Base
from app.models.event import DistributionLevel
from sqlalchemy import JSON, Boolean, Column, Enum, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column


class Feed(Base):
    __tablename__ = "feeds"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True)
    provider = Column(String, nullable=False)
    url = Column(String, nullable=False)
    rules = Column(JSON, nullable=False, default={})
    enabled = Column(Boolean, nullable=False, default=False)
    distribution = Mapped[DistributionLevel] = mapped_column(
        Enum(DistributionLevel, name="distribution_level"),
        nullable=False,
        default=DistributionLevel.ORGANISATION_ONLY,
    )
    sharing_group_id = Column(Integer, ForeignKey("sharing_groups.id"), nullable=False)
    tag_id = Column(Integer, ForeignKey("tags.id"), nullable=True)
    default = Column(Boolean, nullable=False, default=False)
    source_format = Column(String, nullable=False)
    fixed_event = Column(Boolean, nullable=False, default=False)
    delta_merge = Column(Boolean, nullable=False, default=False)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=True)
    publish = Column(Boolean, nullable=False, default=False)
    override_ids = Column(Boolean, nullable=False, default=False)
    settings = Column(JSON, nullable=False, default={})
    input_source = Column(String, nullable=False)
    delete_local_file = Column(Boolean, nullable=False, default=False)
    lookup_visible = Column(Boolean, nullable=False, default=False)
    headers = Column(JSON, nullable=False, default={})
    caching_enabled = Column(Boolean, nullable=False, default=False)
    force_to_ids = Column(Boolean, nullable=False, default=False)
    orgc_id = Column(Integer, ForeignKey("organisations.id"), nullable=False)
    tag_collection_id = Column(Integer, nullable=True)
    cached_elements = Column(Integer, nullable=False, default=0)
    coverage_by_other_feeds = Column(Float, nullable=False, default=0)
