"""Storage for async export artifacts.

Mirrors ``app/services/attachments.py`` but for export files: writes to a
Garage/S3 bucket under an ``exports/`` key prefix when ``STORAGE_ENGINE=s3``,
or to a local directory otherwise. Keys are caller-provided and always
namespaced under ``exports/`` so they never collide with attachment keys.
"""

import logging
import os

from app.services.s3 import get_s3_client
from app.settings import Settings, get_settings

logger = logging.getLogger(__name__)

LOCAL_BASE_PATH = "/tmp/exports"
KEY_PREFIX = "exports/"


def _namespaced_key(key: str) -> str:
    return key if key.startswith(KEY_PREFIX) else f"{KEY_PREFIX}{key}"


def _local_path(key: str) -> str:
    fullpath = os.path.normpath(os.path.join(LOCAL_BASE_PATH, key))
    if not fullpath.startswith(LOCAL_BASE_PATH):
        raise ValueError("Invalid export storage key")
    return fullpath


def store_export(
    key: str,
    content: bytes,
    settings: Settings = None,
) -> str:
    """Persist export bytes under ``key`` and return the stored key."""
    settings = settings or get_settings()
    stored_key = _namespaced_key(key)

    if settings.Storage.engine == "s3":
        get_s3_client().put_object(
            Bucket=settings.Storage.s3.bucket,
            Key=stored_key,
            Body=content,
        )
    else:
        fullpath = _local_path(stored_key)
        os.makedirs(os.path.dirname(fullpath), exist_ok=True)
        with open(fullpath, "wb") as f:
            f.write(content)

    return stored_key


def get_export(key: str, settings: Settings = None) -> bytes:
    settings = settings or get_settings()
    stored_key = _namespaced_key(key)

    if settings.Storage.engine == "s3":
        data = get_s3_client().get_object(
            Bucket=settings.Storage.s3.bucket, Key=stored_key
        )
        return data["Body"].read()

    with open(_local_path(stored_key), "rb") as f:
        return f.read()


def delete_export(key: str, settings: Settings = None) -> None:
    """Best-effort removal of a stored export artifact."""
    settings = settings or get_settings()
    stored_key = _namespaced_key(key)

    try:
        if settings.Storage.engine == "s3":
            get_s3_client().delete_object(
                Bucket=settings.Storage.s3.bucket, Key=stored_key
            )
        else:
            fullpath = _local_path(stored_key)
            if os.path.exists(fullpath):
                os.remove(fullpath)
    except Exception as e:
        logger.warning("Failed to delete export artifact %s: %s", stored_key, e)
