from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class SharingGroupBase(BaseModel):
    name: str
    releasability: str
    description: str
    uuid: Optional[UUID] = None
    organisation_uuid: Optional[UUID] = None
    org_id: int
    sync_user_id: Optional[int] = None
    active: bool
    local: bool
    roaming: bool
    created: datetime
    modified: datetime


class SharingGroupOrganisationBase(BaseModel):
    sharing_group_id: Optional[int] = None
    org_id: int
    extend: bool


class SharingGroupOrganisationCreate(SharingGroupOrganisationBase):
    pass


class SharingGroupOrganisation(SharingGroupOrganisationBase):
    id: int
    model_config = ConfigDict(from_attributes=True)


class SharingGroupServerBase(BaseModel):
    sharing_group_id: Optional[int] = None
    server_id: int
    all_orgs: bool


class SharingGroupServer(SharingGroupServerBase):
    id: int
    model_config = ConfigDict(from_attributes=True)


class SharingGroupServerCreate(SharingGroupServerBase):
    pass


class SharingGroup(SharingGroupBase):
    id: int
    sharing_group_organisations: list[SharingGroupOrganisation] = []
    sharing_group_servers: list[SharingGroupServer] = []
    model_config = ConfigDict(from_attributes=True)


class SharingGroupCreate(SharingGroupBase):
    pass


class SharingGroupUpdate(BaseModel):
    name: Optional[str] = None
    releasability: Optional[str] = None
    description: Optional[str] = None
    sync_user_id: Optional[int] = None
    active: Optional[bool] = None
    local: Optional[bool] = None
    roaming: Optional[bool] = None
    created: Optional[datetime] = None
    modified: Optional[datetime] = None
