from typing import Optional

from app.models.event import DistributionLevel
from pydantic import BaseModel, ConfigDict


class FeedBase(BaseModel):
    name: str
    provider: str
    url: str
    rules: Optional[dict] = None
    enabled: Optional[bool] = False
    distribution: Optional[DistributionLevel] = None
    sharing_group_id: Optional[int] = None
    tag_id: Optional[int] = None
    default: Optional[bool] = False
    source_format: str
    fixed_event: Optional[bool] = False
    delta_merge: Optional[bool] = False
    event_id: Optional[int] = None
    publish: Optional[bool] = False
    override_ids: Optional[bool] = False
    settings: Optional[dict] = None
    input_source: str
    delete_local_file: Optional[bool] = False
    lookup_visible: Optional[bool] = False
    headers: Optional[dict] = None
    caching_enabled: Optional[bool] = False
    force_to_ids: Optional[bool] = False
    orgc_id: Optional[int] = None
    tag_collection_id: Optional[int] = None
    cached_elements: Optional[int] = None
    coverage_by_other_feeds: Optional[float] = None


class Feed(FeedBase):
    id: int
    model_config = ConfigDict(from_attributes=True)


class FeedCreate(FeedBase):
    pass


class FeedUpdate(FeedBase):
    name: Optional[str] = None
    provider: Optional[str] = None
    url: Optional[str] = None
    rules: Optional[dict] = None
    enabled: Optional[bool] = None
    distribution: Optional[DistributionLevel] = None
    sharing_group_id: Optional[int] = None
    tag_id: Optional[int] = None
    default: Optional[bool] = None
    source_format: Optional[str] = None
    fixed_event: Optional[bool] = None
    delta_merge: Optional[bool] = None
    event_id: Optional[int] = None
    publish: Optional[bool] = None
    override_ids: Optional[bool] = None
    settings: Optional[dict] = None
    input_source: Optional[str] = None
    delete_local_file: Optional[bool] = None
    lookup_visible: Optional[bool] = None
    headers: Optional[dict] = None
    caching_enabled: Optional[bool] = None
    force_to_ids: Optional[bool] = None
    orgc_id: Optional[int] = None
    tag_collection_id: Optional[int] = None
    cached_elements: Optional[int] = None
    coverage_by_other_feeds: Optional[float] = None
