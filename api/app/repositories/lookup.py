"""Bulk indicator lookup with a Redis hot path.

SIEMs enrich alerts by asking "is any of these values a known indicator?",
mostly about values that are not. A Redis set of the values of live
``to_ids`` attributes answers the misses with one ``SMISMEMBER`` round trip,
so only candidates reach OpenSearch, which then confirms each one and
returns its context.

The set is a *may-contain* prefilter, never the source of truth:

- it must never miss a value that is an indicator, so additions come from a
  delta sync keyed on ``updated_at`` (stamped by the ingest pipeline on every
  write path: API, pulls, feeds, bulk ingest, ``update_by_query``) every few
  seconds;
- it may hold stale values (attribute deleted, ``to_ids`` turned off): every
  hit is verified in OpenSearch, and an hourly rebuild swaps in a fresh set.

Until a set has been built (fresh install, flushed Redis), lookups fall back
to OpenSearch for every value and a rebuild is queued.
"""

import logging
import time
from typing import Iterable, Optional

from app.repositories import stream_exports
from app.services.opensearch import get_opensearch_client
from app.services.redis import get_redis_client

logger = logging.getLogger(__name__)

VALUES_KEY = "lookup:ids_values"
BUILT_AT_KEY = "lookup:ids_values:built_at"
CURSOR_KEY = "lookup:ids_values:cursor"
REBUILD_LOCK_KEY = "lookup:ids_values:rebuild_lock"
SYNC_LOCK_KEY = "lookup:ids_values:sync_lock"
GENERATION_KEY = "lookup:ids_values:generation"
# Always a member of a built set (never a real value: attribute values don't
# start with a NUL byte). A lookup checks it in the same SMISMEMBER call, so a
# set that Redis evicted or someone deleted is noticed instead of answering
# every value with "no match".
SENTINEL = "\x00lookup:ids_values:built"

# Store a sync's cursor only if no rebuild started or finished while it ran:
# a rebuild's swap may have dropped what that sync added to the old set, and
# the rebuild's own (earlier) cursor makes the next sync read it again.
_SET_CURSOR_IF_GENERATION = """
if redis.call('GET', KEYS[1]) == ARGV[1] then
    redis.call('SET', KEYS[2], ARGV[2])
    return 1
end
return 0
"""

MAX_VALUES_PER_REQUEST = 10_000
DEFAULT_MAX_ATTRIBUTES = 10
MAX_ATTRIBUTES = 100
# Attributes one response may carry in total: a 10,000-value batch gets at
# most 5 per value, however high max_attributes is set.
MAX_ATTRIBUTES_PER_RESPONSE = 50_000
# Values per terms aggregation / msearch request.
TERMS_CHUNK = 1000
# keyword sub-fields are mapped with ignore_above: 256.
KEYWORD_IGNORE_ABOVE = 256
REDIS_CHUNK = 10_000
# A delta sync re-reads this far before its cursor, so writes that were not
# yet searchable (refresh interval, clock skew) on the previous run aren't
# missed. SADD is idempotent, so re-reading costs nothing.
SYNC_OVERLAP_SECONDS = 30
REBUILD_LOCK_SECONDS = 30 * 60
SYNC_LOCK_SECONDS = 5 * 60


class TooManyValues(ValueError):
    pass


# ── Cache maintenance ─────────────────────────────────────────────────────


def _indicator_filter(to_ids_only: bool = True) -> dict:
    query: dict = {"must_not": [{"term": {"deleted": True}}]}
    if to_ids_only:
        query["filter"] = [{"term": {"to_ids": True}}]
    return query


def _add_values(redis, key: str, values: Iterable[str]) -> int:
    added = 0
    batch: list[str] = []
    for value in values:
        if value:
            batch.append(value)
        if len(batch) >= REDIS_CHUNK:
            added += redis.sadd(key, *batch)
            batch = []
    if batch:
        added += redis.sadd(key, *batch)
    return added


def _scan_values(query: dict) -> Iterable[str]:
    for hits in stream_exports.iter_pit_pages(
        get_opensearch_client(), "misp-attributes", query, source=["value"]
    ):
        for hit in hits:
            yield hit["_source"].get("value")


def rebuild_cache() -> Optional[int]:
    """Build the set from scratch and swap it in atomically.

    Returns its size, or None when another rebuild holds the lock.
    """
    redis = get_redis_client()
    if not redis.set(REBUILD_LOCK_KEY, "1", nx=True, ex=REBUILD_LOCK_SECONDS):
        return None
    try:
        redis.incr(GENERATION_KEY)
        started = int(time.time())
        staging = f"{VALUES_KEY}:staging"
        redis.delete(staging)
        redis.sadd(staging, SENTINEL)
        _add_values(redis, staging, _scan_values({"bool": _indicator_filter()}))
        size = redis.scard(staging) - 1
        pipe = redis.pipeline()
        pipe.rename(staging, VALUES_KEY)
        pipe.set(BUILT_AT_KEY, started)
        # Everything written since the scan began is read again by the next
        # sync, including what syncs during the rebuild added to the old set.
        pipe.set(CURSOR_KEY, started)
        pipe.incr(GENERATION_KEY)
        pipe.execute()
        logger.info("lookup cache rebuilt: %s values", size)
        return size
    finally:
        redis.delete(REBUILD_LOCK_KEY, f"{REBUILD_LOCK_KEY}:queued")


