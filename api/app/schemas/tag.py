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


class TagCreate(TagBase):
    pass


class TagUpdate(TagBase):
    name: Optional[str]
    colour: Optional[str]
    exportable: Optional[bool]
    org_id: Optional[int]
    user_id: Optional[int]
    hide_tag: Optional[bool]
    numerical_value: Optional[int]
    is_galaxy: Optional[bool]
    is_custom_galaxy: Optional[bool]
    local_only: Optional[bool]


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
