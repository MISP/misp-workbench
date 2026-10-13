"""Organisations' own warninglists: values never to act on in *their*
environment (their ranges and domains, VPN egress, partners, SaaS).

A list belongs to an organisation and is only seen and managed by it (and
admins): its entries say a lot about its network. Entries are of several
kinds, each with a comment and an optional expiry:

- ``value``: an exact value;
- ``cidr``: an address range (an IP in it, or in an ip|port, matches);
- ``suffix``: a domain and its subdomains (``*.corp.example``);
- ``regex``: matched with RE2, in linear time whatever the pattern, against
  at most the first 1024 characters of a value.

Entries are kept here (Postgres) and, but for regexes, in the warninglist
entries index for matching (LocalMatcher).

Which indicators a list matches (its *members*) is private too, so it is
kept out of the attributes and indicators indices, which anyone can query:
a Redis set per list, mirrored to the ``misp-local-list-members`` index for
detection profiles to leave members out with a terms lookup. A profile
leaves a list's members out only when it attaches the list
(``ProfileRules.exclude_lists``), so one organisation's list doesn't silence
everyone else's outputs. Members are recomputed whenever a list changes, and
for the indicators written since, every minute; a value without an indicator
yet is matched as it comes (detection_profiles). Which lists an indicator is
on, and which entry matched, is only told to the lists' organisation.
"""

import fnmatch
import ipaddress
import logging
import re
import socket
import time
from datetime import datetime, timezone
from typing import Iterable, Iterator, Optional
from urllib.parse import urlsplit

from opensearchpy import helpers as opensearch_helpers
from sqlalchemy.orm import Session

from app.auth.utils import role_has_scope
from app.models import warninglist as models
from app.repositories import warninglists
from app.services.opensearch import get_opensearch_client
from app.services.redis import get_redis_client

logger = logging.getLogger(__name__)

KINDS = ("value", "cidr", "suffix", "regex")
MAX_ENTRIES = 100_000
MAX_REGEX_LENGTH = 256
SYNC_MAX_BYTES = 5 * 1024 * 1024
SYNC_TIMEOUT = (10, 30)
SYNC_EVERY_SECONDS = 24 * 3600
BULK_CHUNK = 1000
LOCAL_TYPE = "local"
# A regex is matched against this much of a value at most.
REGEX_VALUE_LIMIT = 1024
# Where lists' members (indicator uuids) are mirrored for terms lookups.
MEMBERS_INDEX = "misp-local-list-members"
EVAL_LOCK = "local_lists:eval:lock"
EVAL_DIRTY = "local_lists:eval:dirty"
EVAL_CURSOR = "local_lists:eval:cursor"
EVAL_LOCK_SECONDS = 2 * 3600
EVAL_OVERLAP_SECONDS = 30


class InvalidEntry(ValueError):
    pass


class NotVisible(Exception):
    pass


# ── Matching ──────────────────────────────────────────────────────────────


def compile_local_regex(pattern: str):
    """An organisation's regex, compiled with RE2: matching takes linear
    time whatever the pattern (no catastrophic backtracking), unlike the
    MISP lists' (vetted upstream). ``/body/flags`` like MISP's; None when
    RE2 can't compile it (backreferences, lookarounds...)."""
    import re2

    body, prefix = pattern, ""
    match = re.fullmatch(r"/(.*)/([a-z]*)", pattern, flags=re.S)
    if match:
        body, modifiers = match.groups()
        if "i" in modifiers:
            prefix = "(?i)"
    try:
        return re2.compile(prefix + body)
    except re2.error:
        return None


def _not_expired(now: int) -> dict:
    return {
        "bool": {
            "should": [
                {"bool": {"must_not": {"exists": {"field": "expires_at"}}}},
                {"range": {"expires_at": {"gt": now}}},
            ],
            "minimum_should_match": 1,
        }
    }


