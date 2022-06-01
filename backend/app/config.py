from pydantic import BaseSettings, BaseModel
from typing import Optional
from functools import lru_cache


class MISPSettings(BaseModel):
    host_org_id: Optional[int] = 1


class Settings(BaseSettings):
    MISP: MISPSettings = MISPSettings()


@lru_cache()
def get_settings():
    return Settings()
