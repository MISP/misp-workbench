"""Organisations' own warninglists: values never to act on in *their*
environment (their ranges and domains, VPN egress, partners, SaaS).

A list belongs to an organisation and is only seen and managed by it (and
admins): its entries say a lot about its network. Entries are of several
kinds, each with a comment and an optional expiry:

- ``value``: an exact value;
- ``cidr``: an address range (an IP in it, or in an ip|port, matches);
- ``suffix``: a domain and its subdomains (``*.corp.example``);
- ``regex``: guarded against catastrophic backtracking, matched against at
  most the first 1024 characters of a value.

Entries are kept here (Postgres) and, but for regexes, in the warninglist
entries index for matching (see warninglists.LocalMatcher). What a list
matches is flagged on attributes and indicators as ``local_list_hits`` (list
ids), apart from the MISP lists: a detection profile leaves those out only
when it attaches the list (``ProfileRules.exclude_lists``), so one
organisation's list doesn't silence everyone else's outputs. Which entry
matched is only told to the list's organisation (``explain``).
"""

import ipaddress
import logging
import re
from datetime import datetime, timezone
from typing import Iterable, Iterator, Optional
from urllib.parse import urlsplit

from opensearchpy import helpers as opensearch_helpers
from sqlalchemy.orm import Session

from app.auth.utils import role_has_scope
from app.models import warninglist as models
from app.repositories import warninglists
from app.services.opensearch import get_opensearch_client

logger = logging.getLogger(__name__)

KINDS = ("value", "cidr", "suffix", "regex")
MAX_ENTRIES = 100_000
MAX_REGEX_LENGTH = 256
SYNC_MAX_BYTES = 5 * 1024 * 1024
SYNC_TIMEOUT = (10, 30)
SYNC_EVERY_SECONDS = 24 * 3600
BULK_CHUNK = 1000

# A group repeated, holding a repetition or an alternation of its own
# ((a+)+, (\w*)*, (a|ab)*): the shapes of catastrophic backtracking.
# Backreferences can blow up too.
_NESTED_QUANTIFIER = re.compile(r"\((?:[^()\\]|\\.)*[*+}|](?:[^()\\]|\\.)*\)[*+{]")
_BACKREFERENCE = re.compile(r"\\[1-9]|\(\?P=")


class InvalidEntry(ValueError):
    pass


class NotVisible(Exception):
    pass


# ── Who sees what ─────────────────────────────────────────────────────────


def sees_all(user) -> bool:
    """Admins see and manage every organisation's lists."""
    return "*" in list(getattr(getattr(user, "role", None), "scopes", None) or [])


def visible(db: Session, user) -> list:
    query = db.query(models.Warninglist).filter(
        models.Warninglist.type == warninglists.LOCAL_TYPE
    )
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
        or db_list.type != warninglists.LOCAL_TYPE
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
    if len(pattern) > MAX_REGEX_LENGTH:
        raise InvalidEntry(f"a regex is at most {MAX_REGEX_LENGTH} characters")
    body = pattern
    match = re.fullmatch(r"/(.*)/([a-z]*)", pattern, flags=re.S)
    if match:
        body = match.group(1)
    if _NESTED_QUANTIFIER.search(body) or _BACKREFERENCE.search(body):
        raise InvalidEntry(
            "nested repetitions and backreferences aren't allowed in a regex "
            "(they can take forever to match)"
        )
    try:
        re.compile(body)
    except re.error as error:
        raise InvalidEntry(f"not a valid regex: {error}") from None


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
    """The lists changed: flag attributes again, in the background (one
    full evaluation however many changes come in the meantime)."""
    from app.worker import tasks

    tasks.evaluate_all_warninglist_hits.delay()


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


def check_source_url(url: Optional[str]) -> Optional[str]:
    if not url:
        return None
    parts = urlsplit(url.strip())
    if parts.scheme not in ("http", "https") or not parts.netloc:
        raise InvalidEntry("a source is an http(s) URL")
    return url.strip()


def sync(db: Session, db_list) -> dict:
    """Replace the entries a previous sync brought with the list at the
    list's source URL (a plain list, see parse_lines)."""
    import requests

    try:
        with requests.get(
            db_list.source_url, timeout=SYNC_TIMEOUT, stream=True
        ) as response:
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
        models.Warninglist.type == warninglists.LOCAL_TYPE,
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
        type=warninglists.LOCAL_TYPE,
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
    db.delete(db_list)
    db.commit()
    _unindex(ids)
    _reflag()


# ── Why a value matches ───────────────────────────────────────────────────


def explain(db: Session, user, values: list[str], type_: Optional[str] = None) -> dict:
    """For each value, the entries of the user's visible lists it matches:
    ``{value: [{list_id, list_name, entry_id, kind, entry, comment,
    expires_at}]}`` (values without one left out)."""
    lists = {w.id: w for w in visible(db, user) if w.enabled}
    if not lists:
        return {}
    matcher = warninglists.LocalMatcher(db)
    matcher.ids = [i for i in matcher.ids if i in lists]
    matcher.regexes = [(i, p) for i, p in matcher.regexes if i in lists]
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
                    and any(
                        warninglists._in_range(ip, d.get("range")) for ip in cand.ips
                    )
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
        bounded = value[: warninglists.REGEX_VALUE_LIMIT]
        regex_lists = {i for i, p in matcher.regexes if p.search(bounded)}
        if regex_lists:
            now = datetime.now(timezone.utc)
            for row in db.query(models.WarninglistEntry).filter(
                models.WarninglistEntry.warninglist_id.in_(regex_lists),
                models.WarninglistEntry.kind == "regex",
            ):
                compiled = warninglists._compile_regex(row.value)
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
