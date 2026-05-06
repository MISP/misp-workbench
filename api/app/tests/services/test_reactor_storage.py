"""Unit tests for ``app/services/tech_lab/reactor/storage.py``."""

import os
import shutil
from unittest.mock import MagicMock, patch

import pytest
from app.services.tech_lab.reactor import storage


# All keys land under /tmp in local mode. Use a unique prefix per test class so
# we can recursively clean up without touching the rest of /tmp.
LOCAL_PREFIX = "reactor-storage-tests"


def _key(*parts: str) -> str:
    return "/".join((LOCAL_PREFIX, *parts))


@pytest.fixture
def local_mode(monkeypatch):
    """Force the local backend and clean up any files we create."""
    from app.settings import get_settings

    monkeypatch.setattr(get_settings().Storage, "engine", "local")
    yield
    base = os.path.join(storage.LOCAL_BASE, LOCAL_PREFIX)
    if os.path.isdir(base):
        shutil.rmtree(base, ignore_errors=True)


@pytest.fixture
def s3_mode(monkeypatch):
    """Force the s3 backend and patch the S3 client. Yields the mock client."""
    from app.settings import get_settings

    monkeypatch.setattr(get_settings().Storage, "engine", "s3")
    monkeypatch.setattr(get_settings().Storage.s3, "bucket", "test-bucket")
    client = MagicMock()
    with patch.object(storage, "get_s3_client", return_value=client):
        yield client


# ──────────────────────────────────────────────────────────────────────────
# _local_path
# ──────────────────────────────────────────────────────────────────────────


class TestLocalPath:
    def test_resolves_simple_key(self):
        assert storage._local_path("reactor/scripts/abc.py") == "/tmp/reactor/scripts/abc.py"

    def test_normalises_redundant_segments(self):
        assert storage._local_path("reactor/./scripts/abc.py") == "/tmp/reactor/scripts/abc.py"

    def test_rejects_parent_traversal(self):
        with pytest.raises(RuntimeError, match="invalid reactor storage path"):
            storage._local_path("../etc/passwd")

    def test_rejects_traversal_that_escapes_base(self):
        with pytest.raises(RuntimeError, match="invalid reactor storage path"):
            storage._local_path("reactor/../../etc/passwd")

    def test_rejects_absolute_key_outside_base(self):
        # An absolute key bypasses the join, so the result must not be /tmp/...
        with pytest.raises(RuntimeError, match="invalid reactor storage path"):
            storage._local_path("/etc/passwd")


# ──────────────────────────────────────────────────────────────────────────
# Local backend
# ──────────────────────────────────────────────────────────────────────────


class TestLocalBackend:
    def test_write_then_read_roundtrip(self, local_mode):
        key = _key("scripts", "hello.py")
        storage.write_object(key, b"print('hi')")
        assert storage.read_object(key) == b"print('hi')"

    def test_write_creates_intermediate_directories(self, local_mode):
        key = _key("runs", "deeply", "nested", "1.log")
        storage.write_object(key, b"line\n")
        assert os.path.isfile(os.path.join(storage.LOCAL_BASE, key))

    def test_write_overwrites_existing(self, local_mode):
        key = _key("scripts", "overwrite.py")
        storage.write_object(key, b"v1")
        storage.write_object(key, b"v2")
        assert storage.read_object(key) == b"v2"

    def test_read_missing_raises_filenotfound(self, local_mode):
        with pytest.raises(FileNotFoundError):
            storage.read_object(_key("missing.txt"))

    def test_delete_removes_file(self, local_mode):
        key = _key("scripts", "to-delete.py")
        storage.write_object(key, b"x")
        storage.delete_object(key)
        assert not os.path.exists(os.path.join(storage.LOCAL_BASE, key))

    def test_delete_missing_is_silent(self, local_mode):
        # Must not raise for absent files — callers fire-and-forget on cleanup.
        storage.delete_object(_key("never-existed.log"))

    def test_delete_swallows_unexpected_errors(self, local_mode):
        # Local branch uses os.remove; raise from there to exercise the
        # try/except guard.
        with patch("app.services.tech_lab.reactor.storage.os.path.exists", return_value=True), \
                patch("app.services.tech_lab.reactor.storage.os.remove", side_effect=OSError("denied")):
            storage.delete_object(_key("boom.log"))  # must not raise

    def test_delete_empty_key_noops(self, local_mode):
        # Should not even consult settings/backend when key is empty.
        with patch.object(storage, "get_settings") as gs:
            storage.delete_object("")
            storage.delete_object(None)  # type: ignore[arg-type]
        gs.assert_not_called()

    def test_object_exists_true_after_write(self, local_mode):
        key = _key("scripts", "exists.py")
        storage.write_object(key, b"x")
        assert storage.object_exists(key) is True

    def test_object_exists_false_when_absent(self, local_mode):
        assert storage.object_exists(_key("nope.py")) is False

    def test_object_exists_false_for_empty_key(self, local_mode):
        # Same short-circuit as delete_object — never hits the backend.
        with patch.object(storage, "get_settings") as gs:
            assert storage.object_exists("") is False
            assert storage.object_exists(None) is False  # type: ignore[arg-type]
        gs.assert_not_called()


# ──────────────────────────────────────────────────────────────────────────
# S3 backend
# ──────────────────────────────────────────────────────────────────────────


class TestS3Backend:
    def test_write_object_calls_put_object(self, s3_mode):
        storage.write_object("reactor/scripts/x.py", b"body")
        s3_mode.put_object.assert_called_once_with(
            Bucket="test-bucket", Key="reactor/scripts/x.py", Body=b"body"
        )

    def test_read_object_returns_body_bytes(self, s3_mode):
        body = MagicMock()
        body.read.return_value = b"hello"
        s3_mode.get_object.return_value = {"Body": body}
        assert storage.read_object("reactor/scripts/x.py") == b"hello"
        s3_mode.get_object.assert_called_once_with(
            Bucket="test-bucket", Key="reactor/scripts/x.py"
        )

    def test_delete_object_calls_delete_object(self, s3_mode):
        storage.delete_object("reactor/runs/1.log")
        s3_mode.delete_object.assert_called_once_with(
            Bucket="test-bucket", Key="reactor/runs/1.log"
        )

    def test_delete_object_swallows_s3_errors(self, s3_mode):
        s3_mode.delete_object.side_effect = RuntimeError("upstream broken")
        # Must not propagate — cleanup is best-effort.
        storage.delete_object("reactor/runs/1.log")

    def test_object_exists_true_when_head_succeeds(self, s3_mode):
        s3_mode.head_object.return_value = {}
        assert storage.object_exists("reactor/scripts/x.py") is True
        s3_mode.head_object.assert_called_once_with(
            Bucket="test-bucket", Key="reactor/scripts/x.py"
        )

    def test_object_exists_false_when_head_raises(self, s3_mode):
        s3_mode.head_object.side_effect = RuntimeError("404")
        assert storage.object_exists("reactor/scripts/x.py") is False
