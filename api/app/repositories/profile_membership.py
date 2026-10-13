"""Which indicators a detection profile selects, run to run.

Query-based deltas report what was *written* since a cursor. An indicator
can leave a profile without being written: its score decays, it ages out, a
source's trust or the profile itself changes. This materialises the member
set of a profile for one consumer (a feed, a sink) and diffs it with the set
that consumer got last time:

- **added**: members that weren't before;
- **removed**: previous members that aren't any more, each with the rule it
  fails (``detection_profiles.REASONS``), or ``deleted``;
- **changed**: members both times whose indicator was written since.

Sets live in Redis while a diff is computed. The previous set comes from the
consumer: a sink keeps its own in Redis (``state_key``), a feed reads it from
its previous full artifact. A diff is only committed once the consumer has
the changes, so a failed delivery is retried with the same diff.
"""

import json
import logging
import uuid as uuid_module
from typing import Iterable, Iterator, Optional

from app.repositories import detection_profiles
from app.repositories import indicators as indicators_repository
from app.repositories import stream_exports
from app.services.opensearch import get_opensearch_client
from app.services.redis import get_redis_client

logger = logging.getLogger(__name__)

KEY_PREFIX = "profile_membership"
# Always in a built set, so an empty membership still exists (and isn't
# mistaken for "never built").
SENTINEL = "\x00built"
CHUNK = 1000


def state_key(owner: str) -> str:
    """Where a sink's (or any owner's) last delivered member set lives."""
    return f"{KEY_PREFIX}:{owner}"


def _sadd(redis, key: str, members: Iterable[str]) -> None:
    batch: list = []
    for member in members:
        batch.append(member)
        if len(batch) >= CHUNK:
            redis.sadd(key, *batch)
            batch = []
    if batch:
        redis.sadd(key, *batch)


def _scan(redis, key: str) -> Iterator[list[str]]:
    batch: list = []
    for member in redis.sscan_iter(key, count=CHUNK):
        member = member.decode() if isinstance(member, bytes) else member
        if member == SENTINEL:
            continue
        batch.append(member)
        if len(batch) >= CHUNK:
            yield batch
            batch = []
    if batch:
        yield batch


def selection(rules, ctx: dict, extra: Optional[dict] = None) -> dict:
    """The profile's query, narrowed by ``extra`` (a feed's own query)."""
    query = detection_profiles.to_query(rules, ctx)
    if extra is None:
        return query
    return {"bool": {"filter": [query, extra]}}


def current_members(rules, ctx: dict, extra: Optional[dict] = None) -> Iterator[str]:
    """The uuids of the indicators the rules (and ``extra``) select now."""
    client = get_opensearch_client()
    for hits in stream_exports.iter_pit_pages(
        client,
        indicators_repository.INDEX,
        selection(rules, ctx, extra),
        source=False,
    ):
        for hit in hits:
            yield hit["_id"]


