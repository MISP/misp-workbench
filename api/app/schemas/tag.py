from typing import Optional

from pydantic import BaseModel


class TagBase(BaseModel):
    name: str
    colour: str
    exportable: bool
    org_id: int
    user_id: int
    hide_tag: bool
    numerical_value: Optional[int]
    is_galaxy: bool
    is_custom_galaxy: bool
    local_only: bool


class Tag(TagBase):
    id: int

    class Config:
        orm_mode = True


class AttributeTagBase(BaseModel):
    attribute_id: int
    event_id: int
    tag_id: int
    local: bool


class AttributeTag(AttributeTagBase):
    id: int

    class Config:
        orm_mode = True


class EventTagBase(BaseModel):
    event_id: int
    tag_id: int
    local: bool


class EventTag(EventTagBase):
    id: int

    class Config:
        orm_mode = True