def _in_range(ip: str, cidr: Optional[str]) -> bool:
    try:
        return ipaddress.ip_address(ip) in ipaddress.ip_network(cidr, strict=False)
    except (TypeError, ValueError):
        return False


class LocalMatcher:
    """Enabled organisations' lists (or ``only`` these): which of them each
    value hits. Expired entries don't match."""

    def __init__(self, db: Session, only: Optional[Iterable[int]] = None):
        now = datetime.now(timezone.utc)
        query = db.query(models.Warninglist).filter(
            models.Warninglist.type == LOCAL_TYPE,
            models.Warninglist.enabled.is_(True),
        )
        if only is not None:
            query = query.filter(models.Warninglist.id.in_(list(only)))
        self.ids = [w.id for w in query]
        self.regexes: list = []
        if self.ids:
            for entry in db.query(models.WarninglistEntry).filter(
                models.WarninglistEntry.warninglist_id.in_(self.ids),
                models.WarninglistEntry.kind == "regex",
            ):
                if entry.expires_at is not None and entry.expires_at <= now:
                    continue
                compiled = compile_local_regex(entry.value)
                if compiled is not None:
                    self.regexes.append((entry.warninglist_id, compiled))
        self.client = get_opensearch_client()

    @property
    def empty(self) -> bool:
        return not self.ids

    def entries(self, strings: set, hosts: set, ips: set) -> list[dict]:
        """The live index entries matching any candidate, with their ids."""
        if not self.ids or not (strings or hosts or ips):
            return []
        should: list = []
        for list_type, keys in (("string", strings), ("hostname", hosts)):
            if keys:
                should.append(
                    {
                        "bool": {
                            "filter": [
                                {"term": {"type": list_type}},
                                {"terms": {"value": sorted(keys)}},
                            ]
                        }
                    }
                )
        should += [{"term": {"range": ip}} for ip in sorted(ips)]
        query = {
            "bool": {
                "filter": [
                    {"terms": {"warninglist_id": self.ids}},
                    _not_expired(int(time.time())),
                    {"bool": {"should": should, "minimum_should_match": 1}},
                ]
            }
        }
        found = []
        search_after = None
        while True:
            body = {
                "query": query,
                "size": warninglists.MAX_HITS_PER_SEARCH,
                "sort": [{"_id": "asc"}],
            }
            if search_after:
                body["search_after"] = search_after
            hits = self.client.search(index=warninglists.ENTRIES_INDEX, body=body)[
                "hits"
            ]["hits"]
            found.extend({**h["_source"], "_id": h["_id"]} for h in hits)
            if len(hits) < warninglists.MAX_HITS_PER_SEARCH:
                return found
            search_after = hits[-1]["sort"]

    def match(self, items: list[tuple[Optional[str], str]]) -> list[list[int]]:
        """For each (type, value), the ids of the lists it hits."""
        if self.empty:
            return [[] for _ in items]
        candidates = [warninglists._candidates(t, v) for t, v in items]
        entries: list = []
        for start in range(0, len(candidates), warninglists.BATCH_SIZE):
            chunk = candidates[start : start + warninglists.BATCH_SIZE]
            entries += self.entries(
                set().union(*(c.strings for c in chunk)),
                set().union(*(c.hosts for c in chunk)),
                set().union(*(c.ips for c in chunk)),
            )
        return [
            sorted(self._hits(value, cand, entries))
            for (_, value), cand in zip(items, candidates)
        ]

    def _hits(self, value: str, cand, entries: list[dict]) -> set:
        hits = set()
        for entry in entries:
            if entry["type"] == "string" and entry.get("value") in cand.strings:
                hits.add(entry["warninglist_id"])
            elif entry["type"] == "hostname" and entry.get("value") in cand.hosts:
                hits.add(entry["warninglist_id"])
            elif entry["type"] == "cidr" and any(
                _in_range(ip, entry.get("range")) for ip in cand.ips
            ):
                hits.add(entry["warninglist_id"])
        bounded = value[:REGEX_VALUE_LIMIT]
        for list_id, pattern in self.regexes:
            if list_id not in hits and pattern.search(bounded):
                hits.add(list_id)
        return hits


