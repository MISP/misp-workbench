from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class RoleBase(BaseModel):
    name: str
    created: Optional[datetime]
    modified: Optional[datetime]
    perm_add: bool
    perm_modify: bool
    perm_modify_org: bool
    perm_publish: bool
    perm_delegate: bool
    perm_sync: bool
    perm_admin: bool
    perm_audit: bool
    perm_full: bool
    perm_auth: bool
    perm_site_admin: bool
    perm_regexp_access: bool
    perm_tagger: bool
    perm_template: bool
    perm_sharing_group: bool
    perm_tag_editor: bool
    perm_sighting: bool
    perm_object_template: bool
    perm_galaxy_editor: bool
    perm_warninglist: bool
    perm_publish_zmq: bool
    perm_publish_kafka: bool
    perm_decaying: bool
    default_role: bool
    restricted_to_site_admin: bool
    enforce_rate_limit: bool
    rate_limit_count: int
    memory_limit: str
    max_execution_time: str


class Role(RoleBase):
    id: int

    class Config:
        orm_mode = True
