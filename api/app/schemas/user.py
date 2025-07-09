from typing import Optional

from app.schemas.role import Role
from app.schemas.organisations import Organisation
from pydantic import BaseModel, ConfigDict


class UserBase(BaseModel):
    email: str
    org_id: int
    role_id: int


class User(UserBase):
    id: int
    role: Role
    organisation: Organisation
    model_config = ConfigDict(from_attributes=True)


class UserCreate(UserBase):
    password: Optional[str] = None


class UserUpdate(BaseModel):
    email: Optional[str] = None
    org_id: Optional[int] = None
    role_id: Optional[int] = None
