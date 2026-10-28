"""Ingestion runs: feed fetches and MISP server pulls, bounded.

A MISP feed or server lists thousands of events. Queueing one task per event up
front buries every other background task behind them, and lets any number of
sources ingest at the same time. Instead each fetch (or pull) is a *run*:

- at most one run per source: fetching a feed that is already being fetched is
  skipped rather than queued a second time;
- at most ``ingest.max_concurrent_runs`` runs ingest at once (runtime setting);
  the others wait as ``queued`` and try again every QUEUED_RETRY_SECONDS, as
  they do while ``ingest.paused`` is set;
- the events to ingest are kept in a Redis list, and DRAINERS_PER_RUN tasks
  take them BATCH_SIZE at a time, each queueing its next turn at the back of
  the ``ingest`` queue. The queue holds a few messages per run instead of one
  per event, and concurrent runs take turns.

Run state lives in Redis and expires RUN_TTL_SECONDS after the last progress,
so a run whose worker died frees its slot by itself. The events such a worker
had taken are not lost for good: the next fetch finds them missing, or older
than the source's copy, and fetches them again.
"""

import time
from typing import Iterable, Optional

from app.services.redis import get_redis_client

KINDS = ("feed", "server")

QUEUED = "queued"
RUNNING = "running"
DONE = "done"
FAILED = "failed"
CANCELLED = "cancelled"
CANCELLING = "cancelling"

# Events one drain task ingests before handing the run's next turn back to
# the queue.
BATCH_SIZE = 10
# Drain tasks per run: how many of its batches can be ingested at once.
DRAINERS_PER_RUN = 2
QUEUED_RETRY_SECONDS = 60
# A run with no progress for this long is considered dead and frees its slot.
RUN_TTL_SECONDS = 3 * 3600
# A run without progress for this long lost its drain tasks: longer than one
# may run (tasks.DRAIN_SOFT_TIME_LIMIT).
STALLED_SECONDS = 45 * 60
# How long the summary of a source's last finished run is kept.
LAST_RUN_TTL_SECONDS = 30 * 86400

ACTIVE_KEY = "ingest:active"
PUSH_CHUNK = 1000

_COUNTERS = ("total", "done", "failed", "drainers")


def _key(kind: str, source_id: int, part: str) -> str:
    return f"ingest:{kind}:{source_id}:{part}"


def _member(kind: str, source_id: int) -> str:
    return f"{kind}:{source_id}"


def _decode(run: dict) -> Optional[dict]:
    if not run:
        return None
    decoded = dict(run)
    for field in _COUNTERS + ("user_id",):
        if field in decoded:
            decoded[field] = int(decoded[field])
    for field in ("queued_at", "started_at", "updated_at", "finished_at"):
        if field in decoded:
            decoded[field] = int(float(decoded[field]))
    decoded.pop("drainers", None)
    if decoded.pop("cancelled", None) and decoded.get("status") == RUNNING:
        # Its drain tasks finish the batches in hand, then close it.
        decoded["status"] = CANCELLING
    return decoded


def claim(kind: str, source_id: int, user_id: int) -> bool:
    """Open a run for a source, unless it already has one."""
    redis = get_redis_client()
    run = _key(kind, source_id, "run")

    pipe = redis.pipeline()
    pipe.hsetnx(run, "status", QUEUED)
    pipe.expire(run, RUN_TTL_SECONDS)
    claimed, _ = pipe.execute()
    if not claimed:
        return False

    now = int(time.time())
    redis.hset(
        run,
        mapping={
            "user_id": user_id,
            "queued_at": now,
            "updated_at": now,
            "total": 0,
            "done": 0,
            "failed": 0,
            "drainers": 0,
        },
    )
    return True


def is_open(kind: str, source_id: int) -> bool:
    return bool(get_redis_client().exists(_key(kind, source_id, "run")))


def admit(kind: str, source_id: int, max_runs: int) -> bool:
    """Take one of the ``max_runs`` ingestion slots (0: no limit).

    Two runs admitted at the same instant can both see the limit exceeded and
    both back off; they retry shortly, which is cheaper than a lock.
    """
    redis = get_redis_client()
    now = time.time()
    member = _member(kind, source_id)

    redis.zremrangebyscore(ACTIVE_KEY, "-inf", now - RUN_TTL_SECONDS)
    redis.zadd(ACTIVE_KEY, {member: now})
    if max_runs > 0 and redis.zcard(ACTIVE_KEY) > max_runs:
        redis.zrem(ACTIVE_KEY, member)
        return False

    redis.hset(
        _key(kind, source_id, "run"),
        mapping={"status": RUNNING, "started_at": int(now), "updated_at": int(now)},
    )
    heartbeat(kind, source_id)
    return True


def heartbeat(kind: str, source_id: int) -> None:
    """Keep a live run (and its slot) from expiring.

    Not progress: a run that only heartbeats is still stalled (see record).
    """
    redis = get_redis_client()
    now = time.time()
    pipe = redis.pipeline()
    pipe.expire(_key(kind, source_id, "run"), RUN_TTL_SECONDS)
    pipe.expire(_key(kind, source_id, "pending"), RUN_TTL_SECONDS)
    pipe.zadd(ACTIVE_KEY, {_member(kind, source_id): now}, xx=True)
    pipe.execute()


