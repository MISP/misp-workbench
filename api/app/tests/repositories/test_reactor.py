"""Tests for the reactor repository (CRUD + dispatch)."""

import os
import shutil
from unittest.mock import MagicMock, patch

import pytest
from app.models import reactor as reactor_models
from app.repositories import reactor as reactor_repository


@pytest.fixture(autouse=True)
def _local_storage(monkeypatch):
    from app.settings import get_settings

    monkeypatch.setattr(get_settings().Storage, "engine", "local")
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
        full = os.path.join("/tmp", uri)
        assert os.path.exists(full)
        with open(full) as f:
            assert f.read() == "print('hi')\n"
        assert len(sha) == 64

    def test_read_source_round_trip(self):
        uri, _ = reactor_repository._store_source("x = 1\n")
        assert reactor_repository._read_source(uri) == "x = 1\n"

    def test_delete_source_removes_local_file(self):
        uri, _ = reactor_repository._store_source("y = 2\n")
        full = os.path.join("/tmp", uri)
        assert os.path.exists(full)
        reactor_repository._delete_source(uri)
        assert not os.path.exists(full)


class TestActiveTriggerGate:
    """Coverage for ``has_active_subscriber`` + ``refresh_active_triggers_cache``.

    The gate is a Redis-backed short-circuit so the per-attribute event handler
    can skip the Celery hop when nothing subscribes.
    """

    def test_fails_open_when_sentinel_missing(self):
        # Cold cache: gate must return True so dispatch still happens and the
        # authoritative DB check inside ``dispatch_triggered_scripts`` runs.
        client = MagicMock()
        client.exists.return_value = False
        with patch(
            "app.repositories.reactor.get_redis_client", return_value=client
        ):
            assert reactor_repository.has_active_subscriber("attribute", "created") is True
        client.sismember.assert_not_called()

    def test_fails_open_when_redis_raises(self):
        client = MagicMock()
        client.exists.side_effect = RuntimeError("redis down")
        with patch(
            "app.repositories.reactor.get_redis_client", return_value=client
        ):
            assert reactor_repository.has_active_subscriber("attribute", "created") is True

    def test_returns_true_when_trigger_in_set(self):
        client = MagicMock()
        client.exists.return_value = True
        client.sismember.return_value = 1
        with patch(
            "app.repositories.reactor.get_redis_client", return_value=client
        ):
            assert reactor_repository.has_active_subscriber("attribute", "created") is True
        client.sismember.assert_called_once_with(
            "reactor:active_triggers", "attribute:created"
        )

    def test_returns_false_when_trigger_not_in_set(self):
        client = MagicMock()
        client.exists.return_value = True
        client.sismember.return_value = 0
        with patch(
            "app.repositories.reactor.get_redis_client", return_value=client
        ):
            assert reactor_repository.has_active_subscriber("event", "deleted") is False

    def test_refresh_collects_unique_resource_action_pairs(self):
        s1 = MagicMock(
            status="active",
            triggers=[
                {"resource_type": "attribute", "action": "created"},
                {"resource_type": "event", "action": "published"},
            ],
        )
        s2 = MagicMock(
            status="active",
            # Duplicate of s1's first trigger — should collapse in the set.
            triggers=[{"resource_type": "attribute", "action": "created"}],
        )
        db = _fake_db_with([s1, s2])
        client = MagicMock()
        with patch(
            "app.repositories.reactor.get_redis_client", return_value=client
        ):
            keys = reactor_repository.refresh_active_triggers_cache(db)
        assert keys == {"attribute:created", "event:published"}

    def test_refresh_writes_pipeline_with_delete_sadd_sentinel(self):
        s = MagicMock(
            status="active",
            triggers=[{"resource_type": "attribute", "action": "created"}],
        )
        db = _fake_db_with([s])
        client = MagicMock()
        pipe = MagicMock()
        client.pipeline.return_value = pipe
        with patch(
            "app.repositories.reactor.get_redis_client", return_value=client
        ):
            reactor_repository.refresh_active_triggers_cache(db)

        # delete → sadd → set sentinel → execute, in that order.
        pipe.delete.assert_called_once_with("reactor:active_triggers")
        pipe.sadd.assert_called_once()
        sadd_args = pipe.sadd.call_args.args
        assert sadd_args[0] == "reactor:active_triggers"
        assert set(sadd_args[1:]) == {"attribute:created"}
        pipe.set.assert_called_once_with("reactor:active_triggers:populated", "1")
        pipe.execute.assert_called_once()

    def test_refresh_skips_sadd_when_no_triggers(self):
        # Sentinel must still be set so the gate switches from fail-open to
        # authoritative-empty after the first refresh on an empty install.
        db = _fake_db_with([])
        client = MagicMock()
        pipe = MagicMock()
        client.pipeline.return_value = pipe
        with patch(
            "app.repositories.reactor.get_redis_client", return_value=client
        ):
            keys = reactor_repository.refresh_active_triggers_cache(db)
        assert keys == set()
        pipe.delete.assert_called_once()
        pipe.sadd.assert_not_called()
        pipe.set.assert_called_once_with("reactor:active_triggers:populated", "1")
        pipe.execute.assert_called_once()

    def test_refresh_swallows_redis_errors(self):
        # Refresh must not fail script CRUD if Redis is unreachable; the gate
        # will simply remain in fail-open mode.
        db = _fake_db_with([])
        with patch(
            "app.repositories.reactor.get_redis_client",
            side_effect=RuntimeError("redis down"),
        ):
            # Must not raise.
            assert reactor_repository.refresh_active_triggers_cache(db) == set()