def sync_cache() -> Optional[int]:
    """Add the values of indicators written since the last sync.

    Returns how many new values were added; None when the set hasn't been
    built yet (a rebuild is queued) or another sync is running.
    """
    redis = get_redis_client()
    if not redis.exists(BUILT_AT_KEY):
        request_rebuild()
        return None
    if not redis.set(SYNC_LOCK_KEY, "1", nx=True, ex=SYNC_LOCK_SECONDS):
        return None
    try:
        generation = redis.get(GENERATION_KEY) or "0"
        started = int(time.time())
        cursor = int(redis.get(CURSOR_KEY) or started) - SYNC_OVERLAP_SECONDS
        query = {"bool": _indicator_filter()}
        query["bool"]["filter"].append(
            {"range": {"updated_at": {"gte": cursor, "format": "epoch_second"}}}
        )
        added = _add_values(redis, VALUES_KEY, _scan_values(query))
        redis.eval(
            _SET_CURSOR_IF_GENERATION,
            2,
            GENERATION_KEY,
            CURSOR_KEY,
            generation,
            started,
        )
        if added:
            logger.info("lookup cache sync: %s new values", added)
        return added
    finally:
        redis.delete(SYNC_LOCK_KEY)


def request_rebuild() -> None:
    from app.worker import tasks

    redis = get_redis_client()
    # One queued rebuild at a time, however many lookups notice it's missing.
    if redis.set(f"{REBUILD_LOCK_KEY}:queued", "1", nx=True, ex=REBUILD_LOCK_SECONDS):
        tasks.rebuild_lookup_cache.delay()


def cache_status() -> dict:
    redis = get_redis_client()
    built_at = redis.get(BUILT_AT_KEY)
    return {
        "built": built_at is not None,
        "built_at": int(built_at) if built_at else None,
        "synced_at": int(redis.get(CURSOR_KEY) or 0) or None,
        "values": max(redis.scard(VALUES_KEY) - 1, 0),
        # False when the set vanished (evicted, flushed) behind the markers.
        "intact": bool(redis.sismember(VALUES_KEY, SENTINEL)),
    }


# ── Lookup ────────────────────────────────────────────────────────────────


def _candidates(values: list[str]) -> tuple[list[str], str]:
    """Values worth asking OpenSearch about, and where that answer came from."""
    try:
        redis = get_redis_client()
        if not redis.exists(BUILT_AT_KEY):
            request_rebuild()
            return values, "opensearch"
        hits: list[str] = []
        for start in range(0, len(values), REDIS_CHUNK):
            chunk = values[start : start + REDIS_CHUNK]
            # The sentinel rides along with every chunk: a set missing it was
            # lost, and its silence would read as "no match" for everything.
            built, *members = redis.smismember(VALUES_KEY, [SENTINEL, *chunk])
            if not built:
                logger.warning("lookup cache set is gone; falling back and rebuilding")
                request_rebuild()
                return values, "opensearch"
            hits.extend(v for v, member in zip(chunk, members) if member)
        return hits, "cache"
    except Exception:
        # The cache is an optimisation: without Redis, ask OpenSearch directly.
        logger.exception("lookup cache unavailable; falling back to OpenSearch")
        return values, "opensearch"


ATTRIBUTE_FIELDS = [
    "uuid",
    "type",
    "category",
    "value",
    "to_ids",
    "comment",
    "timestamp",
    "first_seen",
    "last_seen",
    "event_uuid",
    "tags",
    "warninglist_hits",
]
NEWEST_FIRST = [{"timestamp": {"order": "desc", "unmapped_type": "long"}}]


