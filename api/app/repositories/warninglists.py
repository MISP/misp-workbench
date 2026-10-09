"""MISP warninglists: loading, matching, and flagging attributes.

Warninglists name values that are benign or too common to act on (public
resolvers, top domains, cloud and CDN ranges, private networks, …). Rather
than checking them on every export or lookup, each attribute carries the
names of the enabled lists it hits in ``warninglist_hits``; every output can
then leave flagged attributes out with a cheap ``must_not exists`` filter.

Entries are kept out of process memory: the large lists hold a million values
each, about 6.4 million in total. ``string``, ``hostname`` and ``cidr``
entries live in the ``misp-warninglist-entries`` OpenSearch index and a batch
of attributes is matched with one query; the handful of ``substring`` and
``regex`` lists are small and matched in memory.

``warninglist_hits`` is kept current by a full re-evaluation whenever the
lists change, and by a sync of attributes written since the last one (keyed on
``updated_at``, which the ingest pipeline stamps on every write path).
"""

import ipaddress
import json
import logging
import os
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Iterable, Iterator, Optional
from urllib.parse import urlsplit

from opensearchpy import helpers as opensearch_helpers
from sqlalchemy.orm import Session

from app.models import warninglist as warninglist_models
from app.repositories import stream_exports
from app.services.opensearch import get_opensearch_client
from app.services.redis import get_redis_client

logger = logging.getLogger(__name__)

WARNINGLISTS_DIR = "app/submodules/misp-warninglists/lists"
ENTRIES_INDEX = "misp-warninglist-entries"
ATTRIBUTES_INDEX = "misp-attributes"

INDEXED_TYPES = ("string", "hostname", "cidr")
PATTERN_TYPES = ("substring", "regex")

BATCH_SIZE = 1000
BULK_CHUNK = 5000
# Single search size for entry hits; past it, a point-in-time scan.
MAX_HITS_PER_SEARCH = 10_000

CURSOR_KEY = "warninglists:eval:cursor"
LOCK_KEY = "warninglists:eval:lock"
# Set when a full evaluation is requested while one is running: the running
# one goes again with the lists as they are now, so no change is lost.
DIRTY_KEY = "warninglists:eval:dirty"
LOCK_SECONDS = 2 * 60 * 60
SYNC_OVERLAP_SECONDS = 30


# ── Loading ───────────────────────────────────────────────────────────────


def _index_value(list_type: str, entry: str) -> Optional[dict]:
    entry = str(entry).strip()
    if not entry:
        return None
    if list_type == "cidr":
        try:
            # ip_range takes CIDR notation; a bare address is its own /32 or /128.
            network = ipaddress.ip_network(entry, strict=False)
        except ValueError:
            return None
        mapped = network.version == 6 and network.network_address.ipv4_mapped
        if mapped:
            # OpenSearch rejects CIDR notation on IPv4-mapped IPv6 (::ffff:a.b.c.d)
            # and stores those addresses as IPv4 anyway: index the IPv4 range.
            network = ipaddress.ip_network(f"{mapped}/{max(network.prefixlen - 96, 0)}")
        return {"range": str(network)}
    if list_type == "hostname":
        return {"value": entry.strip(".").lower()}
    return {"value": entry}


def _index_entries(client, warninglist_id: int, list_type: str, entries: list) -> int:
    client.delete_by_query(
        index=ENTRIES_INDEX,
        body={"query": {"term": {"warninglist_id": warninglist_id}}},
        conflicts="proceed",
        refresh=True,
    )

    def actions():
        for entry in entries:
            doc = _index_value(list_type, entry)
            if doc is not None:
                yield {
                    "_index": ENTRIES_INDEX,
                    "_source": {
                        "warninglist_id": warninglist_id,
                        "type": list_type,
                        **doc,
                    },
                }

    # One entry OpenSearch won't take must not abort loading the other lists.
    indexed, errors = opensearch_helpers.bulk(
        client,
        actions(),
        chunk_size=BULK_CHUNK,
        request_timeout=120,
        raise_on_error=False,
    )
    if errors:
        logger.warning(
            "warninglist %s: %s entries rejected, e.g. %s",
            warninglist_id,
            len(errors),
            errors[0],
        )
    return indexed