# ── Members ───────────────────────────────────────────────────────────────


def members_key(list_id: int) -> str:
    return f"local_list:{list_id}:members"


def members(list_id: int) -> set[str]:
    """The indicators (uuids) a list matches."""
    return {
        m.decode() if isinstance(m, bytes) else m
        for m in get_redis_client().smembers(members_key(list_id))
    }


def lists_of(indicator_ids: list[str], list_ids: Iterable[int]) -> dict[str, list]:
    """Of ``list_ids``, the ones each indicator is on."""
    redis = get_redis_client()
    found: dict[str, list] = {i: [] for i in indicator_ids}
    if not indicator_ids:
        return found
    for list_id in list_ids:
        flags = redis.smismember(members_key(list_id), indicator_ids)
        for indicator_id, flagged in zip(indicator_ids, flags):
            if flagged:
                found[indicator_id].append(list_id)
    return found


def _mirror(list_ids: Iterable[int]) -> None:
    """Copy lists' members where profiles' terms lookups read them."""
    client = get_opensearch_client()
    for list_id in list_ids:
        client.index(
            index=MEMBERS_INDEX,
            id=str(list_id),
            body={"members": sorted(members(list_id))},
            refresh=True,
        )


def _forget(list_id: int) -> None:
    get_redis_client().delete(members_key(list_id))
    get_opensearch_client().delete(
        index=MEMBERS_INDEX, id=str(list_id), ignore=[404], refresh=True
    )


def _indicator_pages(query: dict):
    from app.repositories import indicators as indicators_repository
    from app.repositories import stream_exports

    return stream_exports.iter_pit_pages(
        get_opensearch_client(),
        indicators_repository.INDEX,
        query,
        source=["uuid", "type", "value", "deleted"],
    )


def _evaluate(db: Session, query: dict, full: bool) -> dict:
    """Match the indicators of ``query`` against the enabled lists. A full
    run replaces every list's members; otherwise the indicators evaluated
    are added to or taken off each list."""
    redis = get_redis_client()
    matcher = LocalMatcher(db)
    if matcher.empty and full:
        for key in redis.scan_iter("local_list:*:members"):
            key = key.decode() if isinstance(key, bytes) else key
            _forget(int(key.split(":")[1]))
        return {"evaluated": 0, "lists": 0}
    if matcher.empty:
        return {"evaluated": 0, "lists": 0}
    run = f"{int(time.time())}:{id(matcher)}"
    temp = {i: f"local_list:tmp:{run}:{i}" for i in matcher.ids}
    changed: set = set()
    evaluated = 0
    for hits in _indicator_pages(query):
        live = [h["_source"] for h in hits if not h["_source"].get("deleted")]
        gone = [h["_source"]["uuid"] for h in hits if h["_source"].get("deleted")]
        found = matcher.match(
            [(i.get("type"), str(i.get("value") or "")) for i in live]
        )
        evaluated += len(hits)
        pipe = redis.pipeline()
        for indicator, lists in zip(live, found):
            for list_id in matcher.ids:
                if full:
                    if list_id in lists:
                        pipe.sadd(temp[list_id], indicator["uuid"])
                    pipe.expire(temp[list_id], EVAL_LOCK_SECONDS)
                elif list_id in lists:
                    pipe.sadd(members_key(list_id), indicator["uuid"])
                else:
                    pipe.srem(members_key(list_id), indicator["uuid"])
        if not full and gone:
            for list_id in matcher.ids:
                pipe.srem(members_key(list_id), *gone)
        results = pipe.execute()
        if not full and any(results):
            changed.update(matcher.ids)
    if full:
        for list_id in matcher.ids:
            if redis.exists(temp[list_id]):
                redis.rename(temp[list_id], members_key(list_id))
            else:
                redis.delete(members_key(list_id))
        changed.update(matcher.ids)
        # Lists disabled or deleted since: no members.
        enabled = set(matcher.ids)
        for key in redis.scan_iter("local_list:*:members"):
            key = key.decode() if isinstance(key, bytes) else key
            list_id = int(key.split(":")[1])
            if list_id not in enabled:
                _forget(list_id)
    _mirror(changed)
    return {"evaluated": evaluated, "lists": len(matcher.ids)}


