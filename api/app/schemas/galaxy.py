from datetime import datetime
from typing import Optional
from uuid import UUID

from app.models.event import DistributionLevel
from pydantic import BaseModel, ConfigDict


class GalaxyClusterRelationTagBase(BaseModel):
    galaxy_cluster_relation_id: int
    tag_id: int


class GalaxyClusterRelationTag(GalaxyClusterRelationTagBase):
    galaxy_cluster_relation_id: int
    tag_id: int
    model_config = ConfigDict(from_attributes=True)


class GalaxyClusterRelationBase(BaseModel):
    galaxy_cluster_id: int
    referenced_galaxy_cluster_id: Optional[int] = None
    referenced_galaxy_cluster_uuid: Optional[UUID] = None
    referenced_galaxy_cluster_type: str
    galaxy_cluster_uuid: Optional[UUID] = None
    distribution: DistributionLevel
    sharing_group_id: Optional[int] = None
    default: bool


class GalaxyClusterRelation(GalaxyClusterRelationBase):
    id: int
    tags: list[GalaxyClusterRelationTag] = []
    model_config = ConfigDict(from_attributes=True)


class GalaxyElementBase(BaseModel):
    key: str
    value: str
    galaxy_cluster_id: int


class GalaxyElement(GalaxyElementBase):
    id: int
    model_config = ConfigDict(from_attributes=True)


class GalaxyClusterBase(BaseModel):
    uuid: UUID
    collection_uuid: Optional[UUID] = None
    type: str
    value: str
    tag_name: str
    description: str
    galaxy_id: int
    source: str
    authors: Optional[list] = []
    version: Optional[int] = None
    distribution: DistributionLevel
    sharing_group_id: Optional[int] = None
    org_id: int
    orgc_id: int
    extends_uuid: Optional[UUID] = None
    extends_version: Optional[int] = None
    published: bool
    deleted: bool


class GalaxyCluster(GalaxyClusterBase):
    id: int
    relations: list[GalaxyClusterRelation] = []
    elements: list[GalaxyElement] = []
    model_config = ConfigDict(from_attributes=True)


class GalaxyBase(BaseModel):
    uuid: Optional[UUID] = None
    name: str
    type: str
    description: str
    version: int
    icon: str
    namespace: str
    enabled: bool
    local_only: bool
    kill_chain_order: Optional[dict] = {}
    default: bool
    org_id: int
    orgc_id: int
    created: datetime
    modified: datetime
    distribution: DistributionLevel


class Galaxy(GalaxyBase):
    id: int
    clusters: list[GalaxyCluster] = []
    model_config = ConfigDict(from_attributes=True)


class GalaxyUpdate(BaseModel):
    default: Optional[bool] = None
    enabled: Optional[bool] = None
    local_only: Optional[bool] = None
