from pydantic import BaseModel


class UserBase(BaseModel):
    email: str


class User(UserBase):
    id: int

    class Config:
        orm_mode = True


class UserCreate(UserBase):
    password: str