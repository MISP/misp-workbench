from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class OrganisationBase(BaseModel):
    name: str
    description: Optional[str]
    date_created: datetime
    date_modified: datetime
    type: str
    nationality: str
    sector: str
    created_by: int
    uuid: UUID
    contacts: Optional[str]
    local: bool
    restricted_to_domain: Optional[str]
    landing_page: Optional[str]


class Organisation(OrganisationBase):
    id: int

    class Config:
        orm_mode = True


class OrganisationCreate(OrganisationBase):
    pass
