"""Unit tests for ``app.services.ingest_runs`` and the tasks driving the runs.

Run against the real Redis, under source ids no real feed or server has, with
the active-run set moved to a test key so live runs don't count.
"""

import time
from unittest.mock import MagicMock, patch

import pytest

from app.services import ingest_runs
from app.services.redis import get_redis_client
from app.worker import tasks as worker_tasks

FEED_ID = 990001
OTHER_FEED_ID = 990002
USER_ID = 1


@pytest.fixture(autouse=True)
def isolated_runs(monkeypatch):
    monkeypatch.setattr(ingest_runs, "ACTIVE_KEY", "ingest:test:active")
    redis = get_redis_client()

    def clean():
        keys = list(redis.scan_iter("ingest:feed:99000*"))
        redis.delete("ingest:test:active", *keys)

    clean()
    yield
    clean()


def _run(feed_id=FEED_ID):
    return ingest_runs.status("feed", feed_id)["current"]


def _last(feed_id=FEED_ID):
    return ingest_runs.status("feed", feed_id)["last"]


class TestIngestRuns:
    def test_a_source_has_one_run_at_a_time(self):
        assert ingest_runs.claim("feed", FEED_ID, USER_ID)
        assert not ingest_runs.claim("feed", FEED_ID, USER_ID)
        assert _run()["status"] == ingest_runs.QUEUED
        assert _run()["user_id"] == USER_ID

    def test_admission_is_capped(self):
        for feed_id in (FEED_ID, OTHER_FEED_ID):
            ingest_runs.claim("feed", feed_id, USER_ID)

        assert ingest_runs.admit("feed", FEED_ID, 1)
        assert not ingest_runs.admit("feed", OTHER_FEED_ID, 1)
        assert _run()["status"] == ingest_runs.RUNNING
        assert _run(OTHER_FEED_ID)["status"] == ingest_runs.QUEUED

        ingest_runs.finish("feed", FEED_ID)
        assert ingest_runs.admit("feed", OTHER_FEED_ID, 1)

    def test_no_cap_with_zero(self):
        for feed_id in (FEED_ID, OTHER_FEED_ID):
            ingest_runs.claim("feed", feed_id, USER_ID)
            assert ingest_runs.admit("feed", feed_id, 0)

    def test_a_dead_run_frees_its_slot(self):
        get_redis_client().zadd(
            ingest_runs.ACTIVE_KEY,
            {"feed:%s" % OTHER_FEED_ID: 1},  # last heartbeat in 1970
        )
        ingest_runs.claim("feed", FEED_ID, USER_ID)
        assert ingest_runs.admit("feed", FEED_ID, 1)

    def test_events_need_an_open_run(self):
        assert ingest_runs.add_events("feed", FEED_ID, ["a", "b"]) == 0
        assert ingest_runs.take("feed", FEED_ID) == []

    def test_events_are_taken_in_batches_and_put_back_in_order(self):
        ingest_runs.claim("feed", FEED_ID, USER_ID)
        assert ingest_runs.add_events("feed", FEED_ID, ["a", "b", "c", "d"]) == 4

        batch = ingest_runs.take("feed", FEED_ID, 3)
        assert batch == ["a", "b", "c"]
        ingest_runs.put_back("feed", FEED_ID, batch[1:])

        assert ingest_runs.take("feed", FEED_ID, 10) == ["b", "c", "d"]
        assert _run()["total"] == 4

    def test_the_last_drainer_closes_the_run(self):
        ingest_runs.claim("feed", FEED_ID, USER_ID)
        ingest_runs.admit("feed", FEED_ID, 0)
        ingest_runs.add_events("feed", FEED_ID, ["a", "b"])
        ingest_runs.set_drainers("feed", FEED_ID, 2)
        ingest_runs.record("feed", FEED_ID, 1, 1)

        assert not ingest_runs.drainer_done("feed", FEED_ID)
        assert ingest_runs.drainer_done("feed", FEED_ID)
        ingest_runs.finish("feed", FEED_ID)

        assert _run() is None
        last = _last()
        assert last["status"] == ingest_runs.DONE
        assert (last["total"], last["done"], last["failed"]) == (2, 1, 1)
        assert last["finished_at"] >= last["started_at"]
        assert ingest_runs.active_runs() == []

    def test_cancelling_a_waiting_run_closes_it(self):
        ingest_runs.claim("feed", FEED_ID, USER_ID)
        ingest_runs.cancel("feed", FEED_ID, "the feed was disabled")

        assert _run() is None
        assert _last()["status"] == ingest_runs.CANCELLED
        assert _last()["error"] == "the feed was disabled"

    def test_cancelling_an_ingesting_run_closes_it_at_once(self):
        # Its drain tasks may be far down the queue: it doesn't wait for them.
        ingest_runs.claim("feed", FEED_ID, USER_ID)
        ingest_runs.admit("feed", FEED_ID, 0)
        ingest_runs.add_events("feed", FEED_ID, ["a", "b"])
        ingest_runs.set_drainers("feed", FEED_ID, 2)

        ingest_runs.cancel("feed", FEED_ID, "cancelled by user id=1")

        assert _run() is None
        assert ingest_runs.take("feed", FEED_ID) == []
        assert _last()["status"] == ingest_runs.CANCELLED
        assert _last()["error"] == "cancelled by user id=1"
        assert ingest_runs.active_runs() == []

    def test_each_run_has_its_own_id(self):
        ingest_runs.claim("feed", FEED_ID, USER_ID)
        first = ingest_runs.run_id("feed", FEED_ID)
        ingest_runs.finish("feed", FEED_ID)
        assert ingest_runs.run_id("feed", FEED_ID) is None

        ingest_runs.claim("feed", FEED_ID, USER_ID)
        assert ingest_runs.run_id("feed", FEED_ID) not in (None, first)

    def test_open_runs_include_waiting_ones(self):
        for feed_id in (FEED_ID, OTHER_FEED_ID):
            ingest_runs.claim("feed", feed_id, USER_ID)
        ingest_runs.admit("feed", FEED_ID, 1)
        ingest_runs.add_events("feed", FEED_ID, ["a", "b"])

        runs = {
            run["source_id"]: run
            for run in ingest_runs.open_runs()
            if run["kind"] == "feed" and run["source_id"] in (FEED_ID, OTHER_FEED_ID)
        }
        assert runs[FEED_ID]["status"] == ingest_runs.RUNNING
        assert runs[FEED_ID]["pending"] == 2
        assert runs[OTHER_FEED_ID]["status"] == ingest_runs.QUEUED

        ingest_runs.finish("feed", FEED_ID)
        assert FEED_ID not in [run["source_id"] for run in ingest_runs.open_runs()]


