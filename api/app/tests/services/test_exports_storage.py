"""Unit tests for the streaming helpers in ``app/services/exports_storage.py``."""

import io
import os
from unittest.mock import MagicMock, patch

import pytest

from app.services import exports_storage

KEY = "exports-storage-tests/feed.ndjson"


@pytest.fixture
def local_mode(monkeypatch):
    from app.settings import get_settings

    monkeypatch.setattr(get_settings().Storage, "engine", "local")
    yield
    exports_storage.delete_export(KEY)


@pytest.fixture
def s3_mode(monkeypatch):
    from app.settings import get_settings

    monkeypatch.setattr(get_settings().Storage, "engine", "s3")
    monkeypatch.setattr(get_settings().Storage.s3, "bucket", "test-bucket")
    client = MagicMock()
    with patch.object(exports_storage, "get_s3_client", return_value=client):
        yield client


class TestLocal:
    def test_store_and_read_back_in_chunks(self, local_mode, monkeypatch):
        monkeypatch.setattr(exports_storage, "READ_CHUNK_SIZE", 4)
        stored = exports_storage.store_export_file(KEY, io.BytesIO(b"0123456789"))
        assert stored == f"exports/{KEY}"
        assert list(exports_storage.open_export(KEY)) == [b"0123", b"4567", b"89"]

    def test_replacing_leaves_no_temp_files(self, local_mode):
        exports_storage.store_export_file(KEY, io.BytesIO(b"old"))
        exports_storage.store_export_file(KEY, io.BytesIO(b"new"))
        assert b"".join(exports_storage.open_export(KEY)) == b"new"
        directory = os.path.dirname(exports_storage._local_path(f"exports/{KEY}"))
        assert not [f for f in os.listdir(directory) if f.startswith(".tmp-")]

    def test_failed_write_keeps_previous_version(self, local_mode):
        exports_storage.store_export_file(KEY, io.BytesIO(b"good"))

        class Broken(io.BytesIO):
            def read(self, *args):
                raise OSError("disk full")

        with pytest.raises(OSError):
            exports_storage.store_export_file(KEY, Broken())
        assert b"".join(exports_storage.open_export(KEY)) == b"good"

    def test_missing_artifact_raises_before_reading(self, local_mode):
        with pytest.raises(FileNotFoundError):
            exports_storage.open_export("exports-storage-tests/missing.ndjson")

    def test_unconsumed_iterator_opens_nothing(self, local_mode):
        exports_storage.store_export_file(KEY, io.BytesIO(b"data"))
        with patch("builtins.open") as mock_open:
            exports_storage.open_export(KEY).close()
        mock_open.assert_not_called()


class TestS3:
    def test_store_uploads_multipart_from_the_start(self, s3_mode):
        fileobj = io.BytesIO(b"payload")
        fileobj.seek(3)
        stored = exports_storage.store_export_file(KEY, fileobj)
        assert stored == f"exports/{KEY}"
        s3_mode.upload_fileobj.assert_called_once_with(
            fileobj, "test-bucket", f"exports/{KEY}"
        )
        assert fileobj.tell() == 0

    def test_open_checks_eagerly_and_reads_lazily(self, s3_mode):
        body = MagicMock()
        body.iter_chunks.return_value = iter([b"ab", b"cd"])
        s3_mode.get_object.return_value = {"Body": body}

        chunks = exports_storage.open_export(KEY)
        s3_mode.head_object.assert_called_once_with(
            Bucket="test-bucket", Key=f"exports/{KEY}"
        )
        s3_mode.get_object.assert_not_called()

        assert list(chunks) == [b"ab", b"cd"]
        body.close.assert_called_once()

    def test_missing_object_raises_before_reading(self, s3_mode):
        s3_mode.head_object.side_effect = Exception("404")
        with pytest.raises(Exception, match="404"):
            exports_storage.open_export(KEY)
        s3_mode.get_object.assert_not_called()

    def test_body_closed_when_client_leaves_early(self, s3_mode):
        body = MagicMock()
        body.iter_chunks.return_value = iter([b"ab", b"cd"])
        s3_mode.get_object.return_value = {"Body": body}

        chunks = exports_storage.open_export(KEY)
        next(chunks)
        chunks.close()
        body.close.assert_called_once()
