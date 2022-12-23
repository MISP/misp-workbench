import os
from functools import lru_cache
from typing import Optional

from pydantic import BaseModel, BaseSettings


class MISPSettings(BaseModel):
    host_org_id: Optional[int] = 1
    baseurl: Optional[str] = "https://localhost"
    external_baseurl: Optional[str] = ""


class OAuth2Settings(BaseModel):
    secret_key: str = os.environ["OAUTH2_SECRET_KEY"]
    algorithm: str = os.environ["OAUTH2_ALGORITHM"] or "HS256"
    access_token_expire_minutes: int = (
        int(os.environ["OAUTH2_ACCESS_TOKEN_EXPIRE_MINUTES"]) or 30
    )


class MailSettings(BaseModel):
    host: str = os.environ["MAIL_SERVER"]
    port: int = int(os.environ["MAIL_PORT"])
    username: str = os.environ["MAIL_USERNAME"]
    password: str = os.environ["MAIL_PASSWORD"]


class Settings(BaseSettings):
    MISP: MISPSettings = MISPSettings()
    OAuth2: OAuth2Settings = OAuth2Settings()
    Mail: MailSettings = MailSettings()


@lru_cache
def get_settings():
    return Settings()
