from pydantic import BaseModel
from typing import Optional


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
    lastpulledid: Optional[int]
    lastpushedid: Optional[int]
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
