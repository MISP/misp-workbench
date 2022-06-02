from pydantic import BaseSettings, BaseModel
from typing import Optional
from functools import lru_cache
import os


class MISPSettings(BaseModel):
    host_org_id: Optional[int] = 1


class OAuth2Settings(BaseModel):
    secret_key: str = os.environ['OAUTH2_SECRET_KEY']
    algorithm: str = os.environ['OAUTH2_ALGORITHM'] or "HS256"
    access_token_expire_minutes: int = os.environ['OAUTH2_ACCESS_TOKEN_EXPIRE_MINUTES'] or 30


class Settings(BaseSettings):
    MISP: MISPSettings = MISPSettings()
    OAuth2: OAuth2Settings = OAuth2Settings()


@lru_cache()
def get_settings():
    return Settings()
