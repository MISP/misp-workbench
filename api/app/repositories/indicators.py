"""Consolidated indicators: one record per ``(type, value)``.

MISP data is attributes: the same ``198.51.100.7`` can sit in dozens of events
from several sources, with different tags, ``to_ids`` flags and timestamps.
Security controls want one record per indicator, so this keeps a
``misp-indicators`` index with exactly that, merged from every live attribute
of the type and value:

- ``first_seen`` / ``last_seen`` across the attributes and the value's sightings,
  and ``last_reported`` across the attributes alone (when a source last
  reported it, for hit-rate expiry);
- the events it appears in, and per source (feed, MISP server, local) and
  creator organisation, in how many;
- the tags, with TLP reduced to the most restrictive one and galaxies unioned;
- sighting counters (positive, false-positive, expiration);
- the warninglists any of its attributes hit;
- the analysts' decision on it, if any (``review``, see indicator_reviews).

The unit of work is a *value*: refreshing one recomputes the indicators of
every type it has and tombstones those left without a live attribute.

Maintenance follows the ``/lookup`` cache: a sync every few seconds refreshes
the values of attributes written since its cursor (``updated_at`` is stamped
by the ingest pipeline on every write) and of new sightings, and an hourly
rebuild walks everything, catching what a sync can't see (event-level
changes, hard deletes by retention).

An indicator is only rewritten when its content changed (``checksum``), so
``updated_at`` means "changed", and incremental exports of this index carry
real changes only. Removed indicators stay as tombstones (``deleted: true``)
for ``TOMBSTONE_RETENTION_SECONDS``, so a delta can tell consumers about them.
"""

import hashlib
import json
import logging
import time
import uuid
from typing import Iterable, Iterator, Optional

from opensearchpy import helpers as opensearch_helpers

from app.repositories import stream_exports
from app.services import scoring
from app.services.opensearch import get_opensearch_client
from app.services.redis import get_redis_client

logger = logging.getLogger(__name__)

INDEX = "misp-indicators"
ATTRIBUTES_INDEX = "misp-attributes"

# Indicator uuids are derived from type and value, so the same indicator has
# the same uuid on every instance and across rebuilds.
NAMESPACE = uuid.UUID("5d0c7a2e-3c1b-4e0f-9a51-6b8e2f4d7c13")

# Attribute types that carry context, not something a control can match on.
NON_INDICATOR_TYPES = [
    "attachment",
    "boolean",
    "comment",
    "counter",
    "datetime",
    "float",
    "link",
    "other",
    "size-in-bytes",
    "text",
]

# Least to most restrictive; an indicator's ``tlp`` is the most restrictive
# TLP any of its attributes or events carries.
TLP_ORDER = {
    "tlp:clear": 0,
    "tlp:white": 0,
    "tlp:green": 1,
    "tlp:amber": 2,
    "tlp:amber+strict": 3,
    "tlp:red": 4,
}
GALAXY_PREFIX = "misp-galaxy:"

LOCK_KEY = "indicators:lock"
CURSOR_KEY = "indicators:cursor"
BUILT_AT_KEY = "indicators:built_at"
REBUILD_QUEUED_KEY = "indicators:rebuild_queued"
# Values whose sightings changed, refreshed by the next sync.
DIRTY_KEY = "indicators:dirty_values"
# Events whose own data (tags, organisation, source) changed: their values are
# refreshed by the next sync, rather than waiting for the hourly rebuild.
DIRTY_EVENTS_KEY = "indicators:dirty_events"

VALUES_PER_BATCH = 500
TERMS_CHUNK = 1000
LONG_VALUES_CHUNK = 100
# keyword sub-fields are mapped with ignore_above: 256.
KEYWORD_IGNORE_ABOVE = 256
# Event uuids listed on an indicator (newest first); event_count has them all.
MAX_EVENTS_LISTED = 50
# Event summaries cached during one sync or rebuild.
EVENT_CACHE_SIZE = 100_000
SYNC_OVERLAP_SECONDS = 30
LOCK_SECONDS = 2 * 3600
# How soon a requested rebuild tries again while a sync or rebuild runs.
REBUILD_RETRY_SECONDS = 30
TOMBSTONE_RETENTION_SECONDS = 30 * 86400

ATTRIBUTE_SOURCE = [
    "type",
    "value",
    "category",
    "to_ids",
    "timestamp",
    "first_seen",
    "last_seen",
    "event_uuid",
    "tags",
    "warninglist_hits",
    "validation_issues",
]


