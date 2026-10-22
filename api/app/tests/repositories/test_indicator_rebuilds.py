"""Requested rebuilds: a change every score depends on (a source's trust, the
scoring settings) must reach every score, however small, and must not be lost
to a rebuild that read the settings before the change."""

from unittest.mock import MagicMock, patch

from app.repositories import indicators
from app.worker import tasks


class FakeRedis:
    def __init__(self):
        self.keys = {}

    def set(self, key, value, nx=False, ex=None):
        if nx and key in self.keys:
            return None
        self.keys[key] = value
        return True

    def delete(self, *keys):
        for key in keys:
            self.keys.pop(key, None)

    def exists(self, key):
        return key in self.keys


def _rebuild(redis, requested, during_walk=None):
    """Run indicators.rebuild over an empty index, calling ``during_walk``
    while it walks the values."""
    run = MagicMock(written=0, removed=0)
    run.client.delete_by_query.return_value = {"deleted": 0}

    def walk(client):
        if during_walk:
            during_walk()
        return iter(())

    with patch.object(indicators, "_Run", return_value=run) as make_run, patch.object(
        indicators, "_all_values", side_effect=walk
    ), patch.object(indicators, "_orphaned_values", return_value=iter(())):
        result = indicators.rebuild(requested=requested)
    return result, make_run


def test_requests_merge_until_the_queued_rebuild_starts():
    redis = FakeRedis()
    with patch.object(indicators, "get_redis_client", return_value=redis), patch.object(
        tasks.rebuild_indicators, "apply_async"
    ) as queue:
        indicators.request_rebuild()
        indicators.request_rebuild()
    queue.assert_called_once_with(kwargs={"requested": True})


def test_a_request_while_a_requested_rebuild_runs_queues_the_next():
    redis = FakeRedis()
    with patch.object(indicators, "get_redis_client", return_value=redis), patch.object(
        tasks.rebuild_indicators, "apply_async"
    ) as queue:
        indicators.request_rebuild()
        # A feed's modifier saved while the queued rebuild walks the index:
        # that run read the trust before the change.
        result, make_run = _rebuild(
            redis, requested=True, during_walk=indicators.request_rebuild
        )
    assert result is not None
    make_run.assert_called_once_with(exact_scores=True)
    assert queue.call_count == 2
    assert redis.exists(indicators.REBUILD_QUEUED_KEY)
    assert not redis.exists(indicators.LOCK_KEY)


def test_the_hourly_rebuild_leaves_a_pending_request_alone():
    redis = FakeRedis()
    with patch.object(indicators, "get_redis_client", return_value=redis), patch.object(
        tasks.rebuild_indicators, "apply_async"
    ):
        indicators.request_rebuild()
        _, make_run = _rebuild(redis, requested=False)
    # Not exact, and the request it may have started too early for stays
    # pending for the rebuild it queued.
    make_run.assert_called_once_with(exact_scores=False)
    assert redis.exists(indicators.REBUILD_QUEUED_KEY)


def test_a_requested_rebuild_retries_while_the_lock_is_held():
    with patch.object(indicators, "rebuild", return_value=None), patch.object(
        tasks.rebuild_indicators, "apply_async"
    ) as queue:
        tasks.rebuild_indicators(requested=True)
    queue.assert_called_once_with(
        kwargs={"requested": True}, countdown=indicators.REBUILD_RETRY_SECONDS
    )


def test_the_hourly_rebuild_just_skips_a_turn_when_locked():
    with patch.object(indicators, "rebuild", return_value=None), patch.object(
        tasks.rebuild_indicators, "apply_async"
    ) as queue:
        tasks.rebuild_indicators()
    queue.assert_not_called()


def _run(exact_scores):
    run = indicators._Run.__new__(indicators._Run)
    run.exact_scores = exact_scores
    run.scoring = {"refresh_step": 5, "decayed_below": 30}
    return run


def test_exact_scores_write_any_move():
    assert _run(exact_scores=True).score_changed(53, 56)
    assert not _run(exact_scores=True).score_changed(53, 53)


def test_other_runs_write_a_step_or_a_crossing():
    run = _run(exact_scores=False)
    assert not run.score_changed(53, 56)
    assert run.score_changed(53, 58)
    assert run.score_changed(31, 29)
