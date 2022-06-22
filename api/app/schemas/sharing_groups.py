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


class SharingGroupOrgBase(BaseModel):
    sharing_group_id: int
    org_id: int
    extend: bool


class SharingGroupServerBase(BaseModel):
    sharing_group_id: int
    server_id: int
    all_orgs: bool


class SharingGroup(SharingGroupBase):
    id: int

    class Config:
        orm_mode = True


class SharingGroupOrg(SharingGroupOrgBase):
    id: int

    class Config:
        orm_mode = True


class SharingGroupServer(SharingGroupServerBase):
    id: int

    class Config:
        orm_mode = True


class SharingGroupCreate(SharingGroupBase):
    pass