def evaluate_all(db: Session) -> Optional[dict]:
    """Recompute every list's members (after the lists changed). One run
    however many changes come in the meantime."""
    redis = get_redis_client()
    if not redis.set(EVAL_LOCK, "1", nx=True, ex=EVAL_LOCK_SECONDS):
        redis.set(EVAL_DIRTY, "1", ex=EVAL_LOCK_SECONDS)
        return None
    try:
        while True:
            redis.delete(EVAL_DIRTY)
            started = int(time.time())
            counts = _evaluate(db, {"term": {"deleted": False}}, full=True)
            redis.set(EVAL_CURSOR, started)
            if not redis.exists(EVAL_DIRTY):
                return counts
            db.expire_all()
    finally:
        redis.delete(EVAL_LOCK)


def evaluate_recent(db: Session) -> Optional[dict]:
    """Match the indicators written since the last run (new ones, tombstones)."""
    redis = get_redis_client()
    cursor = redis.get(EVAL_CURSOR)
    if cursor is None:
        return evaluate_all(db)
    if not redis.set(EVAL_LOCK, "1", nx=True, ex=EVAL_LOCK_SECONDS):
        return None
    try:
        started = int(time.time())
        counts = _evaluate(
            db,
            {
                "range": {
                    "updated_at": {
                        "gte": int(cursor) - EVAL_OVERLAP_SECONDS,
                        "format": "epoch_second",
                    }
                }
            },
            full=False,
        )
        redis.set(EVAL_CURSOR, started)
        return counts
    finally:
        redis.delete(EVAL_LOCK)
        if redis.exists(EVAL_DIRTY):
            from app.worker import tasks

            tasks.evaluate_local_warninglists.delay()


# ── Who sees what ─────────────────────────────────────────────────────────


def sees_all(user) -> bool:
    """Admins see and manage every organisation's lists."""
    return "*" in list(getattr(getattr(user, "role", None), "scopes", None) or [])


def visible(db: Session, user) -> list:
    query = db.query(models.Warninglist).filter(models.Warninglist.type == LOCAL_TYPE)
    if not sees_all(user):
        query = query.filter(models.Warninglist.org_id == user.org_id)
    return query.order_by(models.Warninglist.name).all()


def visible_ids(db: Session, user) -> set[int]:
    return {w.id for w in visible(db, user)}


def get_list(db: Session, user, list_id: int):
    """An organisation's list the user may see; NotVisible otherwise (the
    same answer as for a missing one)."""
    db_list = db.get(models.Warninglist, list_id)
    if (
        db_list is None
        or db_list.type != LOCAL_TYPE
        or not (sees_all(user) or db_list.org_id == user.org_id)
    ):
        raise NotVisible(list_id)
    return db_list


def can_manage(user) -> bool:
    return role_has_scope(
        list(getattr(getattr(user, "role", None), "scopes", None) or []),
        "local_warninglists:manage",
    )


# ── Entries ───────────────────────────────────────────────────────────────


def check_regex(pattern: str) -> None:
    """Regexes are matched with RE2 (linear time, see
    compile_local_regex): one it can't compile is refused."""
    if len(pattern) > MAX_REGEX_LENGTH:
        raise InvalidEntry(f"a regex is at most {MAX_REGEX_LENGTH} characters")
    if compile_local_regex(pattern) is None:
        raise InvalidEntry(
            "not a regex this list can match (backreferences and lookarounds "
            "aren't supported)"
        )