def _settings(max_runs=2, paused=False):
    return patch.object(
        worker_tasks, "_ingest_settings", return_value=(max_runs, paused)
    )


class TestFetchFeedTask:
    def test_skipped_while_the_feed_has_a_run(self):
        ingest_runs.claim("feed", FEED_ID, USER_ID)

        with _settings(), patch.object(
            worker_tasks.feeds_repository, "fetch_feed"
        ) as fetch:
            result = worker_tasks.fetch_feed(FEED_ID, USER_ID)

        assert result["result"] == "skipped"
        fetch.assert_not_called()

    def test_waits_for_a_slot(self):
        ingest_runs.claim("feed", OTHER_FEED_ID, USER_ID)
        ingest_runs.admit("feed", OTHER_FEED_ID, 1)

        with _settings(max_runs=1), patch.object(
            worker_tasks.fetch_feed, "apply_async"
        ) as retry, patch.object(worker_tasks.feeds_repository, "fetch_feed") as fetch:
            result = worker_tasks.fetch_feed(FEED_ID, USER_ID)

        assert result["result"] == "queued"
        fetch.assert_not_called()
        assert retry.call_args.args == ((FEED_ID, USER_ID), {"queued": True})
        assert retry.call_args.kwargs["countdown"] == ingest_runs.QUEUED_RETRY_SECONDS
        assert _run()["status"] == ingest_runs.QUEUED

    def test_waits_while_ingestion_is_paused(self):
        with _settings(paused=True), patch.object(
            worker_tasks.fetch_feed, "apply_async"
        ) as retry, patch.object(worker_tasks.feeds_repository, "fetch_feed") as fetch:
            result = worker_tasks.fetch_feed(FEED_ID, USER_ID)

        assert result["result"] == "queued"
        fetch.assert_not_called()
        retry.assert_called_once()

    def test_a_cancelled_waiting_run_does_not_come_back(self):
        with _settings(), patch.object(
            worker_tasks.feeds_repository, "fetch_feed"
        ) as fetch:
            result = worker_tasks.fetch_feed(FEED_ID, USER_ID, queued=True)

        assert result["result"] == "cancelled"
        fetch.assert_not_called()
        assert _run() is None

    def test_a_failed_listing_closes_the_run(self):
        with _settings(), patch.object(worker_tasks, "Session"), patch.object(
            worker_tasks.users_repository, "get_user_by_id"
        ), patch.object(
            worker_tasks.feeds_repository,
            "fetch_feed",
            side_effect=Exception("Failed to fetch the feed manifest: HTTP 404"),
        ):
            with pytest.raises(Exception):
                worker_tasks.fetch_feed(FEED_ID, USER_ID)

        assert _run() is None
        assert _last()["status"] == ingest_runs.FAILED
        assert "HTTP 404" in _last()["error"]
        assert ingest_runs.active_runs() == []


