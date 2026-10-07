"""Storage for async export artifacts.

Mirrors ``app/services/attachments.py`` but for export files: writes to a
Garage/S3 bucket under an ``exports/`` key prefix when ``STORAGE_ENGINE=s3``,
or to a local directory otherwise. Keys are caller-provided and always
namespaced under ``exports/`` so they never collide with attachment keys.
"""

import logging
import os
import shutil
import tempfile
from typing import BinaryIO, Iterator

from app.services.s3 import get_s3_client
from app.settings import Settings, get_settings

logger = logging.getLogger(__name__)

LOCAL_BASE_PATH = "/tmp/exports"
KEY_PREFIX = "exports/"
# Chunk size when streaming a stored artifact back out.
READ_CHUNK_SIZE = 1024 * 1024


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


def store_export_file(
    key: str,
    fileobj: BinaryIO,
    settings: Settings = None,
) -> str:
    """Persist an export from a file object, without reading it into memory.

    The local backend writes beside the target and renames over it, so a
    consumer downloading the previous version never sees a half-written file;
    an S3 upload only becomes visible once complete.
    """
    settings = settings or get_settings()
    stored_key = _namespaced_key(key)
    fileobj.seek(0)

    if settings.Storage.engine == "s3":
        # Multipart for large files, so no single request holds the artifact.
        get_s3_client().upload_fileobj(fileobj, settings.Storage.s3.bucket, stored_key)
    else:
        fullpath = _local_path(stored_key)
        directory = os.path.dirname(fullpath)
        os.makedirs(directory, exist_ok=True)
        fd, tmp_path = tempfile.mkstemp(dir=directory, prefix=".tmp-")
        try:
            with os.fdopen(fd, "wb") as f:
                shutil.copyfileobj(fileobj, f)
            os.replace(tmp_path, fullpath)
        except BaseException:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
            raise

    return stored_key


def open_export(key: str, settings: Settings = None) -> Iterator[bytes]:
    """Open a stored artifact and return an iterator over its chunks.

    The object is opened here, eagerly, so a missing artifact raises before a
    caller has started a response; only the reading is deferred.
    """
    settings = settings or get_settings()
    stored_key = _namespaced_key(key)

    if settings.Storage.engine == "s3":
        body = get_s3_client().get_object(
            Bucket=settings.Storage.s3.bucket, Key=stored_key
        )["Body"]

        def read_s3():
            try:
                yield from body.iter_chunks(READ_CHUNK_SIZE)
            finally:
                body.close()

        return read_s3()

    f = open(_local_path(stored_key), "rb")

    def read_local():
        with f:
            while chunk := f.read(READ_CHUNK_SIZE):
                yield chunk

    return read_local()


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
