import uuid

from app.database import Base
from app.models.event import DistributionLevel
from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column


class Galaxy(Base):
    __tablename__ = "galaxies"

    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(UUID(as_uuid=True), unique=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    type = Column(String, nullable=False)
    description = Column(String, nullable=False)
    version = Column(Integer, nullable=False)
    icon = Column(String, nullable=False)
    namespace = Column(String, nullable=False)
    enabled = Column(Boolean, nullable=False, default=False)
    local_only = Column(Boolean, nullable=False, default=False)
    kill_chain_order = Column(JSON, nullable=True, default={})
    default = Column(Boolean, nullable=False, default=False)
    org_id = Column(Integer, ForeignKey("organisations.id"), index=True, nullable=False)
    orgc_id = Column(
        Integer, ForeignKey("organisations.id"), index=True, nullable=False
    )
    created = Column(DateTime, nullable=False)
    modified = Column(DateTime, nullable=False)
    distribution: Mapped[DistributionLevel] = mapped_column(
        Enum(DistributionLevel, name="distribution_level"),
        nullable=False,
        default=DistributionLevel.INHERIT_EVENT,
    )
    # predicates = relationship("TaxonomyPredicate", lazy="subquery")


# class TaxonomyPredicate(Base):
#     __tablename__ = "taxonomy_predicates"

#     id = Column(Integer, primary_key=True, index=True)
#     taxonomy_id = Column(
#         Integer, ForeignKey("taxonomies.id"), index=True, nullable=True
#     )
#     value = Column(String, nullable=False)
#     expanded = Column(String, nullable=False)
#     colour = Column(String, nullable=False)
#     description = Column(String, nullable=False)
#     exclusive = Column(Boolean, nullable=False, default=False)
#     numerical_value = Column(Integer, index=True)

#     entries = relationship("TaxonomyEntry", lazy="subquery")


# class TaxonomyEntry(Base):
#     __tablename__ = "taxonomy_entries"

#     id = Column(Integer, primary_key=True, index=True)
#     taxonomy_predicate_id = Column(
#         Integer, ForeignKey("taxonomy_predicates.id"), index=True, nullable=True
#     )
#     value = Column(String, nullable=False)
#     expanded = Column(String, nullable=False)
#     colour = Column(String, nullable=False)
#     description = Column(String, nullable=False)
#     numerical_value = Column(Integer, index=True)