class Diff:
    """A computed membership diff, waiting for its consumer.

    ``commit`` makes the current set the consumer's previous one;
    ``discard`` drops the work (the next run computes the diff again).
    """

    def __init__(
        self,
        owner: str,
        rules,
        ctx: dict,
        previous_key: Optional[str],
        extra: Optional[dict] = None,
    ):
        self.redis = get_redis_client()
        self.owner = owner
        self.rules = rules
        self.ctx = ctx
        self.extra = extra
        run = uuid_module.uuid4().hex
        self.next_key = f"{KEY_PREFIX}:tmp:{run}:next"
        self.added_key = f"{KEY_PREFIX}:tmp:{run}:added"
        self.removed_key = f"{KEY_PREFIX}:tmp:{run}:removed"
        # A first run (no previous set) has nothing to remove: everything is
        # added.
        self.first = previous_key is None or not self.redis.exists(previous_key)
        self.previous_key = previous_key

        self.redis.sadd(self.next_key, SENTINEL)
        _sadd(self.redis, self.next_key, current_members(rules, ctx, extra))
        if self.first:
            self.redis.sunionstore(self.added_key, [self.next_key])
            self.redis.srem(self.added_key, SENTINEL)
        else:
            self.redis.sdiffstore(self.added_key, [self.next_key, previous_key])
            self.redis.sdiffstore(self.removed_key, [previous_key, self.next_key])
        for key in (self.next_key, self.added_key, self.removed_key):
            self.redis.expire(key, 6 * 3600)

    @property
    def members(self) -> int:
        return max(self.redis.scard(self.next_key) - 1, 0)

    @property
    def added(self) -> int:
        return self.redis.scard(self.added_key)

    @property
    def removed(self) -> int:
        return self.redis.scard(self.removed_key)

    def added_indicators(self) -> Iterator[list[dict]]:
        for ids in _scan(self.redis, self.added_key):
            found = indicators_repository.get_indicators(ids)
            yield [found[i] for i in ids if i in found]

    def removals(self, details_key: Optional[str] = None) -> Iterator[list[dict]]:
        """Removal records: uuid, type, value, reason.

        ``details_key`` (a hash uuid -> {type, value}, see ``load_previous``)
        describes indicators purged since.
        """
        client = get_opensearch_client()
        for ids in _scan(self.redis, self.removed_key):
            known = {}
            if details_key:
                for indicator_id, raw in zip(ids, self.redis.hmget(details_key, ids)):
                    if raw:
                        known[indicator_id] = json.loads(raw)
            docs = {
                d["_id"]: d["_source"]
                for d in client.mget(
                    index=indicators_repository.INDEX, body={"ids": ids}
                )["docs"]
                if d.get("found")
            }
            batch = []
            for indicator_id in ids:
                doc = docs.get(indicator_id)
                fallback = known.get(indicator_id) or {}
                batch.append(
                    {
                        "uuid": indicator_id,
                        "type": (doc or fallback).get("type"),
                        "value": (doc or fallback).get("value"),
                        "action": "remove",
                        "reason": detection_profiles.failing_rule(
                            self.rules, doc, self.ctx
                        )
                        # Back in the profile by now, but not when the set
                        # was taken: report it as changed rules.
                        or "rules",
                    }
                )
            yield batch

    def changed_indicators(self, since: int) -> Iterator[list[dict]]:
        """Members both times whose indicator was written at or after ``since``."""
        if self.first:
            return
        client = get_opensearch_client()
        query = {
            "bool": {
                "filter": [
                    selection(self.rules, self.ctx, self.extra),
                    {"range": {"updated_at": {"gte": since, "format": "epoch_second"}}},
                ]
            }
        }
        for hits in stream_exports.iter_pit_pages(
            client,
            indicators_repository.INDEX,
            query,
            source={"excludes": ["checksum"]},
        ):
            ids = [h["_id"] for h in hits]
            new = self.redis.smismember(self.added_key, ids)
            changed = [h["_source"] for h, is_new in zip(hits, new) if not is_new]
            if changed:
                yield changed

    def keep_released(self, released_key: str) -> None:
        """Leave out additions not in ``released_key`` (a profile's released
        members, see profile_gate): a run sends nothing its profile hasn't
        released, whatever joined since the release."""
        pending = list(self.redis.sdiff([self.added_key, released_key]))
        for start in range(0, len(pending), CHUNK):
            self.withhold(pending[start : start + CHUNK])

    def withhold(self, ids: list[str]) -> None:
        """Leave members out of this run: not sent, not kept as delivered, so
        the next run considers them again."""
        if ids:
            self.redis.srem(self.next_key, *ids)
            self.redis.srem(self.added_key, *ids)

    def commit(self, state: Optional[str] = None) -> None:
        """Keep the current set (as ``state``, a sink's) and drop the rest."""
        pipe = self.redis.pipeline()
        if state:
            pipe.rename(self.next_key, state)
            pipe.persist(state)
        else:
            pipe.delete(self.next_key)
        pipe.delete(self.added_key, self.removed_key)
        pipe.execute()

    def discard(self) -> None:
        self.redis.delete(self.next_key, self.added_key, self.removed_key)


def lines_of(chunks: Iterable[bytes]) -> Iterator[bytes]:
    """The lines of a stored artifact, whatever its chunks."""
    pending = b""
    for chunk in chunks:
        pending += chunk
        *complete, pending = pending.split(b"\n")
        yield from complete
    if pending:
        yield pending


def load_previous(lines: Iterable[bytes]) -> tuple[str, str]:
    """A feed's previous member set, from its last full artifact (NDJSON).

    Returns two temporary Redis keys: the set of uuids, and a hash of
    uuid -> {type, value} describing indicators purged since. Both live in
    Redis, not the worker, however large the feed.
    """
    redis = get_redis_client()
    run = uuid_module.uuid4().hex
    key = f"{KEY_PREFIX}:tmp:{run}:previous"
    details = f"{KEY_PREFIX}:tmp:{run}:details"
    redis.sadd(key, SENTINEL)
    batch: dict = {}
    for line in lines:
        line = line.strip()
        if not line:
            continue
        record = json.loads(line)
        if not record.get("uuid"):
            continue
        batch[record["uuid"]] = json.dumps(
            {"type": record.get("type"), "value": record.get("value")}
        )
        if len(batch) >= CHUNK:
            redis.sadd(key, *batch)
            redis.hset(details, mapping=batch)
            batch = {}
    if batch:
        redis.sadd(key, *batch)
        redis.hset(details, mapping=batch)
    for k in (key, details):
        redis.expire(k, 6 * 3600)
    return key, details
