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
    sane_default: Optional[list[str]] = []


class ObjectTemplateBase(BaseModel):
    uuid: UUID
    version: int
    name: str
    description: str
    meta_category: str
    attributes: list[ObjectTemplateAttribute] = []
    # MISP's two kinds of requirement: every relation in required, and at
    # least one of those in requiredOneOf
    required: Optional[list[str]] = []
    requiredOneOf: Optional[list[str]] = []


class ObjectTemplate(ObjectTemplateBase):
    pass