def indicator_uuid(type_: str, value: str) -> str:
    return str(uuid.uuid5(NAMESPACE, f"{type_}|{value}"))


def _chunks(items: list, size: int) -> Iterator[list]:
    for start in range(0, len(items), size):
        yield items[start : start + size]


def _as_int(value) -> Optional[int]:
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _tag_names(tags) -> list[str]:
    return [t.get("name") for t in tags or [] if isinstance(t, dict) and t.get("name")]


def merge_tags(names: Iterable[str]) -> tuple[list[str], Optional[str], list[str]]:
    """Every tag, the most restrictive TLP, and the galaxy tags.

    An indicator that is amber in one event and red in another has ``tlp``
    red. Its tags keep both, and every other tag, untruncated: outputs exclude
    by tag (``tlp:amber``, ``PAP:RED``, ...), and a tag dropped here would be
    a value sent where it must not go. A TLP tag in another case (``TLP:RED``)
    is also kept lowercased, so the usual ``tlp:red`` exclusion matches it.
    """
    names = set(names)
    tlps = [n for n in names if n.lower() in TLP_ORDER]
    tags = sorted(names | {n.lower() for n in tlps})
    tlp = max(tlps, key=lambda n: TLP_ORDER[n.lower()]).lower() if tlps else None
    galaxies = [n for n in tags if n.startswith(GALAXY_PREFIX)]
    return tags, tlp, galaxies


# ── Value queries ─────────────────────────────────────────────────────────


def value_clauses(values: Iterable[str]) -> Iterator[dict]:
    """Query clauses matching ``values``, in request-sized chunks.

    Values past the keyword's ignore_above aren't in ``value.keyword`` and
    are matched by phrase; callers keep exact matches only.
    """
    values = list(values)
    short = [v for v in values if len(v) <= KEYWORD_IGNORE_ABOVE]
    long_values = [v for v in values if len(v) > KEYWORD_IGNORE_ABOVE]
    for chunk in _chunks(short, TERMS_CHUNK):
        yield {"terms": {"value.keyword": chunk}}
    for chunk in _chunks(long_values, LONG_VALUES_CHUNK):
        yield {
            "bool": {
                "should": [{"match_phrase": {"value": v}} for v in chunk],
                "minimum_should_match": 1,
            }
        }


def _live_attributes(extra: Optional[list] = None) -> dict:
    return {
        "bool": {
            "filter": list(extra or []),
            "must_not": [
                {"term": {"deleted": True}},
                {"terms": {"type.keyword": NON_INDICATOR_TYPES}},
            ],
        }
    }


def _scan_attributes(client, values: set) -> Iterator[dict]:
    for clause in value_clauses(values):
        for hits in stream_exports.iter_pit_pages(
            client,
            ATTRIBUTES_INDEX,
            _live_attributes([clause]),
            source=ATTRIBUTE_SOURCE,
        ):
            for hit in hits:
                source = hit["_source"]
                if source.get("value") in values:
                    yield source


def _existing_indicators(client, values: set) -> dict[str, dict]:
    """Live indicators of ``values``, by id."""
    found = {}
    for clause in value_clauses(values):
        query = {
            "bool": {"filter": [clause], "must_not": [{"term": {"deleted": True}}]}
        }
        for hits in stream_exports.iter_pit_pages(
            client, INDEX, query, source=["value", "checksum", "score"]
        ):
            for hit in hits:
                if hit["_source"].get("value") in values:
                    found[hit["_id"]] = hit["_source"]
    return found


# ── Context: events, organisations, sightings ─────────────────────────────


def _organisation_names() -> dict[int, str]:
    from app.database import SessionLocal
    from app.models import organisation as organisation_models

    with SessionLocal() as db:
        return {
            org_id: name
            for org_id, name in db.query(
                organisation_models.Organisation.id,
                organisation_models.Organisation.name,
            )
        }


