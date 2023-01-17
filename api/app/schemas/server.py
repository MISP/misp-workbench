from typing import Optional

from pydantic import BaseModel


class ServerBase(BaseModel):
    name: str
    url: str
    authkey: str
    org_id: int
    push: bool
    pull: bool
    push_sightings: bool
    push_galaxy_clusters: bool
    pull_galaxy_clusters: bool
    last_pulled_id: Optional[int]
    last_pushed_id: Optional[int]
    organisation: Optional[str]
    remote_org_id: int
    publish_without_email: bool
    unpublish_event: bool
    self_signed: bool
    pull_rules: Optional[dict]
    push_rules: Optional[dict]
    cert_file: Optional[str]
    client_cert_file: Optional[str]
    internal: bool
    skip_proxy: bool
    caching_enabled: bool
    priority: int


class Server(ServerBase):
    id: int

    class Config:
        orm_mode = True


class ServerCreate(ServerBase):
    pass


class ServerUpdate(BaseModel):
    name: Optional[str]
    url: Optional[str]
    authkey: Optional[str]
    org_id: Optional[int]
    push: Optional[bool]
    pull: Optional[bool]
    push_sightings: Optional[bool]
    push_galaxy_clusters: Optional[bool]
    pull_galaxy_clusters: Optional[bool]
    last_pulled_id: Optional[int]
    last_pushed_id: Optional[int]
    organisation: Optional[str]
    remote_org_id: Optional[int]
    publish_without_email: Optional[bool]
    unpublish_event: Optional[bool]
    self_signed: Optional[bool]
    pull_rules: Optional[dict]
    push_rules: Optional[dict]
    cert_file: Optional[str]
    client_cert_file: Optional[str]
    internal: Optional[bool]
    skip_proxy: Optional[bool]
    caching_enabled: Optional[bool]
    priority: Optional[int]
