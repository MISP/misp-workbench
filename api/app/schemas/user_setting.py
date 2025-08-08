from pydantic import BaseModel


class UserSetting(BaseModel):
    id: int
    user_id: int
    namespace: str
    value: dict