class _Events:
    """What an indicator needs from its events, fetched once per run."""

    FIELDS = ["deleted", "source", "organisation", "orgc_id", "org_id", "tags"]

    def __init__(self, client, organisations: dict[int, str]):
        self.client = client
        self.organisations = organisations
        self.cache: dict[str, dict] = {}

    def _summary(self, doc: dict) -> dict:
        source = doc.get("source") or {}
        if not source.get("type"):
            # Events from before sources were recorded: only locally created
            # ones carry their organisation.
            source = {"type": "local" if doc.get("organisation") else "unknown"}
        # The organisation is identified by id: names aren't unique, and a feed
        # creates an organisation under any name its data claims, so a name
        # can't be what source trust is keyed on.
        embedded = doc.get("organisation") or {}
        org_id = embedded.get("id") or doc.get("orgc_id") or doc.get("org_id")
        name = self.organisations.get(org_id) or embedded.get("name")
        org = {"id": org_id, "name": name} if name else None
        return {
            "deleted": bool(doc.get("deleted")),
            "source": {
                "type": source.get("type"),
                "id": source.get("id"),
                "name": source.get("name") or source.get("type"),
            },
            "org": org,
            "tags": _tag_names(doc.get("tags")),
        }

    def get(self, uuids: set) -> dict[str, dict]:
        missing = [u for u in uuids if u not in self.cache]
        if len(self.cache) + len(missing) > EVENT_CACHE_SIZE:
            self.cache.clear()
            missing = list(uuids)
        for chunk in _chunks(missing, TERMS_CHUNK):
            response = self.client.mget(
                index="misp-events", body={"ids": chunk}, _source_includes=self.FIELDS
            )
            for doc in response["docs"]:
                if doc.get("found"):
                    self.cache[doc["_id"]] = self._summary(doc["_source"])
        return {u: self.cache[u] for u in uuids if u in self.cache}


def _sightings(client, values: set) -> dict[str, dict]:
    """Sighting counters per value.

    Sightings are recorded per value (they apply to every type sharing it).
    Values past the keyword's ignore_above can't be aggregated on and get none.
    """
    counters: dict[str, dict] = {}
    short = [v for v in values if len(v) <= KEYWORD_IGNORE_ABOVE]
    for chunk in _chunks(short, TERMS_CHUNK):
        response = client.search(
            index="misp-sightings",
            body={
                "size": 0,
                "query": {"terms": {"value.keyword": chunk}},
                "aggs": {
                    "values": {
                        "terms": {"field": "value.keyword", "size": len(chunk)},
                        "aggs": {
                            "types": {
                                "terms": {"field": "type", "size": 10},
                                "aggs": {"last": {"max": {"field": "@timestamp"}}},
                            },
                            "first": {"min": {"field": "@timestamp"}},
                            "last": {"max": {"field": "@timestamp"}},
                        },
                    }
                },
            },
            ignore=[400, 404],
        )
        for bucket in (
            (response.get("aggregations") or {}).get("values", {}).get("buckets", [])
        ):
            types = {b["key"]: b for b in bucket["types"]["buckets"]}

            def count(type_):
                return types[type_]["doc_count"] if type_ in types else 0

            def last(type_):
                if type_ not in types:
                    return None
                return _millis_to_seconds(types[type_]["last"].get("value"))

            counters[bucket["key"]] = {
                "positive": count("positive"),
                "false_positive": count("false-positive"),
                "expiration": count("expiration"),
                "first_at": _millis_to_seconds(bucket["first"].get("value")),
                "last_at": _millis_to_seconds(bucket["last"].get("value")),
                # An expiration only counts when no positive sighting followed.
                "last_positive_at": last("positive"),
                "last_expiration_at": last("expiration"),
                # For a source's recent false-positive rate (source quality).
                "last_false_positive_at": last("false-positive"),
            }
    return counters


