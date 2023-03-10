from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class ObjectTemplateAttribute(BaseModel):
    name: str
    description: Optional[str]
    disable_correlation: Optional[bool]
    misp_attribute: str
    multiple: Optional[bool]
    ui_priority: Optional[int]


class ObjectTemplateBase(BaseModel):
    uuid: UUID
    version: int
    name: str
    meta_category: str
    attributes: list[ObjectTemplateAttribute] = []
    requiredOneOf: Optional[list[str]] = []


class ObjectTemplate(ObjectTemplateBase):
    pass
