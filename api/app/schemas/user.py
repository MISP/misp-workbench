from typing import Optional

from pydantic import BaseModel


class UserBase(BaseModel):
    email: str
    org_id: int
    role_id: int


class User(UserBase):
    id: int

    class Config:
        orm_mode = True


class UserCreate(UserBase):
    password: str


class UserUpdate(BaseModel):
    email: Optional[str]
    role_id: Optional[int]