def _find_attributes(
    values: list[str],
    to_ids_only: bool,
    max_attributes: int,
    include_warninglisted: bool = False,
) -> dict[str, dict]:
    """Per value: total matching attributes and the newest ``max_attributes``.

    Bounded by construction: OpenSearch returns at most ``max_attributes``
    documents per value (a top_hits per terms bucket, or a sized search for
    long values) and a total count, however many attributes share the value.
    """
    found: dict[str, dict] = {}
    if not values:
        return found
    client = get_opensearch_client()
    base = _indicator_filter(to_ids_only)
    if not include_warninglisted:
        from app.repositories.warninglists import WARNINGLISTED

        base["must_not"] = base["must_not"] + [WARNINGLISTED]

    short = [v for v in values if len(v) <= KEYWORD_IGNORE_ABOVE]
    for start in range(0, len(short), TERMS_CHUNK):
        chunk = short[start : start + TERMS_CHUNK]
        query = {
            "bool": {
                **base,
                "filter": base.get("filter", [])
                + [{"terms": {"value.keyword": chunk}}],
            }
        }
        response = client.search(
            index="misp-attributes",
            body={
                "size": 0,
                "query": query,
                "aggs": {
                    "values": {
                        "terms": {"field": "value.keyword", "size": len(chunk)},
                        "aggs": {
                            "newest": {
                                "top_hits": {
                                    "size": max_attributes,
                                    "sort": NEWEST_FIRST,
                                    "_source": ATTRIBUTE_FIELDS,
                                }
                            }
                        },
                    }
                },
            },
        )
        for bucket in response["aggregations"]["values"]["buckets"]:
            found[bucket["key"]] = {
                "count": bucket["doc_count"],
                "attributes": [
                    hit["_source"] for hit in bucket["newest"]["hits"]["hits"]
                ],
            }

    # Values past the keyword's ignore_above aren't in value.keyword: one sized
    # phrase search each, sent together.
    long_values = [v for v in values if len(v) > KEYWORD_IGNORE_ABOVE]
    for start in range(0, len(long_values), TERMS_CHUNK):
        chunk = long_values[start : start + TERMS_CHUNK]
        lines: list = []
        for value in chunk:
            lines.append({"index": "misp-attributes"})
            lines.append(
                {
                    "size": max_attributes,
                    "track_total_hits": True,
                    "sort": NEWEST_FIRST,
                    "_source": ATTRIBUTE_FIELDS,
                    "query": {
                        "bool": {**base, "must": [{"match_phrase": {"value": value}}]}
                    },
                }
            )
        for value, response in zip(chunk, client.msearch(body=lines)["responses"]):
            # match_phrase is looser than equality; keep exact matches only.
            hits = [
                hit["_source"]
                for hit in response["hits"]["hits"]
                if hit["_source"].get("value") == value
            ]
            if hits:
                found[value] = {
                    "count": response["hits"]["total"]["value"],
                    "attributes": hits,
                }
    return found


def _events(event_uuids: set) -> dict[str, dict]:
    if not event_uuids:
        return {}
    response = get_opensearch_client().mget(
        index="misp-events",
        body={"ids": list(event_uuids)},
        _source_includes=[
            "uuid",
            "info",
            "threat_level",
            "published",
            "organisation",
            "tags",
        ],
    )
    return {d["_id"]: d["_source"] for d in response["docs"] if d.get("found")}


def _tag_names(tags) -> list[str]:
    return [t.get("name") for t in tags or [] if isinstance(t, dict) and t.get("name")]


def _context(attribute: dict, event: Optional[dict]) -> dict:
    event = event or {}
    return {
        "uuid": attribute.get("uuid"),
        "type": attribute.get("type"),
        "category": attribute.get("category"),
        "to_ids": bool(attribute.get("to_ids")),
        "comment": attribute.get("comment") or "",
        "timestamp": attribute.get("timestamp"),
        "first_seen": attribute.get("first_seen"),
        "last_seen": attribute.get("last_seen"),
        "tags": _tag_names(attribute.get("tags")),
        "warninglist_hits": list(attribute.get("warninglist_hits") or []),
        "event": {
            "uuid": attribute.get("event_uuid"),
            "info": event.get("info"),
            "threat_level_id": event.get("threat_level"),
            "published": event.get("published"),
            "org": (event.get("organisation") or {}).get("name"),
            "tags": _tag_names(event.get("tags")),
        },
    }


def lookup(
    values: list,
    to_ids_only: bool = True,
    max_attributes: int = DEFAULT_MAX_ATTRIBUTES,
    include_warninglisted: bool = False,
) -> dict:
    """Which of ``values`` are known indicators, with their context.

    With ``to_ids_only`` (the default) only IDS attributes count and the Redis
    prefilter applies; otherwise every live attribute counts and OpenSearch is
    asked about all values.
    """
    started = time.perf_counter()
    unique = list(
        dict.fromkeys(str(v) for v in values if v is not None and str(v) != "")
    )
    if len(unique) > MAX_VALUES_PER_REQUEST:
        raise TooManyValues(
            f"at most {MAX_VALUES_PER_REQUEST} values per request, got {len(unique)}"
        )
    if to_ids_only:
        candidates, source = _candidates(unique)
    else:
        candidates, source = unique, "opensearch"

    # Bounded per value and per response, whatever the request asks for.
    max_attributes = max(
        1,
        min(
            int(max_attributes),
            MAX_ATTRIBUTES,
            MAX_ATTRIBUTES_PER_RESPONSE // max(len(candidates), 1),
        ),
    )

    found = _find_attributes(
        candidates, to_ids_only, max_attributes, include_warninglisted
    )
    events = _events(
        {
            a.get("event_uuid")
            for e in found.values()
            for a in e["attributes"]
            if a.get("event_uuid")
        }
    )
    matches = [
        {
            "value": value,
            "attribute_count": found[value]["count"],
            "attributes": [
                _context(a, events.get(a.get("event_uuid")))
                for a in found[value]["attributes"]
            ],
        }
        for value in unique
        if value in found
    ]
    return {
        "checked": len(unique),
        "matched": len(matches),
        "candidates": len(candidates),
        "source": source,
        "took_ms": round((time.perf_counter() - started) * 1000, 1),
        "matches": matches,
    }
