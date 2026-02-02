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
    refresh_secret_key: str = os.environ.get("OAUTH2_REFRESH_SECRET_KEY") or (
        os.environ["OAUTH2_SECRET_KEY"] + "_refresh"
    )
    algorithm: str = os.environ["OAUTH2_ALGORITHM"] or "HS256"
    access_token_expire_minutes: int = (
        int(os.environ["OAUTH2_ACCESS_TOKEN_EXPIRE_MINUTES"]) or 30
    )
    refresh_token_expire_days: int = (
        int(os.environ["OAUTH2_REFRESH_TOKEN_EXPIRE_DAYS"]) or 7
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
    host: str = (
        os.environ["MINIO_HOST"] if os.environ["STORAGE_ENGINE"] == "minio" else ""
    )
    access_key: str = (
        os.environ["MINIO_ROOT_USER"] if os.environ["STORAGE_ENGINE"] == "minio" else ""
    )
    secret_key: str = (
        os.environ["MINIO_ROOT_PASSWORD"]
        if os.environ["STORAGE_ENGINE"] == "minio"
        else ""
    )
    bucket: str = (
        os.environ["MINIO_BUCKET"] if os.environ["STORAGE_ENGINE"] == "minio" else ""
    )
    secure: bool = (
        os.environ["MINIO_SECURE"] == "true"
        if os.environ["STORAGE_ENGINE"] == "minio"
        else ""
    )


class StorageSettings(BaseModel):
    engine: str = os.environ["STORAGE_ENGINE"] or "local"
    minio: MinioSettings = MinioSettings()

class RedisSettings(BaseModel):
    host: str = os.environ["REDIS_HOSTNAME"] or "localhost"
    port: int = int(os.environ["REDIS_PORT"]) or 6379
    cache_db: int = int(os.environ["REDIS_CACHE_DB"]) or 5

class Settings(BaseSettings):
    MISP: MISPSettings = MISPSettings()
    OAuth2: OAuth2Settings = OAuth2Settings()
    Mail: MailSettings = MailSettings()
    Modules: ModuleSettings = ModuleSettings()
    Storage: StorageSettings = StorageSettings()
    Redis: RedisSettings = RedisSettings()


@lru_cache
def get_settings():
    return Settings()