def add_events(kind: str, source_id: int, event_uuids: Iterable[str]) -> int:
    """Queue events for the run to ingest; returns how many were added.

    Nothing is added without an open run, so a run cancelled while its source
    was being listed stays cancelled.
    """
    redis = get_redis_client()
    if not redis.exists(_key(kind, source_id, "run")):
        return 0
    pending = _key(kind, source_id, "pending")
    event_uuids = [str(event_uuid) for event_uuid in event_uuids]

    for start in range(0, len(event_uuids), PUSH_CHUNK):
        redis.rpush(pending, *event_uuids[start : start + PUSH_CHUNK])
    if event_uuids:
        redis.hincrby(_key(kind, source_id, "run"), "total", len(event_uuids))
        heartbeat(kind, source_id)
    return len(event_uuids)


def set_drainers(kind: str, source_id: int, count: int) -> None:
    get_redis_client().hset(_key(kind, source_id, "run"), "drainers", count)


def take(kind: str, source_id: int, size: int = BATCH_SIZE) -> list[str]:
    return get_redis_client().lpop(_key(kind, source_id, "pending"), size) or []


def put_back(kind: str, source_id: int, event_uuids: list[str]) -> None:
    """Return events a drain task took but did not get to."""
    if event_uuids:
        get_redis_client().lpush(
            _key(kind, source_id, "pending"), *reversed(event_uuids)
        )


def record(kind: str, source_id: int, done: int, failed: int) -> None:
    redis = get_redis_client()
    run = _key(kind, source_id, "run")
    if not redis.exists(run):
        return
    pipe = redis.pipeline()
    pipe.hincrby(run, "done", done)
    pipe.hincrby(run, "failed", failed)
    pipe.hset(run, "updated_at", int(time.time()))
    pipe.execute()
    heartbeat(kind, source_id)


def drainer_done(kind: str, source_id: int) -> bool:
    """A drain task found nothing left; True when it was the run's last one."""
    redis = get_redis_client()
    run = _key(kind, source_id, "run")
    if not redis.exists(run):
        return False
    return redis.hincrby(run, "drainers", -1) <= 0


def cancel(kind: str, source_id: int, reason: str = "") -> None:
    """Drop the events a run has yet to ingest; its drain tasks then finish it."""
    redis = get_redis_client()
    run = _key(kind, source_id, "run")
    redis.delete(_key(kind, source_id, "pending"))
    if redis.exists(run):
        redis.hset(run, mapping={"cancelled": 1, "error": reason})
        if int(redis.hget(run, "drainers") or 0) <= 0:
            # Not ingesting yet (queued, or listing the source's events):
            # nothing would come back to finish it.
            finish(kind, source_id)


def finish(kind: str, source_id: int, status: str = DONE, error: str = "") -> None:
    """Close a run, keep its summary as the source's last run, free its slot."""
    redis = get_redis_client()
    run_key = _key(kind, source_id, "run")
    run = redis.hgetall(run_key)

    if run:
        if run.get("cancelled"):
            # Keeps the reason it was cancelled for.
            status, error = CANCELLED, run.get("error") or error
        summary = {
            **{k: v for k, v in run.items() if k not in ("drainers", "cancelled")},
            "status": status,
            "finished_at": int(time.time()),
        }
        if error:
            summary["error"] = error
        last = _key(kind, source_id, "last")
        pipe = redis.pipeline()
        pipe.delete(last)
        pipe.hset(last, mapping=summary)
        pipe.expire(last, LAST_RUN_TTL_SECONDS)
        pipe.execute()

    redis.delete(run_key, _key(kind, source_id, "pending"))
    redis.zrem(ACTIVE_KEY, _member(kind, source_id))


def status(kind: str, source_id: int) -> dict:
    """The source's current run (if any), with what is left, and its last run."""
    redis = get_redis_client()
    current = _decode(redis.hgetall(_key(kind, source_id, "run")))
    if current is not None:
        current["pending"] = redis.llen(_key(kind, source_id, "pending"))
    return {
        "current": current,
        "last": _decode(redis.hgetall(_key(kind, source_id, "last"))),
    }


def stalled_runs(stalled_seconds: int = STALLED_SECONDS) -> list[dict]:
    """Admitted runs without progress for ``stalled_seconds``.

    A drain task killed mid-batch (a worker restarted or OOM-killed) was
    already acknowledged, so it is not redelivered and its run would sit on
    its slot, ingesting nothing, until it expires.
    """
    now = time.time()
    stalled = []
    for run in active_runs():
        current = status(run["kind"], run["source_id"])["current"]
        if (
            current is not None
            and current["status"] in (RUNNING, CANCELLING)
            and now - current.get("updated_at", now) >= stalled_seconds
        ):
            stalled.append(
                {
                    **run,
                    "user_id": current.get("user_id"),
                    "pending": current["pending"],
                }
            )
    return stalled


def active_runs() -> list[dict]:
    """Every run ingesting now, as ``{"kind", "source_id"}`` (stale ones dropped)."""
    redis = get_redis_client()
    redis.zremrangebyscore(ACTIVE_KEY, "-inf", time.time() - RUN_TTL_SECONDS)
    runs = []
    for member in redis.zrange(ACTIVE_KEY, 0, -1):
        kind, _, source_id = member.partition(":")
        runs.append({"kind": kind, "source_id": int(source_id)})
    return runs