def normalise(value: str, kind: Optional[str] = None) -> tuple[str, str]:
    """``(kind, value)`` of an entry, its kind guessed when not given:
    ``/…/`` a regex, ``*.x`` or ``.x`` a domain suffix, ``a.b.c.d/n`` a
    CIDR, anything else an exact value. InvalidEntry when it isn't one."""
    value = (value or "").strip()
    if not value:
        raise InvalidEntry("an entry can't be empty")
    if kind is None:
        if re.fullmatch(r"/.+/[a-z]*", value, flags=re.S):
            kind = "regex"
        elif value.startswith(("*.", ".")):
            kind = "suffix"
        elif "/" in value and _is_network(value):
            kind = "cidr"
        else:
            kind = "value"
    if kind not in KINDS:
        raise InvalidEntry(f"{kind!r} is not a kind ({', '.join(KINDS)})")
    if kind == "regex":
        check_regex(value)
        return kind, value
    if kind == "cidr":
        try:
            return kind, str(ipaddress.ip_network(value, strict=False))
        except ValueError:
            raise InvalidEntry(f"{value!r} is not an address range") from None
    if kind == "suffix":
        domain = value.lstrip("*").strip(".").lower()
        if not domain or "." not in domain or any(c in domain for c in "/ *"):
            raise InvalidEntry(f"{value!r} is not a domain")
        return kind, domain
    if len(value) > 2048:
        raise InvalidEntry("a value is at most 2048 characters")
    return kind, value


def _is_network(value: str) -> bool:
    try:
        ipaddress.ip_network(value, strict=False)
        return True
    except ValueError:
        return False


def _index_doc(entry) -> Optional[dict]:
    """The entry as the matcher reads it; None for a regex (matched from
    Postgres)."""
    if entry.kind == "regex":
        return None
    list_type = {"value": "string", "cidr": "cidr", "suffix": "hostname"}[entry.kind]
    indexed = warninglists._index_value(list_type, entry.value)
    if indexed is None:
        return None
    return {
        "warninglist_id": entry.warninglist_id,
        "type": list_type,
        **indexed,
        "expires_at": (int(entry.expires_at.timestamp()) if entry.expires_at else None),
    }


def _doc_id(entry_id: int) -> str:
    return f"local-{entry_id}"


def _index(entries: Iterable) -> None:
    actions = (
        {"_index": warninglists.ENTRIES_INDEX, "_id": _doc_id(e.id), "_source": doc}
        for e in entries
        if (doc := _index_doc(e)) is not None
    )
    opensearch_helpers.bulk(
        get_opensearch_client(), actions, chunk_size=BULK_CHUNK, refresh=True
    )


def _unindex(entry_ids: list[int]) -> None:
    client = get_opensearch_client()
    for start in range(0, len(entry_ids), BULK_CHUNK):
        client.delete_by_query(
            index=warninglists.ENTRIES_INDEX,
            body={
                "query": {
                    "ids": {
                        "values": [
                            _doc_id(i) for i in entry_ids[start : start + BULK_CHUNK]
                        ]
                    }
                }
            },
            conflicts="proceed",
            refresh=True,
        )


def _recount(db: Session, db_list) -> None:
    db_list.entry_count = (
        db.query(models.WarninglistEntry)
        .filter(models.WarninglistEntry.warninglist_id == db_list.id)
        .count()
    )
    db_list.updated_at = datetime.now(timezone.utc)


def _reflag() -> None:
    """The lists changed: recompute their members in the background (one
    full evaluation however many changes come in the meantime)."""
    from app.worker import tasks

    tasks.evaluate_local_warninglists.delay()


def entries(
    db: Session, db_list, query: Optional[str] = None, page: int = 1, size: int = 50
) -> dict:
    rows = db.query(models.WarninglistEntry).filter(
        models.WarninglistEntry.warninglist_id == db_list.id
    )
    if query:
        rows = rows.filter(models.WarninglistEntry.value.ilike(f"%{query}%"))
    total = rows.count()
    items = (
        rows.order_by(
            models.WarninglistEntry.created_at.desc(), models.WarninglistEntry.id.desc()
        )
        .offset((max(page, 1) - 1) * size)
        .limit(size)
        .all()
    )
    return {"total": total, "page": max(page, 1), "size": size, "items": items}


