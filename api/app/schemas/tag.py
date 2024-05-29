from typing import Optional

from pydantic import BaseModel, ConfigDict


class TagBase(BaseModel):
    name: str
    colour: str
    exportable: bool
    org_id: int
    user_id: int
    hide_tag: bool
    numerical_value: Optional[int] = None
    is_galaxy: bool
    is_custom_galaxy: bool
    local_only: bool


class Tag(TagBase):
    id: int
    model_config = ConfigDict(from_attributes=True)


class TagCreate(TagBase):
    pass


class TagUpdate(TagBase):
    name: Optional[str] = None
    colour: Optional[str] = None
    exportable: Optional[bool] = None
    org_id: Optional[int] = None
    user_id: Optional[int] = None
    hide_tag: Optional[bool] = None
    numerical_value: Optional[int] = None
    is_galaxy: Optional[bool] = None
    is_custom_galaxy: Optional[bool] = None
    local_only: Optional[bool] = None


class AttributeTagBase(BaseModel):
    attribute_id: int
    event_id: int
    tag_id: int
    local: bool


class AttributeTag(AttributeTagBase):
    id: int
    model_config = ConfigDict(from_attributes=True)


class EventTagBase(BaseModel):
    event_id: int
    tag_id: int
    local: bool


class EventTag(EventTagBase):
    id: int
    model_config = ConfigDict(from_attributes=True)
