from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


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
    # Indicator scoring: points added to (or taken off) the score of what
    # this source reports, and an optional ceiling for it.
    score_modifier: int = Field(0, ge=-100, le=100)
    score_cap: Optional[int] = Field(None, ge=0, le=100)


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
    # Indicator scoring: points added to (or taken off) the score of what
    # this source reports, and an optional ceiling for it.
    score_modifier: int = Field(0, ge=-100, le=100)
    score_cap: Optional[int] = Field(None, ge=0, le=100)


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
    score_modifier: Optional[int] = Field(None, ge=-100, le=100)
    score_cap: Optional[int] = Field(None, ge=0, le=100)