def add_entries(
    db: Session,
    db_list,
    new: list[dict],
    user_id: Optional[int],
    origin: str = "manual",
    replace: bool = False,
) -> dict:
    """Add entries (``value``, optional ``kind``, ``comment``,
    ``expires_at``), updating the comment and expiry of ones already there.
    ``replace`` first drops the list's entries of the same origin (a sync
    replaces what the last sync brought). InvalidEntry, naming the line, when
    one isn't valid: nothing is changed then."""
    now = datetime.now(timezone.utc)
    parsed: dict[tuple[str, str], dict] = {}
    for line, item in enumerate(new, start=1):
        try:
            kind, value = normalise(item.get("value"), item.get("kind"))
        except InvalidEntry as error:
            raise InvalidEntry(f"entry {line}: {error}") from None
        parsed[(kind, value)] = item

    existing = {
        (e.kind, e.value): e
        for e in db.query(models.WarninglistEntry).filter(
            models.WarninglistEntry.warninglist_id == db_list.id
        )
    }
    dropped = []
    if replace:
        for key, entry in list(existing.items()):
            if entry.origin == origin and key not in parsed:
                dropped.append(entry.id)
                db.delete(entry)
                del existing[key]
    if len(existing) + len(set(parsed) - set(existing)) > MAX_ENTRIES:
        raise InvalidEntry(f"a list holds at most {MAX_ENTRIES:,} entries")

    touched = []
    added = 0
    for (kind, value), item in parsed.items():
        entry = existing.get((kind, value))
        if entry is None:
            entry = models.WarninglistEntry(
                warninglist_id=db_list.id,
                kind=kind,
                value=value,
                origin=origin,
                created_by=user_id,
                created_at=now,
            )
            db.add(entry)
            added += 1
        entry.comment = item.get("comment") or entry.comment
        entry.expires_at = item.get("expires_at", entry.expires_at)
        touched.append(entry)
    db.flush()
    _recount(db, db_list)
    db.commit()
    _unindex(dropped)
    _index(touched)
    _reflag()
    return {"added": added, "updated": len(touched) - added, "removed": len(dropped)}


def delete_entries(db: Session, db_list, entry_ids: list[int]) -> int:
    rows = (
        db.query(models.WarninglistEntry)
        .filter(
            models.WarninglistEntry.warninglist_id == db_list.id,
            models.WarninglistEntry.id.in_(entry_ids),
        )
        .all()
    )
    for row in rows:
        db.delete(row)
    _recount(db, db_list)
    db.commit()
    _unindex([r.id for r in rows])
    _reflag()
    return len(rows)


# ── Plain lists ───────────────────────────────────────────────────────────


def parse_lines(text: str) -> list[dict]:
    """One entry per line, ``entry  # comment``; blank lines and lines
    starting with ``#`` are skipped."""
    found = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        value, _, comment = line.partition(" #")
        found.append({"value": value.strip(), "comment": comment.strip() or None})
    return found


def export_lines(db: Session, db_list) -> Iterator[str]:
    yield f"# {db_list.name}\n"
    for entry in (
        db.query(models.WarninglistEntry)
        .filter(models.WarninglistEntry.warninglist_id == db_list.id)
        .order_by(models.WarninglistEntry.kind, models.WarninglistEntry.value)
    ):
        value = f"*.{entry.value}" if entry.kind == "suffix" else entry.value
        yield f"{value}  # {entry.comment}\n" if entry.comment else f"{value}\n"


def allowed_hosts() -> list[str]:
    """Hosts lists may sync from (runtime setting warninglists.source_hosts)."""
    from app.database import SessionLocal
    from app.services.runtime_settings import RuntimeSettings

    with SessionLocal() as db:
        hosts = RuntimeSettings(db).get_value("warninglists.source_hosts", default=[])
    return [str(h).strip().lower() for h in hosts or [] if str(h).strip()]


