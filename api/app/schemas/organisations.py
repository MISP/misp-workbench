from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class OrganisationBase(BaseModel):
    name: str
    description: Optional[str] = None
    date_created: datetime
    date_modified: datetime
    type: Optional[str] = None
    nationality: Optional[str] = None
    sector: Optional[str] = None
    created_by: int
    uuid: UUID
    contacts: Optional[str] = None
    local: bool
    restricted_to_domain: Optional[str] = None
    landing_page: Optional[str] = None


class Organisation(OrganisationBase):
    id: int
    model_config = ConfigDict(from_attributes=True)


class OrganisationCreate(BaseModel):
    name: str
    description: Optional[str] = None
    date_created: Optional[datetime] = None
    date_modified: Optional[datetime] = None
    type: Optional[str] = None
    nationality: Optional[str] = None
    sector: Optional[str] = None
    created_by: Optional[int] = None
    uuid: Optional[UUID] = None
    contacts: Optional[str] = None
    local: bool
    restricted_to_domain: Optional[str] = None
    landing_page: Optional[str] = None


class OrganisationUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    date_created: Optional[datetime] = None
    date_modified: Optional[datetime] = None
    type: Optional[str] = None
    nationality: Optional[str] = None
    sector: Optional[str] = None
    created_by: Optional[int] = None
    contacts: Optional[str] = None
    local: Optional[bool] = None
    restricted_to_domain: Optional[str] = None
    landing_page: Optional[str] = None
