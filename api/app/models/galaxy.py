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
from sqlalchemy.orm import Mapped, mapped_column, relationship


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
    clusters = relationship("GalaxyCluster", lazy="subquery")


class GalaxyCluster(Base):
    __tablename__ = "galaxy_clusters"

    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(UUID(as_uuid=True), unique=True, default=uuid.uuid4)
    collection_uuid = Column(UUID(as_uuid=True), nullable=True)
    type = Column(String, nullable=False)
    value = Column(String, nullable=False)
    tag_name = Column(String, nullable=False)
    description = Column(String, nullable=False)
    galaxy_id = Column(Integer, ForeignKey("galaxies.id"), index=True, nullable=False)
    source = Column(String, nullable=True)
    authors = Column(JSON, nullable=True, default={})
    version = Column(Integer, nullable=True)
    distribution: Mapped[DistributionLevel] = mapped_column(
        Enum(DistributionLevel, name="distribution_level"),
        nullable=False,
        default=DistributionLevel.INHERIT_EVENT,
    )
    sharing_group_id = Column(
        Integer, ForeignKey("sharing_groups.id"), index=True, nullable=True
    )
    org_id = Column(Integer, ForeignKey("organisations.id"), index=True, nullable=False)
    orgc_id = Column(
        Integer, ForeignKey("organisations.id"), index=True, nullable=False
    )
    extends_uuid = Column(UUID(as_uuid=True), nullable=True)
    extends_version = Column(Integer, nullable=True)
    published = Column(Boolean, nullable=False, default=False)
    deleted = Column(Boolean, nullable=False, default=False)


class GalaxyElement(Base):
    __tablename__ = "galaxy_elements"
    id = Column(Integer, primary_key=True, index=True)
    key = Column(String, nullable=False)
    value = Column(String, nullable=False)
    galaxy_cluster_id = Column(
        Integer, ForeignKey("galaxy_clusters.id"), index=True, nullable=False
    )


class GalaxyClusterRelation(Base):
    __tablename__ = "galaxy_cluster_relations"
    id = Column(Integer, primary_key=True, index=True)
    galaxy_cluster_id = Column(
        Integer, ForeignKey("galaxy_clusters.id"), index=True, nullable=False
    )
    referenced_galaxy_cluster_id = Column(
        Integer, ForeignKey("galaxy_clusters.id"), index=True, nullable=False
    )
    referenced_galaxy_cluster_uuid = Column(UUID(as_uuid=True), nullable=False)
    referenced_galaxy_cluster_type = Column(String, nullable=False)
    galaxy_cluster_uuid = Column(UUID(as_uuid=True), nullable=False)
    distribution: Mapped[DistributionLevel] = mapped_column(
        Enum(DistributionLevel, name="distribution_level"),
        nullable=False,
        default=DistributionLevel.INHERIT_EVENT,
    )
    sharing_group_id = Column(
        Integer, ForeignKey("sharing_groups.id"), index=True, nullable=True
    )
    default = Column(Boolean, nullable=False, default=False)


class GalaxyClusterRelationTag(Base):
    __tablename__ = "galaxy_cluster_relation_tags"
    id = Column(Integer, primary_key=True, index=True)
    galaxy_cluster_relation_id = Column(
        Integer, ForeignKey("galaxy_cluster_relations.id"), index=True, nullable=False
    )
    tag_id = Column(Integer, ForeignKey("tags.id"), index=True, nullable=False)