def check_source_url(url: Optional[str]) -> Optional[str]:
    """An http(s) URL on a host an admin allowed. Fetching from inside the
    network is the point (a CMDB), so where to is the operator's call, not
    the list owner's."""
    if not url:
        return None
    parts = urlsplit(url.strip())
    if parts.scheme not in ("http", "https") or not parts.hostname:
        raise InvalidEntry("a source is an http(s) URL")
    host = parts.hostname.lower()
    if not any(fnmatch.fnmatchcase(host, pattern) for pattern in allowed_hosts()):
        raise InvalidEntry(
            f"{host} isn't a host lists may sync from; an admin allows hosts in "
            "the runtime settings (warninglists.source_hosts)"
        )
    return url.strip()


def _forbidden(address: str) -> bool:
    ip = ipaddress.ip_address(address)
    # Private ranges are fine (a CMDB is on one); these never are: the host
    # itself, link-local (cloud metadata services), multicast, reserved.
    return (
        ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    )


def _check_destination(url: str) -> None:
    """At fetch time: the host is still allowed, and none of the addresses
    it resolves to is one a sync may never reach."""
    check_source_url(url)
    parts = urlsplit(url)
    port = parts.port or (443 if parts.scheme == "https" else 80)
    try:
        addresses = {info[4][0] for info in socket.getaddrinfo(parts.hostname, port)}
    except socket.gaierror as error:
        raise InvalidEntry(f"{parts.hostname} doesn't resolve: {error}") from None
    blocked = sorted(a for a in addresses if _forbidden(a))
    if blocked:
        raise InvalidEntry(
            f"{parts.hostname} resolves to an address a sync may not reach "
            f"({', '.join(blocked)})"
        )


def sync(db: Session, db_list) -> dict:
    """Replace the entries a previous sync brought with the list at the
    list's source URL (a plain list, see parse_lines)."""
    import requests

    try:
        _check_destination(db_list.source_url)
        # No redirects: they could lead anywhere the checks above don't.
        with requests.get(
            db_list.source_url,
            timeout=SYNC_TIMEOUT,
            stream=True,
            allow_redirects=False,
        ) as response:
            if response.is_redirect:
                raise InvalidEntry("the source redirects; give its final URL")
            response.raise_for_status()
            body = b""
            for chunk in response.iter_content(64 * 1024):
                body += chunk
                if len(body) > SYNC_MAX_BYTES:
                    raise InvalidEntry(
                        f"the source is larger than {SYNC_MAX_BYTES // 1024 // 1024} MB"
                    )
        result = add_entries(
            db,
            db_list,
            parse_lines(body.decode("utf-8", errors="replace")),
            None,
            origin="sync",
            replace=True,
        )
        db_list.sync_error = None
    except (requests.RequestException, InvalidEntry) as error:
        db.rollback()
        db_list.sync_error = str(error)[:1000]
        result = {"error": db_list.sync_error}
    db_list.synced_at = datetime.now(timezone.utc)
    db.commit()
    return result


# ── Upkeep ────────────────────────────────────────────────────────────────


def sweep(db: Session) -> dict:
    """Drop expired entries, and sync the lists whose source is due."""
    now = datetime.now(timezone.utc)
    expired = (
        db.query(models.WarninglistEntry)
        .filter(
            models.WarninglistEntry.expires_at.isnot(None),
            models.WarninglistEntry.expires_at <= now,
        )
        .all()
    )
    lists = {e.warninglist_id for e in expired}
    for entry in expired:
        db.delete(entry)
    for list_id in lists:
        _recount(db, db.get(models.Warninglist, list_id))
    db.commit()
    if expired:
        _unindex([e.id for e in expired])
        _reflag()

    synced = 0
    for db_list in db.query(models.Warninglist).filter(
        models.Warninglist.type == LOCAL_TYPE,
        models.Warninglist.source_url.isnot(None),
        models.Warninglist.enabled.is_(True),
    ):
        due = db_list.synced_at is None or (
            (now - db_list.synced_at).total_seconds() >= SYNC_EVERY_SECONDS
        )
        if due:
            sync(db, db_list)
            synced += 1
    return {"expired": len(expired), "synced": synced}