def _millis_to_seconds(value) -> Optional[int]:
    return int(value // 1000) if value is not None else None


# ── Building ──────────────────────────────────────────────────────────────


VALIDATION_TAG = 'workbench:validation="{}"'


def validation_tag(issue: str) -> str:
    """The tag a validation issue shows as, e.g. workbench:validation="private-ip"."""
    return VALIDATION_TAG.format(issue)


def source_key(source: dict) -> str:
    """``feed:3``, ``server:2``, ``local`` or ``unknown``: one source, exactly."""
    if source.get("type") in ("feed", "server") and source.get("id") is not None:
        return f"{source['type']}:{source['id']}"
    return str(source.get("type") or "unknown")


def _counted(counts: dict, key, entry: dict) -> None:
    if key not in counts:
        counts[key] = {**entry, "event_count": 0}
    counts[key]["event_count"] += 1


def build_indicator(
    type_: str,
    value: str,
    attributes: list[dict],
    events: dict[str, dict],
    sightings: Optional[dict] = None,
    scoring_config: Optional[dict] = None,
    now: Optional[int] = None,
    review: Optional[dict] = None,
) -> Optional[dict]:
    """The consolidated record of one type and value, or None if it has no
    live attribute (all in deleted events).

    Carries its confidence score (see ``app.services.scoring``), which is
    left out of ``checksum``: a score moves with time alone.
    """
    live = [
        a
        for a in attributes
        if not (events.get(a.get("event_uuid")) or {}).get("deleted")
    ]
    if not live:
        return None
    live.sort(key=lambda a: _as_int(a.get("timestamp")) or 0, reverse=True)

    event_uuids: list[str] = []
    for attribute in live:
        event_uuid = attribute.get("event_uuid")
        if event_uuid and event_uuid not in event_uuids:
            event_uuids.append(event_uuid)

    sources: dict = {}
    organisations: dict = {}
    tag_names: set = set()
    for event_uuid in event_uuids:
        event = events.get(event_uuid)
        if event is None:
            continue
        source = event["source"]
        _counted(sources, (source["type"], source["id"], source["name"]), source)
        org = event["org"]
        if org:
            _counted(organisations, (org["id"], org["name"]), dict(org))
        tag_names.update(event["tags"])
    validation_issues = sorted(
        {issue for a in live for issue in a.get("validation_issues") or []}
    )
    for attribute in live:
        tag_names.update(_tag_names(attribute.get("tags")))
    # As tags too, so tag filters (sinks, exports) can leave them out.
    tag_names.update(validation_tag(issue) for issue in validation_issues)
    tags, tlp, galaxies = merge_tags(tag_names)

    sightings = sightings or {}
    starts = [_as_int(a.get("first_seen") or a.get("timestamp")) for a in live]
    ends = [_as_int(a.get("last_seen") or a.get("timestamp")) for a in live]
    reported = [t for t in ends if t]
    starts.append(sightings.get("first_at"))
    ends.append(sightings.get("last_at"))
    starts = [t for t in starts if t]
    ends = [t for t in ends if t]

    ids_count = sum(1 for a in live if a.get("to_ids"))
    doc = {
        "uuid": indicator_uuid(type_, value),
        "type": type_,
        "value": value,
        "categories": sorted({a["category"] for a in live if a.get("category")}),
        "to_ids": ids_count > 0,
        "deleted": False,
        "attribute_count": len(live),
        "ids_attribute_count": ids_count,
        "event_count": len(event_uuids),
        "events": event_uuids[:MAX_EVENTS_LISTED],
        "first_seen": min(starts) if starts else None,
        "last_seen": max(ends) if ends else None,
        "last_reported": max(reported) if reported else None,
        "sources": sorted(
            sources.values(), key=lambda s: (-s["event_count"], str(s["name"]))
        ),
        "organisations": sorted(
            organisations.values(), key=lambda o: (-o["event_count"], o["name"])
        ),
        # Flat keys, so queries and per-source statistics can match one
        # source exactly (sources is an array of objects, flattened when
        # indexed: sources.type:feed AND sources.id:2 could pair the type of
        # one with the id of another).
        "source_keys": sorted({source_key(s) for s in sources.values()}),
        "source_count": len(sources),
        "organisation_ids": sorted(
            {o["id"] for o in organisations.values() if o.get("id") is not None}
        ),
        "organisation_count": len(organisations),
        "tags": tags,
        "tlp": tlp,
        "galaxies": galaxies,
        "sightings": {
            "positive": sightings.get("positive", 0),
            "false_positive": sightings.get("false_positive", 0),
            "expiration": sightings.get("expiration", 0),
            "first_at": sightings.get("first_at"),
            "last_at": sightings.get("last_at"),
            "last_positive_at": sightings.get("last_positive_at"),
            "last_expiration_at": sightings.get("last_expiration_at"),
            "last_false_positive_at": sightings.get("last_false_positive_at"),
        },
        "warninglist_hits": sorted(
            {hit for a in live for hit in a.get("warninglist_hits") or []}
        ),
        "validation_issues": validation_issues,
    }
    if review:
        doc["review"] = review
    doc["checksum"] = hashlib.sha256(
        json.dumps(doc, sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()
    now = int(time.time()) if now is None else now
    doc["score"], doc["score_breakdown"] = scoring.score(
        doc, scoring_config or scoring.config(), now
    )
    doc["scored_at"] = now
    return doc


class _Run:
    """State shared by the batches of one sync or rebuild."""

    def __init__(self, exact_scores: bool = False):
        self.client = get_opensearch_client()
        self.events = _Events(self.client, _organisation_names())
        self.scoring = scoring.load_config()
        # A requested rebuild (a source's trust or the scoring settings
        # changed) writes every score that moved, however little: otherwise a
        # modifier of -3 would be computed and never stored.
        self.exact_scores = exact_scores
        self.written = 0
        self.removed = 0

    def score_changed(self, stored: Optional[int], new: Optional[int]) -> bool:
        if self.exact_scores:
            return stored != new
        return scoring.needs_rewrite(stored, new, self.scoring)


def refresh_values(values: Iterable[str], run: Optional[_Run] = None) -> dict:
    """Recompute the indicators of ``values``, every type of each.

    Writes those whose content changed and tombstones those left without a
    live attribute. Returns how many were written and removed.
    """
    run = run or _Run()
    values = {str(v) for v in values if v not in (None, "")}
    for chunk in _chunks(sorted(values), VALUES_PER_BATCH):
        _refresh_batch(run, set(chunk))
    return {"written": run.written, "removed": run.removed}


def _refresh_batch(run: _Run, values: set) -> None:
    client = run.client
    groups: dict[tuple, list] = {}
    for attribute in _scan_attributes(client, values):
        groups.setdefault((attribute.get("type"), attribute["value"]), []).append(
            attribute
        )
    events = run.events.get(
        {
            a["event_uuid"]
            for group in groups.values()
            for a in group
            if a.get("event_uuid")
        }
    )
    sightings = _sightings(client, values)
    reviews = _reviews(
        [indicator_uuid(type_, value) for type_, value in groups if type_]
    )
    now = int(time.time())

    docs = {}
    for (type_, value), attributes in groups.items():
        if not type_:
            continue
        doc = build_indicator(
            type_,
            value,
            attributes,
            events,
            sightings.get(value),
            run.scoring,
            now,
            reviews.get(indicator_uuid(type_, value)),
        )
        if doc is not None:
            docs[doc["uuid"]] = doc

    existing = _existing_indicators(client, values)
    actions = []
    for doc_id, doc in docs.items():
        stored = existing.get(doc_id, {})
        if stored.get("checksum") == doc["checksum"] and not run.score_changed(
            stored.get("score"), doc["score"]
        ):
            continue
        actions.append(
            {
                "_op_type": "index",
                "_index": INDEX,
                "_id": doc_id,
                "_source": {**doc, "updated_at": now},
            }
        )
    removed = [doc_id for doc_id in existing if doc_id not in docs]
    for doc_id in removed:
        actions.append(
            {
                "_op_type": "update",
                "_index": INDEX,
                "_id": doc_id,
                "doc": {"deleted": True, "checksum": None, "updated_at": now},
            }
        )
    if actions:
        opensearch_helpers.bulk(client, actions)
    run.written += len(actions) - len(removed)
    run.removed += len(removed)


def _reviews(ids: list[str]) -> dict[str, dict]:
    from app.repositories import indicator_reviews

    return indicator_reviews.reviews_for(ids)


# ── Maintenance ───────────────────────────────────────────────────────────


def _changed_values(client, since: int) -> Iterator[list[str]]:
    """Values of attributes written at or after ``since``, deleted ones too."""
    query = {
        "bool": {
            "filter": [
                {"range": {"updated_at": {"gte": since, "format": "epoch_second"}}}
            ],
            "must_not": [{"terms": {"type.keyword": NON_INDICATOR_TYPES}}],
        }
    }
    batch: set = set()
    for hits in stream_exports.iter_pit_pages(
        client, ATTRIBUTES_INDEX, query, source=["value"]
    ):
        for hit in hits:
            value = hit["_source"].get("value")
            if value not in (None, ""):
                batch.add(str(value))
        if len(batch) >= VALUES_PER_BATCH:
            yield sorted(batch)
            batch = set()
    if batch:
        yield sorted(batch)


def _all_values(client) -> Iterator[list[str]]:
    """Every value that has a live attribute, in batches."""
    after = None
    while True:
        composite = {
            "size": VALUES_PER_BATCH,
            "sources": [{"value": {"terms": {"field": "value.keyword"}}}],
        }
        if after:
            composite["after"] = after
        response = client.search(
            index=ATTRIBUTES_INDEX,
            body={
                "size": 0,
                "query": _live_attributes(),
                "aggs": {"values": {"composite": composite}},
            },
        )
        agg = response["aggregations"]["values"]
        values = [b["key"]["value"] for b in agg["buckets"]]
        if values:
            yield values
        after = agg.get("after_key")
        if not after or len(values) < VALUES_PER_BATCH:
            break

    # Values past the keyword's ignore_above aren't aggregated; few enough to
    # collect from a scan.
    long_values: set = set()
    query = _live_attributes()
    query["bool"]["must_not"].append({"exists": {"field": "value.keyword"}})
    for hits in stream_exports.iter_pit_pages(
        client, ATTRIBUTES_INDEX, query, source=["value"]
    ):
        long_values.update(
            h["_source"]["value"] for h in hits if h["_source"].get("value")
        )
    yield from _chunks(sorted(long_values), VALUES_PER_BATCH)


def _values_with_live_attributes(client, values: list[str]) -> set:
    short = [v for v in values if len(v) <= KEYWORD_IGNORE_ABOVE]
    if not short:
        return set()
    response = client.search(
        index=ATTRIBUTES_INDEX,
        body={
            "size": 0,
            "query": _live_attributes([{"terms": {"value.keyword": short}}]),
            "aggs": {
                "values": {"terms": {"field": "value.keyword", "size": len(short)}}
            },
        },
    )
    return {b["key"] for b in response["aggregations"]["values"]["buckets"]}


def _orphaned_values(client) -> Iterator[list[str]]:
    """Values of live indicators that have no live attribute left.

    Hard deletes (retention, force-deleting an event) leave no trace a sync
    could follow; this is how their indicators get tombstoned. Long values
    are always re-checked, which costs a refresh each.
    """
    query = {"bool": {"must_not": [{"term": {"deleted": True}}]}}
    for hits in stream_exports.iter_pit_pages(client, INDEX, query, source=["value"]):
        values = sorted(
            {h["_source"]["value"] for h in hits if h["_source"].get("value")}
        )
        gone = set(values) - _values_with_live_attributes(client, values)
        if gone:
            yield sorted(gone)


def _lock(redis, wait_seconds: int) -> bool:
    deadline = time.monotonic() + wait_seconds
    while True:
        if redis.set(LOCK_KEY, "1", nx=True, ex=LOCK_SECONDS):
            return True
        if time.monotonic() >= deadline:
            return False
        time.sleep(1)


def rebuild(wait_seconds: int = 0, requested: bool = False) -> Optional[dict]:
    """Recompute every indicator and tombstone the orphaned ones.

    Unchanged indicators aren't rewritten, so a rebuild over a quiet index
    writes nothing. ``requested``: something changed that every score depends
    on (see request_rebuild), so every score that moved is written, not only
    moves of ``refresh_step`` or more. Returns counts, or None when a sync or
    rebuild holds the lock for longer than ``wait_seconds``.
    """
    redis = get_redis_client()
    if not _lock(redis, wait_seconds):
        return None
    if requested:
        # This run reads the settings and every source's trust now: a request
        # from here on needs a run of its own, so it may queue one.
        redis.delete(REBUILD_QUEUED_KEY)
    try:
        started = int(time.time())
        run = _Run(exact_scores=requested)
        client = run.client
        for values in _all_values(client):
            refresh_values(values, run)
        for values in _orphaned_values(client):
            refresh_values(values, run)
        purged = client.delete_by_query(
            index=INDEX,
            body={
                "query": {
                    "bool": {
                        "filter": [
                            {"term": {"deleted": True}},
                            {
                                "range": {
                                    "updated_at": {
                                        "lt": started - TOMBSTONE_RETENTION_SECONDS
                                    }
                                }
                            },
                        ]
                    }
                }
            },
            conflicts="proceed",
        ).get("deleted", 0)
        # Everything written since the walk began is read again by the next sync.
        redis.set(BUILT_AT_KEY, started)
        redis.set(CURSOR_KEY, started)
        result = {"written": run.written, "removed": run.removed, "purged": purged}
        logger.info("indicators rebuilt: %s", result)
        return result
    finally:
        redis.delete(LOCK_KEY)


def sync() -> Optional[dict]:
    """Refresh the values written or sighted since the last sync.

    None when nothing has been built yet (a rebuild is queued) or a sync or
    rebuild is running.
    """
    redis = get_redis_client()
    if not redis.exists(BUILT_AT_KEY):
        request_rebuild()
        return None
    if not _lock(redis, 0):
        return None
    try:
        started = int(time.time())
        cursor = int(redis.get(CURSOR_KEY) or started) - SYNC_OVERLAP_SECONDS
        run = _Run()
        for values in _changed_values(run.client, cursor):
            refresh_values(values, run)
        while True:
            # Popped values are gone from the set even if the refresh fails;
            # the hourly rebuild catches those.
            sighted = redis.spop(DIRTY_KEY, VALUES_PER_BATCH)
            if not sighted:
                break
            refresh_values(sighted, run)
        while True:
            events = redis.spop(DIRTY_EVENTS_KEY, TERMS_CHUNK)
            if not events:
                break
            for values in _event_values(run.client, events):
                refresh_values(values, run)
        redis.set(CURSOR_KEY, started)
        result = {"written": run.written, "removed": run.removed}
        if run.written or run.removed:
            logger.info("indicators sync: %s", result)
        return result
    finally:
        redis.delete(LOCK_KEY)


def _event_values(client, event_uuids: list[str]) -> Iterator[list[str]]:
    """Values of the attributes of ``event_uuids``, in batches."""
    query = {"bool": {"filter": [{"terms": {"event_uuid": list(event_uuids)}}]}}
    batch: set = set()
    for hits in stream_exports.iter_pit_pages(
        client, ATTRIBUTES_INDEX, query, source=["value"]
    ):
        batch.update(
            str(h["_source"]["value"])
            for h in hits
            if h["_source"].get("value") not in (None, "")
        )
        if len(batch) >= VALUES_PER_BATCH:
            yield sorted(batch)
            batch = set()
    if batch:
        yield sorted(batch)


def request_rebuild() -> None:
    """Queue a rebuild for a change every score depends on: a source's trust,
    the scoring settings. Requests are merged until the queued rebuild starts,
    since it reads the latest of everything then; one arriving while it runs
    queues the next, rather than being lost to a run that read too early."""
    from app.worker import tasks

    redis = get_redis_client()
    if redis.set(REBUILD_QUEUED_KEY, "1", nx=True, ex=LOCK_SECONDS):
        tasks.rebuild_indicators.apply_async(kwargs={"requested": True})


def mark_sighted(values: Iterable[str]) -> None:
    """Queue values whose sightings (or review decisions) changed for the
    next sync. Best-effort."""
    values = [str(v) for v in values if v not in (None, "")]
    if not values:
        return
    try:
        redis = get_redis_client()
        for chunk in _chunks(values, TERMS_CHUNK):
            redis.sadd(DIRTY_KEY, *chunk)
    except Exception:
        logger.exception("could not queue sighted values for the indicators sync")


def mark_event_changed(event_uuid) -> None:
    """Queue an event whose tags, organisation or source changed. Best-effort.

    Its indicators carry its tags (a tlp:red on the event makes them red) and
    count its source and organisation, so they are refreshed at the next sync.
    """
    if not event_uuid:
        return
    try:
        get_redis_client().sadd(DIRTY_EVENTS_KEY, str(event_uuid))
    except Exception:
        logger.exception("could not queue a changed event for the indicators sync")


def status() -> dict:
    redis = get_redis_client()
    client = get_opensearch_client()
    built_at = redis.get(BUILT_AT_KEY)

    def count(deleted: bool) -> int:
        response = client.count(
            index=INDEX, body={"query": {"term": {"deleted": deleted}}}, ignore=[404]
        )
        return response.get("count", 0)

    return {
        "built": built_at is not None,
        "built_at": int(built_at) if built_at else None,
        "synced_at": int(redis.get(CURSOR_KEY) or 0) or None,
        "indicators": count(False),
        "tombstones": count(True),
        "pending_sighted_values": redis.scard(DIRTY_KEY),
        "pending_events": redis.scard(DIRTY_EVENTS_KEY),
    }


# ── Reading ───────────────────────────────────────────────────────────────

# Not part of what an API client gets back.
INTERNAL_FIELDS = ("checksum",)
MAX_RESULT_WINDOW = 10_000


def _public(source: dict) -> dict:
    return {k: v for k, v in source.items() if k not in INTERNAL_FIELDS}


def get_indicator(indicator_id: str) -> Optional[dict]:
    response = get_opensearch_client().get(index=INDEX, id=indicator_id, ignore=[404])
    return _public(response["_source"]) if response.get("found") else None


def get_indicators(ids: Iterable[str]) -> dict[str, dict]:
    ids = list(dict.fromkeys(ids))
    found: dict[str, dict] = {}
    client = get_opensearch_client()
    for chunk in _chunks(ids, TERMS_CHUNK):
        response = client.mget(index=INDEX, body={"ids": chunk})
        for doc in response["docs"]:
            if doc.get("found") and not doc["_source"].get("deleted"):
                found[doc["_id"]] = _public(doc["_source"])
    return found


MAX_SCORE_KEYS = 1000


def scores_for(keys: list[tuple[str, str]]) -> list[Optional[dict]]:
    """Score and breakdown of the indicator of each ``(type, value)``, in order.

    None where there is no live indicator (a context type, or one not built
    yet).
    """
    ids = [indicator_uuid(t, v) for t, v in keys]
    found = get_indicators(ids)
    return [
        (
            {
                "uuid": i,
                "score": found[i].get("score"),
                "score_breakdown": found[i].get("score_breakdown") or [],
                "scored_at": found[i].get("scored_at"),
            }
            if i in found
            else None
        )
        for i in ids
    ]


SORTS = {
    "score": [{"score": {"order": "desc", "missing": "_last"}}],
    "last_seen": [{"last_seen": {"order": "desc", "missing": "_last"}}],
    "first_seen": [{"first_seen": {"order": "desc", "missing": "_last"}}],
    "event_count": [{"event_count": {"order": "desc"}}],
    "updated_at": [{"updated_at": {"order": "desc"}}],
}


def search(
    query: Optional[str] = None,
    type_: Optional[str] = None,
    to_ids: Optional[bool] = None,
    include_deleted: bool = False,
    sort: str = "last_seen",
    page: int = 1,
    size: int = 50,
    min_score: Optional[int] = None,
    profile: Optional[dict] = None,
) -> dict:
    filters: list = []
    if profile is not None:
        from app.repositories import detection_profiles

        filters.append(
            detection_profiles.to_query(
                profile["rules"], detection_profiles.context(), live_only=False
            )
        )
    if min_score:
        filters.append({"range": {"score": {"gte": min_score}}})
    if type_:
        filters.append({"term": {"type.keyword": type_}})
    if to_ids is not None:
        filters.append({"term": {"to_ids": to_ids}})
    if not include_deleted:
        filters.append({"term": {"deleted": False}})
    must = (
        [{"query_string": {"query": query, "default_field": "value"}}] if query else []
    )
    size = max(1, min(size, 1000))
    start = (max(page, 1) - 1) * size
    if start + size > MAX_RESULT_WINDOW:
        raise ValueError(
            f"results past the first {MAX_RESULT_WINDOW} can't be paged to; "
            "narrow the query or use /indicators/export"
        )
    response = get_opensearch_client().search(
        index=INDEX,
        body={
            "query": {"bool": {"must": must, "filter": filters}},
            "sort": SORTS.get(sort, SORTS["last_seen"]) + [{"uuid.keyword": "asc"}],
            "from": start,
            "size": size,
            "track_total_hits": True,
            "_source": {"excludes": list(INTERNAL_FIELDS)},
        },
    )
    return {
        "total": response["hits"]["total"]["value"],
        "page": max(page, 1),
        "size": size,
        "items": [hit["_source"] for hit in response["hits"]["hits"]],
    }


def find_by_values(
    values: list[str], to_ids_only: bool = True, include_warninglisted: bool = False
) -> dict[str, list[dict]]:
    """Live indicators of ``values``, grouped by value (one per type)."""
    found: dict[str, list[dict]] = {}
    wanted = set(values)
    client = get_opensearch_client()
    must_not: list = [{"term": {"deleted": True}}]
    if not include_warninglisted:
        from app.repositories.warninglists import WARNINGLISTED

        must_not.append(WARNINGLISTED)
    for clause in value_clauses(values):
        filters = [clause]
        if to_ids_only:
            filters.append({"term": {"to_ids": True}})
        response = client.search(
            index=INDEX,
            body={
                "query": {"bool": {"filter": filters, "must_not": must_not}},
                # A value has one indicator per type: a handful at most.
                "size": MAX_RESULT_WINDOW,
                "_source": {"excludes": list(INTERNAL_FIELDS)},
            },
        )
        for hit in response["hits"]["hits"]:
            source = hit["_source"]
            if source.get("value") in wanted:
                found.setdefault(source["value"], []).append(source)
    return found
