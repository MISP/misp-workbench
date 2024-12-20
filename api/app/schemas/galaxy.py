from datetime import datetime
from typing import Optional
from uuid import UUID

from app.models.event import DistributionLevel
from pydantic import BaseModel, ConfigDict


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
    model_config = ConfigDict(from_attributes=True)


class GalaxyUpdate(BaseModel):
    default: Optional[bool] = None
    enabled: Optional[bool] = None
    local_only: Optional[bool] = None


class GalaxyClusterBase(BaseModel):
    name: str
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