def update_warninglists(db: Session, lists_dir: str = WARNINGLISTS_DIR) -> dict:
    """Load or refresh the lists shipped in the misp-warninglists submodule.

    Only lists whose version changed are re-indexed. New lists start enabled,
    as in MISP. Returns counts, and whether anything changed (in which case
    attributes need re-evaluating).
    """
    client = get_opensearch_client()
    counts = {"created": 0, "updated": 0, "unchanged": 0, "skipped": 0}
    existing = {w.name: w for w in db.query(warninglist_models.Warninglist).all()}

    for entry in sorted(os.listdir(lists_dir)):
        path = os.path.join(lists_dir, entry, "list.json")
        if not os.path.exists(path):
            continue
        with open(path) as f:
            raw = json.load(f)
        list_type = raw.get("type")
        if list_type not in INDEXED_TYPES + PATTERN_TYPES:
            counts["skipped"] += 1
            continue

        db_list = existing.get(raw["name"])
        if db_list is not None and db_list.version == raw.get("version"):
            counts["unchanged"] += 1
            continue
        if db_list is None:
            db_list = warninglist_models.Warninglist(name=raw["name"], enabled=True)
            db.add(db_list)
            counts["created"] += 1
        else:
            counts["updated"] += 1

        entries = [str(v) for v in raw.get("list") or []]
        db_list.description = raw.get("description")
        db_list.type = list_type
        db_list.category = raw.get("category")
        db_list.version = raw.get("version") or 0
        db_list.matching_attributes = list(raw.get("matching_attributes") or [])
        db_list.updated_at = datetime.now(timezone.utc)
        db.flush()

        if list_type in PATTERN_TYPES:
            db_list.patterns = entries
            db_list.entry_count = len(entries)
        else:
            db_list.patterns = None
            db_list.entry_count = _index_entries(client, db_list.id, list_type, entries)
        db.commit()
        logger.info(
            "warninglist %r loaded: %s entries", db_list.name, db_list.entry_count
        )

    # Entries of no list: left by a load that failed before committing its row.
    known = [w.id for w in db.query(warninglist_models.Warninglist.id).all()]
    client.delete_by_query(
        index=ENTRIES_INDEX,
        body={"query": {"bool": {"must_not": [{"terms": {"warninglist_id": known}}]}}},
        conflicts="proceed",
        refresh=True,
    )
    counts["changed"] = bool(counts["created"] or counts["updated"])
    return counts


def get_warninglists(db: Session) -> list:
    return (
        db.query(warninglist_models.Warninglist)
        .order_by(warninglist_models.Warninglist.name.asc())
        .all()
    )


def get_warninglist(db: Session, warninglist_id: int):
    return (
        db.query(warninglist_models.Warninglist)
        .filter(warninglist_models.Warninglist.id == warninglist_id)
        .first()
    )


def set_enabled(db: Session, db_list, enabled: bool):
    db_list.enabled = enabled
    db.commit()
    db.refresh(db_list)
    return db_list


# ── Matching ──────────────────────────────────────────────────────────────


def _compile_regex(pattern: str) -> Optional[re.Pattern]:
    """MISP stores PHP-style ``/body/flags`` regexes; plain ones work too."""
    flags = 0
    body = pattern
    match = re.fullmatch(r"/(.*)/([a-z]*)", pattern, flags=re.S)
    if match:
        body, modifiers = match.groups()
        if "i" in modifiers:
            flags |= re.I
    try:
        return re.compile(body, flags)
    except re.error:
        logger.warning("warninglist regex %r doesn't compile; ignored", pattern)
        return None


@dataclass
class _List:
    id: int
    name: str
    type: str
    matching: frozenset
    patterns: list = field(default_factory=list)

    def applies_to(self, attribute_type: Optional[str]) -> bool:
        return (
            attribute_type is None
            or not self.matching
            or attribute_type in self.matching
        )


def _parts(attribute_type: Optional[str], value: str) -> list[str]:
    if attribute_type and "|" in attribute_type and "|" in value:
        return [p for p in value.split("|") if p]
    return [value]


def _host_of(value: str) -> Optional[str]:
    try:
        host = urlsplit(value if "://" in value else f"http://{value}").hostname
    except ValueError:
        return None
    return host.strip(".").lower() if host else None


def _ip_of(value: str) -> Optional[str]:
    try:
        return str(ipaddress.ip_address(value))
    except ValueError:
        pass
    try:
        return str(ipaddress.ip_network(value, strict=False).network_address)
    except ValueError:
        return None


def _suffixes(host: str) -> list[str]:
    labels = host.split(".")
    return [".".join(labels[i:]) for i in range(len(labels))]


@dataclass
class _Candidates:
    strings: set
    hosts: set
    ips: set


def _candidates(attribute_type: Optional[str], value: str) -> _Candidates:
    strings: set = {value, value.lower()}
    hosts: set = set()
    ips: set = set()
    for part in _parts(attribute_type, value):
        strings.update({part, part.lower()})
        ip = _ip_of(part)
        if ip:
            ips.add(ip)
            continue
        host = _host_of(part)
        if host and "." in host:
            hosts.update(_suffixes(host))
    return _Candidates(strings, hosts, ips)


