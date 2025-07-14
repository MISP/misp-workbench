from pydantic import BaseModel


class Setting(BaseModel):
    id: int
    user_id: int
    namespace: str
    value: dict
