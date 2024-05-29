from typing import Optional

from pydantic import BaseModel, ConfigDict


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
    last_pulled_id: Optional[int] = None
    last_pushed_id: Optional[int] = None
    organisation: Optional[str] = None
    remote_org_id: int
    publish_without_email: bool
    unpublish_event: bool
    self_signed: bool
    pull_rules: Optional[dict] = None
    push_rules: Optional[dict] = None
    cert_file: Optional[str] = None
    client_cert_file: Optional[str] = None
    internal: bool
    skip_proxy: bool
    caching_enabled: bool
    priority: int


class Server(ServerBase):
    id: int
    model_config = ConfigDict(from_attributes=True)


class ServerCreate(ServerBase):
    pass


class ServerUpdate(BaseModel):
    name: Optional[str] = None
    url: Optional[str] = None
    authkey: Optional[str] = None
    org_id: Optional[int] = None
    push: Optional[bool] = None
    pull: Optional[bool] = None
    push_sightings: Optional[bool] = None
    push_galaxy_clusters: Optional[bool] = None
    pull_galaxy_clusters: Optional[bool] = None
    last_pulled_id: Optional[int] = None
    last_pushed_id: Optional[int] = None
    organisation: Optional[str] = None
    remote_org_id: Optional[int] = None
    publish_without_email: Optional[bool] = None
    unpublish_event: Optional[bool] = None
    self_signed: Optional[bool] = None
    pull_rules: Optional[dict] = None
    push_rules: Optional[dict] = None
    cert_file: Optional[str] = None
    client_cert_file: Optional[str] = None
    internal: Optional[bool] = None
    skip_proxy: Optional[bool] = None
    caching_enabled: Optional[bool] = None
    priority: Optional[int] = None


class TestServerConnectionResponse(BaseModel):
    status: str
    version: Optional[str] = None
    error: Optional[str] = None
