from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class ApiKeyBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    comment: Optional[str] = None
    scopes: list[str] = Field(default_factory=list)
    expires_at: Optional[datetime] = None


class ApiKeyCreate(ApiKeyBase):
    pass


class ApiKeyUpdate(BaseModel):
    disabled: bool


class ApiKey(BaseModel):
    id: int
    user_id: int
    name: str
    comment: Optional[str] = None
    scopes: list[str]
    expires_at: Optional[datetime] = None
    last_used_at: Optional[datetime] = None
    disabled: bool
    admin_disabled: bool
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class ApiKeyCreated(ApiKey):
    """Response returned once on creation, includes the raw token."""

    token: str
