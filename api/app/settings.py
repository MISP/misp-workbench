import os
from functools import lru_cache
from typing import Optional

from pydantic import BaseModel
from pydantic_settings import BaseSettings


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


class ModuleSettings(BaseModel):
    host: str = os.environ["MODULES_HOST"] or "localhost"
    port: int = int(os.environ["MODULES_PORT"]) or 6666


class MinioSettings(BaseModel):
    host: str = os.environ["MINIO_HOST"]
    access_key: str = os.environ["MINIO_ROOT_USER"]
    secret_key: str = os.environ["MINIO_ROOT_PASSWORD"]
    bucket: str = os.environ["MINIO_BUCKET"]


class StorageSettings(BaseModel):
    engine: str = os.environ["STORAGE_ENGINE"] or "local"
    minio: MinioSettings = MinioSettings()


class Settings(BaseSettings):
    MISP: MISPSettings = MISPSettings()
    OAuth2: OAuth2Settings = OAuth2Settings()
    Mail: MailSettings = MailSettings()
    Modules: ModuleSettings = ModuleSettings()
    Storage: StorageSettings = StorageSettings()


@lru_cache
def get_settings():
    return Settings()