class Matcher:
    """The enabled lists, ready to match batches of (type, value)."""

    def __init__(self, db: Session):
        lists = (
            db.query(warninglist_models.Warninglist)
            .filter(warninglist_models.Warninglist.enabled.is_(True))
            .all()
        )
        self.indexed = {
            w.id: _List(w.id, w.name, w.type, frozenset(w.matching_attributes or []))
            for w in lists
            if w.type in INDEXED_TYPES
        }
        self.patterns = []
        for w in lists:
            if w.type == "substring":
                self.patterns.append(
                    _List(
                        w.id,
                        w.name,
                        w.type,
                        frozenset(w.matching_attributes or []),
                        [p.lower() for p in w.patterns or [] if p],
                    )
                )
            elif w.type == "regex":
                compiled = [c for c in map(_compile_regex, w.patterns or []) if c]
                self.patterns.append(
                    _List(
                        w.id,
                        w.name,
                        w.type,
                        frozenset(w.matching_attributes or []),
                        compiled,
                    )
                )
        self.client = get_opensearch_client()

    @property
    def empty(self) -> bool:
        return not self.indexed and not self.patterns

    def _entry_hits(self, strings: set, hosts: set) -> set:
        """(list id, value) pairs among string/hostname entries."""
        keys = sorted(strings | hosts)
        if not keys or not self.indexed:
            return set()
        query = {
            "bool": {
                "filter": [
                    {"terms": {"warninglist_id": sorted(self.indexed)}},
                    {"terms": {"type": ["string", "hostname"]}},
                    {"terms": {"value": keys}},
                ]
            }
        }
        response = self.client.search(
            index=ENTRIES_INDEX,
            body={
                "query": query,
                "_source": ["warninglist_id", "value"],
                "size": MAX_HITS_PER_SEARCH,
                "track_total_hits": True,
            },
        )
        pages: Iterable = [response["hits"]["hits"]]
        if response["hits"]["total"]["value"] > MAX_HITS_PER_SEARCH:
            pages = stream_exports.iter_pit_pages(
                self.client, ENTRIES_INDEX, query, source=["warninglist_id", "value"]
            )
        return {
            (hit["_source"]["warninglist_id"], hit["_source"]["value"])
            for page in pages
            for hit in page
        }

    def _cidr_hits(self, ips: set) -> dict[str, set]:
        """Per address, the ids of the enabled CIDR lists containing it."""
        cidr_ids = sorted(i for i, w in self.indexed.items() if w.type == "cidr")
        found: dict[str, set] = {}
        ordered = sorted(ips)
        if not ordered or not cidr_ids:
            return found
        for start in range(0, len(ordered), BATCH_SIZE):
            chunk = ordered[start : start + BATCH_SIZE]
            lines: list = []
            for ip in chunk:
                lines.append({"index": ENTRIES_INDEX})
                lines.append(
                    {
                        "size": 0,
                        "query": {
                            "bool": {
                                "filter": [
                                    {"terms": {"warninglist_id": cidr_ids}},
                                    {"term": {"range": ip}},
                                ]
                            }
                        },
                        "aggs": {
                            "lists": {
                                "terms": {
                                    "field": "warninglist_id",
                                    "size": len(cidr_ids),
                                }
                            }
                        },
                    }
                )
            for ip, response in zip(
                chunk, self.client.msearch(body=lines)["responses"]
            ):
                buckets = (
                    response.get("aggregations", {}).get("lists", {}).get("buckets", [])
                )
                if buckets:
                    found[ip] = {b["key"] for b in buckets}
        return found

    def match(self, items: list[tuple[Optional[str], str]]) -> list[list[str]]:
        """For each (attribute type, value), the names of the lists it hits.

        A type of None means "any": every list applies.
        """
        if self.empty:
            return [[] for _ in items]
        candidates = [_candidates(t, v) for t, v in items]
        entry_hits = self._entry_hits(
            set().union(*(c.strings for c in candidates)) if candidates else set(),
            set().union(*(c.hosts for c in candidates)) if candidates else set(),
        )
        cidr_hits = self._cidr_hits(
            set().union(*(c.ips for c in candidates)) if candidates else set()
        )

        results = []
        for (attribute_type, value), cand in zip(items, candidates):
            hits: set = set()
            for list_id, entry in entry_hits:
                wl = self.indexed[list_id]
                if not wl.applies_to(attribute_type):
                    continue
                keys = cand.hosts if wl.type == "hostname" else cand.strings
                if entry in keys:
                    hits.add(wl.name)
            for ip in cand.ips:
                for list_id in cidr_hits.get(ip, ()):
                    if self.indexed[list_id].applies_to(attribute_type):
                        hits.add(self.indexed[list_id].name)
            lowered = value.lower()
            for wl in self.patterns:
                if not wl.applies_to(attribute_type):
                    continue
                if wl.type == "substring":
                    if any(p in lowered for p in wl.patterns):
                        hits.add(wl.name)
                elif any(p.search(value) for p in wl.patterns):
                    hits.add(wl.name)
            results.append(sorted(hits))
        return results


