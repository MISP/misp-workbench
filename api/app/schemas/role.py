from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class RoleBase(BaseModel):
    name: str
    created: Optional[datetime] = None
    modified: Optional[datetime] = None
    scopes: list[str]
    default_role: bool = False


class RoleCreate(RoleBase):
    pass


class RoleUpdate(BaseModel):
    name: Optional[str] = None
    scopes: Optional[list[str]] = None
    default_role: Optional[bool] = None


class Role(RoleBase):
    id: int
    model_config = ConfigDict(from_attributes=True)
