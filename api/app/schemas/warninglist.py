from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class Warninglist(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    type: str
    category: Optional[str] = None
    version: int
    matching_attributes: list[str] = []
    entry_count: int
    enabled: bool
    updated_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


class WarninglistUpdate(BaseModel):
    enabled: bool


class WarninglistCheckRequest(BaseModel):
    values: list[str] = Field(..., max_length=10_000)
    # The attribute type the values would have; lists not applying to it are
    # skipped. Omit to check against every list.
    type: Optional[str] = None


class WarninglistCheckResponse(BaseModel):
    # value -> names of the enabled lists it hits (only values with hits).
    hits: dict[str, list[str]]