class TestDrainIngestRun:
    def _open(self, events):
        ingest_runs.claim("feed", FEED_ID, USER_ID)
        ingest_runs.admit("feed", FEED_ID, 0)
        with patch.object(worker_tasks.drain_ingest_run, "delay") as delay:
            worker_tasks.start_ingest_drainers(
                "feed",
                FEED_ID,
                USER_ID,
                ingest_runs.add_events("feed", FEED_ID, events),
            )
        return delay

    def _drain(self, feed=None, process=None):
        feed = feed if feed is not None else MagicMock(enabled=True)
        with _settings(), patch.object(worker_tasks, "Session"), patch.object(
            worker_tasks.users_repository, "get_user_by_id"
        ), patch.object(
            worker_tasks.feeds_repository, "get_feed_by_id", return_value=feed
        ), patch.object(
            worker_tasks.attributes_repository, "bulk_ingest"
        ), patch.object(
            worker_tasks.feeds_repository, "process_feed_event", side_effect=process
        ) as processed, patch.object(
            worker_tasks.drain_ingest_run, "delay"
        ) as next_turn:
            result = worker_tasks.drain_ingest_run("feed", FEED_ID, USER_ID)
        return result, processed, next_turn

    def test_drainers_are_started_for_the_run(self):
        delay = self._open(["e%s" % i for i in range(3 * ingest_runs.BATCH_SIZE)])
        assert delay.call_count == ingest_runs.DRAINERS_PER_RUN

    def test_a_small_run_gets_a_single_drainer(self):
        delay = self._open(["a"])
        assert delay.call_count == 1

    def test_a_run_with_nothing_to_ingest_is_closed(self):
        self._open([])
        assert _run() is None
        assert _last()["status"] == ingest_runs.DONE

    def test_ingests_a_batch_and_queues_the_next_turn(self):
        self._open(["e%s" % i for i in range(ingest_runs.BATCH_SIZE + 1)])

        result, processed, next_turn = self._drain(
            process=lambda db, uuid, feed, user: (
                (_ for _ in ()).throw(ValueError("bad")) if uuid == "e1" else None
            )
        )

        assert processed.call_count == ingest_runs.BATCH_SIZE
        assert (result["ingested"], result["failed"]) == (ingest_runs.BATCH_SIZE - 1, 1)
        next_turn.assert_called_once_with(
            "feed", FEED_ID, USER_ID, ingest_runs.run_id("feed", FEED_ID)
        )
        assert _run()["pending"] == 1

    def test_the_last_turn_closes_the_run(self):
        self._open(["a"])

        self._drain()  # ingests "a", queues another turn
        _, processed, next_turn = self._drain()  # finds nothing left

        processed.assert_not_called()
        next_turn.assert_not_called()
        assert _run() is None
        last = _last()
        assert (last["status"], last["total"], last["done"]) == (ingest_runs.DONE, 1, 1)

    def test_a_disabled_feed_cancels_its_run(self):
        self._open(["a", "b"])

        _, processed, next_turn = self._drain(feed=MagicMock(enabled=False))

        processed.assert_not_called()
        next_turn.assert_not_called()
        assert _run() is None
        assert _last()["status"] == ingest_runs.CANCELLED

    def test_a_run_cancelled_mid_batch_is_left_closed(self):
        self._open(["a", "b"])

        result, _, next_turn = self._drain(
            process=lambda db, uuid, feed, user: ingest_runs.cancel("feed", FEED_ID)
        )

        assert result["result"] == "cancelled"
        next_turn.assert_not_called()
        assert _run() is None
        assert _last()["status"] == ingest_runs.CANCELLED

    def test_a_drain_task_of_an_earlier_run_leaves_the_new_one_alone(self):
        self._open(["a"])
        earlier = ingest_runs.run_id("feed", FEED_ID)
        ingest_runs.cancel("feed", FEED_ID)
        self._open(["b"])

        with patch.object(
            worker_tasks.feeds_repository, "process_feed_event"
        ) as processed:
            result = worker_tasks.drain_ingest_run("feed", FEED_ID, USER_ID, earlier)

        assert result["result"] == "skipped"
        processed.assert_not_called()
        assert _run()["pending"] == 1

    def test_a_run_opened_before_runs_had_ids_is_still_drained(self):
        # Under way during the upgrade that added run ids.
        self._open(["a"])
        get_redis_client().hdel("ingest:feed:%s:run" % FEED_ID, "id")

        result, processed, next_turn = self._drain()

        assert result["result"] == "success"
        processed.assert_called_once()
        next_turn.assert_called_once_with("feed", FEED_ID, USER_ID, None)

    def test_a_closed_run_is_not_drained(self):
        result, processed, _ = self._drain()

        assert result["result"] == "skipped"
        processed.assert_not_called()


