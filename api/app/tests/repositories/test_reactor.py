"""Tests for the reactor repository (CRUD + dispatch)."""

import os
import shutil
from unittest.mock import MagicMock, patch

import pytest
from app.models import reactor as reactor_models
from app.repositories import reactor as reactor_repository
from app.schemas import reactor as reactor_schemas


@pytest.fixture(autouse=True)
def _local_storage(monkeypatch):
    monkeypatch.setenv("STORAGE_ENGINE", "local")
    base = "/tmp/reactor"
    yield
    if os.path.isdir(base):
        shutil.rmtree(base, ignore_errors=True)


def _fake_db_with(scripts: list[reactor_models.ReactorScript]):
    db = MagicMock()
    chain = db.query.return_value.filter.return_value
    chain.all.return_value = scripts
    return db


class TestDispatchTriggeredScripts:
    def test_no_matching_scripts_returns_empty(self):
        db = _fake_db_with([])
        with patch("app.worker.tasks.run_reactor_script") as mock_task:
            ids = reactor_repository.dispatch_triggered_scripts(
                db, "attribute", "created", {"type": "ip-src"}
            )
        assert ids == []
        mock_task.apply_async.assert_not_called()

    def test_matching_script_creates_run_and_enqueues_task(self):
        script = MagicMock(spec=reactor_models.ReactorScript)
        script.id = 42
        script.status = "active"
        script.triggers = [
            {"resource_type": "attribute", "action": "created"}
        ]

        db = _fake_db_with([script])
        # add() and commit() set the id on the new ReactorRun.
        added_runs: list = []

        def _capture_add(obj):
            if isinstance(obj, reactor_models.ReactorRun):
                obj.id = 7
                added_runs.append(obj)

        db.add.side_effect = _capture_add

        async_result = MagicMock(id="celery-task-99")
        with patch("app.worker.tasks.run_reactor_script") as mock_task:
            mock_task.apply_async.return_value = async_result
            ids = reactor_repository.dispatch_triggered_scripts(
                db, "attribute", "created", {"type": "ip-src"}
            )

        assert ids == [7]
        mock_task.apply_async.assert_called_once_with(
            args=[7], queue="reactor_sandbox"
        )
        assert added_runs[0].triggered_by["resource_type"] == "attribute"
        assert added_runs[0].triggered_by["action"] == "created"

    def test_filter_excludes_non_matching_payload(self):
        script = MagicMock(spec=reactor_models.ReactorScript)
        script.id = 1
        script.status = "active"
        script.triggers = [
            {
                "resource_type": "attribute",
                "action": "created",
                "filters": {"type": "ip-src"},
            }
        ]
        db = _fake_db_with([script])
        with patch("app.worker.tasks.run_reactor_script") as mock_task:
            ids = reactor_repository.dispatch_triggered_scripts(
                db, "attribute", "created", {"type": "url"}
            )
        assert ids == []
        mock_task.apply_async.assert_not_called()


class TestSourceStorage:
    def test_store_source_writes_local_file(self):
        uri, sha = reactor_repository._store_source("print('hi')\n")
        assert uri.startswith("reactor/scripts/")
        full = os.path.join("/tmp/reactor", uri)
        assert os.path.exists(full)
        with open(full) as f:
            assert f.read() == "print('hi')\n"
        assert len(sha) == 64

    def test_read_source_round_trip(self):
        uri, _ = reactor_repository._store_source("x = 1\n")
        assert reactor_repository._read_source(uri) == "x = 1\n"

    def test_delete_source_removes_local_file(self):
        uri, _ = reactor_repository._store_source("y = 2\n")
        full = os.path.join("/tmp/reactor", uri)
        assert os.path.exists(full)
        reactor_repository._delete_source(uri)
        assert not os.path.exists(full)
