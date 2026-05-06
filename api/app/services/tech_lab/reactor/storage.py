"""Backend-agnostic storage for reactor script source and run logs.

Keys are canonical (``reactor/scripts/<uuid>.py``, ``reactor/runs/<id>.log``)
in both s3 and local mode; in local mode they map to ``/tmp/<key>``.
"""

import logging
import os

from app.services.s3 import get_s3_client
from app.settings import get_settings

logger = logging.getLogger(__name__)

LOCAL_BASE = "/tmp"


def _local_path(key: str) -> str:
    full = os.path.normpath(os.path.join(LOCAL_BASE, key))
    if not full.startswith(LOCAL_BASE + os.sep):
        raise RuntimeError("invalid reactor storage path")
    return full


def write_object(key: str, body: bytes) -> None:
    settings = get_settings()
    if settings.Storage.engine == "s3":
        client = get_s3_client()
        client.put_object(Bucket=settings.Storage.s3.bucket, Key=key, Body=body)
        return

    full = _local_path(key)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "wb") as f:
        f.write(body)


def read_object(key: str) -> bytes:
    settings = get_settings()
    if settings.Storage.engine == "s3":
        client = get_s3_client()
        obj = client.get_object(Bucket=settings.Storage.s3.bucket, Key=key)
        return obj["Body"].read()

    full = _local_path(key)
    with open(full, "rb") as f:
        return f.read()


def delete_object(key: str) -> None:
    if not key:
        return
    settings = get_settings()
    try:
        if settings.Storage.engine == "s3":
            client = get_s3_client()
            client.delete_object(Bucket=settings.Storage.s3.bucket, Key=key)
            return
        full = _local_path(key)
        if os.path.exists(full):
            os.remove(full)
    except Exception:  # noqa: BLE001
        logger.exception("failed to delete reactor object key=%s", key)


def object_exists(key: str) -> bool:
    if not key:
        return False
    settings = get_settings()
    if settings.Storage.engine == "s3":
        client = get_s3_client()
        try:
            client.head_object(Bucket=settings.Storage.s3.bucket, Key=key)
            return True
        except Exception:  # noqa: BLE001
            return False
    return os.path.exists(_local_path(key))
