from typing import Optional

from app.schemas.role import Role
from pydantic import BaseModel


class UserBase(BaseModel):
    email: str
    org_id: int
    role_id: int


class User(UserBase):
    id: int
    role: Role

    class Config:
        orm_mode = True


class UserCreate(UserBase):
    password: Optional[str]


class UserUpdate(BaseModel):
    email: Optional[str]
    role_id: Optional[int]