# ── Lists ─────────────────────────────────────────────────────────────────


def create_list(db: Session, org_id: int, name: str, description=None, source_url=None):
    db_list = models.Warninglist(
        name=name,
        description=description,
        type=LOCAL_TYPE,
        category="organisation",
        version=0,
        matching_attributes=[],
        entry_count=0,
        enabled=True,
        org_id=org_id,
        source_url=check_source_url(source_url),
        updated_at=datetime.now(timezone.utc),
    )
    db.add(db_list)
    db.commit()
    db.refresh(db_list)
    return db_list


def update_list(db: Session, db_list, patch: dict):
    if "source_url" in patch:
        patch["source_url"] = check_source_url(patch["source_url"])
        db_list.synced_at = None
    enabled_before = db_list.enabled
    for key, value in patch.items():
        setattr(db_list, key, value)
    db_list.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(db_list)
    if db_list.enabled != enabled_before:
        _reflag()
    return db_list


def delete_list(db: Session, db_list) -> None:
    ids = [
        i
        for (i,) in db.query(models.WarninglistEntry.id).filter(
            models.WarninglistEntry.warninglist_id == db_list.id
        )
    ]
    list_id = db_list.id
    db.delete(db_list)
    db.commit()
    _unindex(ids)
    _forget(list_id)


# ── Why a value matches ───────────────────────────────────────────────────


def explain(db: Session, user, values: list[str], type_: Optional[str] = None) -> dict:
    """For each value, the entries of the user's visible lists it matches:
    ``{value: [{list_id, list_name, entry_id, kind, entry, comment,
    expires_at}]}`` (values without one left out)."""
    lists = {w.id: w for w in visible(db, user) if w.enabled}
    if not lists:
        return {}
    matcher = LocalMatcher(db, only=lists)
    found: dict[str, list] = {}
    for value in dict.fromkeys(v for v in values if v):
        cand = warninglists._candidates(type_, value)
        docs = matcher.entries(cand.strings, cand.hosts, cand.ips)
        entry_ids = [
            int(d["_id"].removeprefix("local-"))
            for d in docs
            if d["warninglist_id"] in lists
            and (
                (d["type"] == "string" and d.get("value") in cand.strings)
                or (d["type"] == "hostname" and d.get("value") in cand.hosts)
                or (
                    d["type"] == "cidr"
                    and any(_in_range(ip, d.get("range")) for ip in cand.ips)
                )
            )
        ]
        rows = (
            db.query(models.WarninglistEntry)
            .filter(models.WarninglistEntry.id.in_(entry_ids))
            .all()
            if entry_ids
            else []
        )
        bounded = value[:REGEX_VALUE_LIMIT]
        regex_lists = {i for i, p in matcher.regexes if p.search(bounded)}
        if regex_lists:
            now = datetime.now(timezone.utc)
            for row in db.query(models.WarninglistEntry).filter(
                models.WarninglistEntry.warninglist_id.in_(regex_lists),
                models.WarninglistEntry.kind == "regex",
            ):
                compiled = compile_local_regex(row.value)
                if (
                    compiled is not None
                    and compiled.search(bounded)
                    and (row.expires_at is None or row.expires_at > now)
                ):
                    rows.append(row)
        if rows:
            found[value] = [
                {
                    "list_id": r.warninglist_id,
                    "list_name": lists[r.warninglist_id].name,
                    "entry_id": r.id,
                    "kind": r.kind,
                    "entry": r.value,
                    "comment": r.comment,
                    "expires_at": r.expires_at,
                }
                for r in rows
            ]
    return found
