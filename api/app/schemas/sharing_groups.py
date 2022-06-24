from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class SharingGroupBase(BaseModel):
    name: str
    releasability: str
    description: str
    uuid: Optional[UUID]
    organisation_uuid: Optional[UUID]
    org_id: int
    sync_user_id: Optional[int]
    active: bool
    local: bool
    roaming: bool
    created: datetime
    modified: datetime


class SharingGroupOrganisationBase(BaseModel):
    sharing_group_id: Optional[int]
    org_id: int
    extend: bool


class SharingGroupOrganisationCreate(SharingGroupOrganisationBase):
    pass


class SharingGroupOrganisation(SharingGroupOrganisationBase):
    id: int

    class Config:
        orm_mode = True


class SharingGroupServerBase(BaseModel):
    sharing_group_id: Optional[int]
    server_id: int
    all_orgs: bool


class SharingGroupServer(SharingGroupServerBase):
    id: int

    class Config:
        orm_mode = True


class SharingGroupServerCreate(SharingGroupServerBase):
    pass


class SharingGroup(SharingGroupBase):
    id: int
    sharing_group_organisations: list[SharingGroupOrganisation] = []
    sharing_group_servers: list[SharingGroupServer] = []

    class Config:
        orm_mode = True


class SharingGroupCreate(SharingGroupBase):
    pass


class SharingGroupUpdate(BaseModel):
    name: Optional[str]
    releasability: Optional[str]
    description: Optional[str]
    sync_user_id: Optional[int]
    active: Optional[bool]
    local: Optional[bool]
    roaming: Optional[bool]
    created: Optional[datetime]
    modified: Optional[datetime]