def check_values(
    db: Session, values: list[str], attribute_type: Optional[str] = None
) -> dict:
    """Which enabled lists each value hits (for analysts and integrations)."""
    matcher = Matcher(db)
    unique = list(dict.fromkeys(v for v in values if v))
    results = {}
    for start in range(0, len(unique), BATCH_SIZE):
        chunk = unique[start : start + BATCH_SIZE]
        for value, hits in zip(
            chunk, matcher.match([(attribute_type, v) for v in chunk])
        ):
            results[value] = hits
    return results


# ── Flagging attributes ───────────────────────────────────────────────────


def _evaluate(matcher: Matcher, query: dict) -> dict:
    """Recompute warninglist_hits for matching attributes; write only changes."""
    client = matcher.client
    counts = {"evaluated": 0, "changed": 0}

    def updates() -> Iterator[dict]:
        for hits in stream_exports.iter_pit_pages(
            client,
            ATTRIBUTES_INDEX,
            query,
            source=["type", "value", "warninglist_hits"],
        ):
            items = [
                (h["_source"].get("type"), str(h["_source"].get("value") or ""))
                for h in hits
            ]
            for hit, new in zip(hits, matcher.match(items)):
                counts["evaluated"] += 1
                old = sorted(hit["_source"].get("warninglist_hits") or [])
                if new != old:
                    counts["changed"] += 1
                    yield {
                        "_op_type": "update",
                        "_index": ATTRIBUTES_INDEX,
                        "_id": hit["_id"],
                        "doc": {"warninglist_hits": new},
                    }

    opensearch_helpers.bulk(
        client, updates(), chunk_size=BATCH_SIZE, raise_on_error=False
    )
    client.indices.refresh(index=ATTRIBUTES_INDEX)
    return counts


def evaluate_all(db: Session) -> Optional[dict]:
    """Re-evaluate every live attribute (after the lists changed)."""
    redis = get_redis_client()
    if not redis.set(LOCK_KEY, "1", nx=True, ex=LOCK_SECONDS):
        redis.set(DIRTY_KEY, "1", ex=LOCK_SECONDS)
        return None
    try:
        while True:
            redis.delete(DIRTY_KEY)
            started = int(time.time())
            # A fresh matcher each pass: it reads which lists are enabled now.
            counts = _evaluate(
                Matcher(db), {"bool": {"must_not": [{"term": {"deleted": True}}]}}
            )
            # Attributes written during the scan are picked up by the next sync.
            redis.set(CURSOR_KEY, started)
            logger.info("warninglists: full evaluation %s", counts)
            if not redis.exists(DIRTY_KEY):
                return counts
            db.expire_all()
    finally:
        redis.delete(LOCK_KEY)


def evaluate_recent(db: Session) -> Optional[dict]:
    """Evaluate attributes written since the last run (skipped during a full one).

    Writing ``warninglist_hits`` moves ``updated_at`` too, so a flagged
    attribute is read once more on the next run; its hits then match and
    nothing is written, so the loop settles.
    """
    redis = get_redis_client()
    if not redis.set(LOCK_KEY, "1", nx=True, ex=LOCK_SECONDS):
        return None
    try:
        started = int(time.time())
        cursor = redis.get(CURSOR_KEY)
        if cursor is None:
            # Never fully evaluated: the next full run sets the cursor.
            return None
        matcher = Matcher(db)
        if matcher.empty:
            redis.set(CURSOR_KEY, started)
            return {"evaluated": 0, "changed": 0}
        since = int(cursor) - SYNC_OVERLAP_SECONDS
        counts = _evaluate(
            matcher,
            {
                "bool": {
                    "filter": [
                        {
                            "range": {
                                "updated_at": {"gte": since, "format": "epoch_second"}
                            }
                        }
                    ],
                    "must_not": [{"term": {"deleted": True}}],
                }
            },
        )
        redis.set(CURSOR_KEY, started)
        return counts
    finally:
        redis.delete(LOCK_KEY)
        # A full evaluation asked for while this held the lock gave way to it.
        if redis.exists(DIRTY_KEY):
            from app.worker import tasks

            tasks.evaluate_all_warninglist_hits.delay()


# Matches flagged attributes: outputs put it in ``must_not`` to leave them out.
WARNINGLISTED = {"exists": {"field": "warninglist_hits"}}