class TestIngestFollowUps:
    """Follow-ups an ingest generates stay on the ingest queue."""

    def test_bulk_object_follow_ups_go_to_the_ingest_queue(self):
        with patch.object(
            worker_tasks.handle_created_object, "apply_async"
        ) as apply_async, patch.object(
            worker_tasks.handle_created_object, "delay"
        ) as delay:
            worker_tasks.enqueue_created_object("o", "e", True)
            worker_tasks.enqueue_created_object("o", "e", False)

        apply_async.assert_called_once_with(
            ("o", "e", True), queue=worker_tasks.INGEST_QUEUE
        )
        delay.assert_called_once_with("o", "e", False)

    def test_objects_created_during_an_ingest_wait_for_its_batch(self):
        from app.repositories import attributes as attributes_repository

        batch = {"created": [], "updated": [], "handled": [], "objects": []}
        token = attributes_repository._bulk_ingest.set(batch)
        try:
            with patch.object(
                worker_tasks.handle_created_object, "apply_async"
            ) as apply_async:
                worker_tasks.enqueue_created_object("o", "e", True)
        finally:
            attributes_repository._bulk_ingest.reset(token)

        apply_async.assert_not_called()
        assert batch["objects"] == [["o", "e"]]

    def test_reactor_dispatch_follows_the_queue_it_is_given(self):
        with patch.object(
            worker_tasks.reactor_repository, "has_active_subscriber", return_value=True
        ), patch.object(
            worker_tasks.reactor_dispatch, "apply_async"
        ) as apply_async, patch.object(
            worker_tasks.reactor_dispatch, "delay"
        ) as delay:
            worker_tasks._dispatch_if_subscribed(
                "attribute", "created", {"x": 1}, queue=worker_tasks.INGEST_QUEUE
            )

        apply_async.assert_called_once_with(
            ("attribute", "created", {"x": 1}), queue=worker_tasks.INGEST_QUEUE
        )
        delay.assert_not_called()


class TestReviveStalledRuns:
    def _running(self, events, updated_at):
        ingest_runs.claim("feed", FEED_ID, USER_ID)
        ingest_runs.admit("feed", FEED_ID, 0)
        ingest_runs.add_events("feed", FEED_ID, events)
        ingest_runs.set_drainers("feed", FEED_ID, 1)
        get_redis_client().hset(
            "ingest:feed:%s:run" % FEED_ID, "updated_at", updated_at
        )

    def test_a_progressing_run_is_left_alone(self):
        self._running(["a"], int(time.time()))
        assert ingest_runs.stalled_runs() == []

    def test_a_stalled_run_gets_its_drainers_back(self):
        self._running(["a", "b"], 1)

        with patch.object(worker_tasks.drain_ingest_run, "delay") as delay:
            assert worker_tasks.revive_stalled_ingest_runs() == 1

        delay.assert_called_once_with(
            "feed", FEED_ID, USER_ID, ingest_runs.run_id("feed", FEED_ID)
        )
        assert ingest_runs.stalled_runs() == []
        assert _run()["pending"] == 2

    def test_a_stalled_run_with_nothing_left_is_closed(self):
        self._running([], 1)

        with patch.object(worker_tasks.drain_ingest_run, "delay") as delay:
            assert worker_tasks.revive_stalled_ingest_runs() == 0

        delay.assert_not_called()
        assert _run() is None
        assert _last()["status"] == ingest_runs.FAILED
        assert ingest_runs.active_runs() == []

    def test_a_paused_run_is_not_stalled(self):
        self._running(["a"], 1)

        with _settings(paused=True), patch.object(
            worker_tasks.drain_ingest_run, "apply_async"
        ):
            result = worker_tasks.drain_ingest_run("feed", FEED_ID, USER_ID)

        assert result["result"] == "queued"
        assert ingest_runs.stalled_runs() == []
        assert _run()["pending"] == 1
