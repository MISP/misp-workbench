"""MISP-compatible ``restSearch`` for attributes and events.

Implements the subset of MISP's ``/attributes/restSearch`` and
``/events/restSearch`` filters that SIEM integrations (Splunk's MISP42 app, the
Wazuh MISP integration, Graylog MISP adapters, PyMISP's ``search()``) actually
send, translated into OpenSearch queries.

Results are produced by generators that page through OpenSearch with
``search_after``, so the response can be streamed and memory stays flat no
matter how many attributes match. Everything that can fail on bad input
(parameter parsing, query building, resolving event-level filters) happens
eagerly in ``prepare_*`` so the router can still answer with a 400 before the
first byte of the stream is sent.

Attribute documents do not carry their event's fields (published, info, org,
event tags...). Event-level filters are therefore resolved against
``misp-events`` first and turned into an ``event_uuid`` clause on the
attribute query; see ``_event_uuid_clause``.
"""

import csv
import io
import json
import logging
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Iterator, Optional

from app.repositories import events as events_repository
from app.schemas import event as event_schemas
from app.services.opensearch import get_opensearch_client

logger = logging.getLogger(__name__)

ATTRIBUTES_INDEX = "misp-attributes"
EVENTS_INDEX = "misp-events"
OBJECTS_INDEX = "misp-objects"

# Page size used when streaming through OpenSearch with search_after.
PAGE_SIZE = 1000
# index.max_result_window default: `from + size` beyond this is rejected.
MAX_RESULT_WINDOW = 10_000
# index.max_terms_count defaults to 65,536 per terms query; stay below it and
# OR several terms queries together for larger sets.
MAX_TERMS_PER_CLAUSE = 50_000
# keyword sub-fields are mapped with ignore_above: 256, so longer values are
# only reachable through the analyzed text field.
KEYWORD_IGNORE_ABOVE = 256

ATTRIBUTE_RETURN_FORMATS = ("json", "csv", "text")
EVENT_RETURN_FORMATS = ("json",)

CSV_COLUMNS = [
    "uuid",
    "event_id",
    "category",
    "type",
    "value",
    "comment",
    "to_ids",
    "date",
    "object_relation",
    "attribute_tag",
    "object_uuid",
    "object_name",
    "object_meta-category",
]

EVENT_CONTEXT_FIELDS = [
    "uuid",
    "id",
    "info",
    "org_id",
    "orgc_id",
    "distribution",
    "sharing_group_id",
    "published",
    "date",
    "threat_level",
    "analysis",
    "timestamp",
    "publish_timestamp",
    "organisation",
    "tags",
]

_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.I
)
_RELATIVE_TS_RE = re.compile(r"^(\d+)\s*([smhdw])$", re.I)
_RELATIVE_UNITS = {"s": 1, "m": 60, "h": 3600, "d": 86400, "w": 604800}

# Event-level filters accepted by /attributes/restSearch. Any of them being
# present triggers a lookup against misp-events.
_ATTRIBUTE_EVENT_LEVEL_PARAMS = (
    "published",
    "eventid",
    "eventinfo",
    "org",
    "last",
    "publish_timestamp",
    "event_timestamp",
    "threat_level_id",
    "from",
    "to",
    "date",
)


class RestSearchError(ValueError):
    """Invalid restSearch parameters; surfaced to the client as a 400."""


# --------------------------------------------------------------------------
# Parameter parsing
# --------------------------------------------------------------------------


def normalize_params(raw: Any) -> dict:
    """Lower-case the keys and unwrap the legacy ``{"request": {...}}`` body."""
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise RestSearchError("restSearch parameters must be a JSON object")
    if set(raw.keys()) == {"request"} and isinstance(raw["request"], dict):
        raw = raw["request"]
    return {str(k).lower(): v for k, v in raw.items()}


def _is_empty(value: Any) -> bool:
    return value is None or value == "" or value == [] or value == {}


def _as_list(value: Any) -> list:
    if _is_empty(value):
        return []
    if isinstance(value, (list, tuple, set)):
        return [v for v in value if not _is_empty(v)]
    return [value]


def _split_filter(raw: Any) -> tuple[list[str], list[str], list[str]]:
    """Split a MISP filter value into (OR, AND, NOT) value lists.

    Accepts a scalar, a list (``"!"``-prefixed entries are negated) or MISP's
    ``{"OR": [...], "AND": [...], "NOT": [...]}`` form.
    """
    any_of: list[str] = []
    all_of: list[str] = []
    none_of: list[str] = []

    if isinstance(raw, dict):
        for key, values in raw.items():
            bucket = {"or": any_of, "and": all_of, "not": none_of}.get(str(key).lower())
            if bucket is None:
                raise RestSearchError(
                    f"Unknown filter operator {key!r}; expected OR, AND or NOT"
                )
            bucket.extend(str(v) for v in _as_list(values))
        return any_of, all_of, none_of

    for value in _as_list(raw):
        value = str(value)
        if value.startswith("!") and len(value) > 1:
            none_of.append(value[1:])
        else:
            any_of.append(value)
    return any_of, all_of, none_of


_TRUE = {"1", "true", "yes"}
_FALSE = {"0", "false", "no"}


def _parse_bool(value: Any, name: str) -> Optional[bool]:
    """Parse a MISP boolean filter: None means "don't filter"."""
    values = _as_list(value)
    if not values:
        return None
    parsed = set()
    for v in values:
        s = str(v).strip().lower()
        if s in _TRUE:
            parsed.add(True)
        elif s in _FALSE:
            parsed.add(False)
        else:
            raise RestSearchError(f"Invalid boolean value {v!r} for {name}")
    if len(parsed) != 1:
        return None
    return parsed.pop()


def _parse_flag(params: dict, name: str, default: bool = False) -> bool:
    parsed = _parse_bool(params.get(name), name)
    return default if parsed is None else parsed


def _parse_int(value: Any, name: str, minimum: int = 0) -> Optional[int]:
    if _is_empty(value):
        return None
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        raise RestSearchError(f"Invalid integer value {value!r} for {name}")
    if parsed < minimum:
        raise RestSearchError(f"{name} must be >= {minimum}")
    return parsed


def parse_timestamp(value: Any, name: str, now: Optional[int] = None) -> int:
    """Epoch seconds, a relative age (``30m``, ``7d``, ``2w``) or a date."""
    if isinstance(value, bool):
        raise RestSearchError(f"Invalid timestamp {value!r} for {name}")
    if isinstance(value, (int, float)):
        return int(value)
    s = str(value).strip()
    if s.isdigit():
        return int(s)
    match = _RELATIVE_TS_RE.match(s)
    if match:
        now = now if now is not None else int(time.time())
        return now - int(match.group(1)) * _RELATIVE_UNITS[match.group(2).lower()]
    try:
        parsed = datetime.fromisoformat(s)
    except ValueError:
        raise RestSearchError(f"Invalid timestamp {value!r} for {name}")
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return int(parsed.timestamp())


def _timestamp_range(value: Any, name: str, field_name: str) -> Optional[dict]:
    """``x`` means "since x"; ``[from, to]`` is an inclusive window."""
    if _is_empty(value):
        return None
    if isinstance(value, (list, tuple)):
        if len(value) != 2:
            raise RestSearchError(f"{name} range must be [from, to]")
        bounds = {}
        if not _is_empty(value[0]):
            bounds["gte"] = parse_timestamp(value[0], name)
        if not _is_empty(value[1]):
            bounds["lte"] = parse_timestamp(value[1], name)
        return {"range": {field_name: bounds}} if bounds else None
    return {"range": {field_name: {"gte": parse_timestamp(value, name)}}}


def _parse_date(value: Any, name: str) -> str:
    """Event dates are compared as ``YYYY-MM-DD``; epochs are converted."""
    s = str(value).strip()
    if s.isdigit():
        return datetime.fromtimestamp(int(s), tz=timezone.utc).strftime("%Y-%m-%d")
    try:
        return datetime.fromisoformat(s).strftime("%Y-%m-%d")
    except ValueError:
        raise RestSearchError(f"Invalid date {value!r} for {name}")


def _parse_pagination(params: dict) -> tuple[Optional[int], int]:
    limit = _parse_int(params.get("limit"), "limit", minimum=1)
    page = _parse_int(params.get("page"), "page", minimum=1) or 1
    if limit is None:
        return None, 0
    return limit, (page - 1) * limit


# --------------------------------------------------------------------------
# Query building
# --------------------------------------------------------------------------


def _value_clause(keyword_field: str, text_field: Optional[str], value: str) -> dict:
    """Exact match, or a case-insensitive LIKE when the value contains ``%``."""
    if "%" in value:
        pattern = (
            value.replace("\\", "\\\\")
            .replace("*", "\\*")
            .replace("?", "\\?")
            .replace("%", "*")
        )
        return {
            "wildcard": {keyword_field: {"value": pattern, "case_insensitive": True}}
        }
    if text_field and len(value) > KEYWORD_IGNORE_ABOVE:
        return {"match_phrase": {text_field: value}}
    return {"term": {keyword_field: value}}


def _apply_filter(
    must: list,
    must_not: list,
    raw: Any,
    clause_for,
) -> None:
    """Add a parsed OR/AND/NOT filter to the given clause lists."""
    any_of, all_of, none_of = _split_filter(raw)
    if any_of:
        clauses = [clause_for(v) for v in any_of]
        must.append(
            clauses[0]
            if len(clauses) == 1
            else {"bool": {"should": clauses, "minimum_should_match": 1}}
        )
    must.extend(clause_for(v) for v in all_of)
    must_not.extend(clause_for(v) for v in none_of)


def _keyword_filter(must, must_not, raw, field_name):
    _apply_filter(
        must,
        must_not,
        raw,
        lambda v: _value_clause(f"{field_name}.keyword", field_name, v),
    )


def _terms_any(field_name: str, values: list[str]) -> dict:
    if len(values) <= MAX_TERMS_PER_CLAUSE:
        return {"terms": {field_name: values}}
    return {
        "bool": {
            "should": [
                {"terms": {field_name: values[i : i + MAX_TERMS_PER_CLAUSE]}}
                for i in range(0, len(values), MAX_TERMS_PER_CLAUSE)
            ],
            "minimum_should_match": 1,
        }
    }


def _bool_query(must: list, must_not: list) -> dict:
    if not must and not must_not:
        return {"match_all": {}}
    query: dict = {}
    if must:
        query["filter"] = must
    if must_not:
        query["must_not"] = must_not
    return {"bool": query}


def _scan_uuids(client, index: str, query: dict) -> list[str]:
    uuids: list[str] = []
    search_after = None
    while True:
        body = {
            "query": query,
            "_source": ["uuid"],
            "size": MAX_RESULT_WINDOW,
            "sort": [{"uuid.keyword": "asc"}],
        }
        if search_after:
            body["search_after"] = search_after
        hits = client.search(index=index, body=body)["hits"]["hits"]
        uuids.extend(str(h["_source"]["uuid"]) for h in hits)
        if len(hits) < MAX_RESULT_WINDOW:
            return uuids
        search_after = hits[-1]["sort"]


@dataclass
class _EventResolver:
    """Turns an event-level query into an ``event_uuid`` clause.

    Fetches whichever side is smaller, the matching events or their
    complement, so a near-universal filter such as ``published: 1`` costs as
    little as a selective one.
    """

    client: Any
    _total: Optional[int] = None

    def total(self) -> int:
        if self._total is None:
            self._total = self.client.count(index=EVENTS_INDEX)["count"]
        return self._total

    def clause(self, event_query: dict, field_name: str = "event_uuid") -> dict:
        matched = self.client.count(index=EVENTS_INDEX, body={"query": event_query})[
            "count"
        ]
        if matched == 0:
            return {"match_none": {}}
        total = self.total()
        if matched >= total:
            return {"match_all": {}}
        if matched <= total - matched:
            return _terms_any(
                field_name, _scan_uuids(self.client, EVENTS_INDEX, event_query)
            )
        complement = _scan_uuids(
            self.client, EVENTS_INDEX, {"bool": {"must_not": [event_query]}}
        )
        return {"bool": {"must_not": [_terms_any(field_name, complement)]}}


def _org_clause(value: str) -> dict:
    if value.isdigit():
        return {"term": {"orgc_id": int(value)}}
    if _UUID_RE.match(value):
        return {"term": {"organisation.uuid.keyword": value}}
    return _value_clause("organisation.name.keyword", "organisation.name", value)


def _eventid_clause(value: str) -> dict:
    if value.isdigit():
        return {"term": {"id": int(value)}}
    return {"term": {"uuid.keyword": value}}


def _tag_clause(value: str) -> dict:
    return _value_clause("tags.name.keyword", "tags.name", value)


def _build_event_level_query(params: dict, timestamp_param: str) -> dict:
    """Filters that live on misp-events documents.

    ``timestamp_param`` is the parameter name holding the *event* timestamp:
    ``timestamp`` on /events/restSearch, ``event_timestamp`` on attributes.
    """
    must: list = []
    must_not: list = [{"term": {"deleted": True}}]

    published = _parse_bool(params.get("published"), "published")
    if published is not None:
        must.append({"term": {"published": published}})

    _apply_filter(must, must_not, params.get("eventid"), _eventid_clause)
    _apply_filter(
        must,
        must_not,
        params.get("eventinfo"),
        lambda v: _value_clause("info.keyword", "info", v),
    )
    _apply_filter(must, must_not, params.get("org"), _org_clause)
    _apply_filter(
        must,
        must_not,
        params.get("threat_level_id"),
        lambda v: {"term": {"threat_level": _parse_int(v, "threat_level_id")}},
    )

    for name, field_name in (
        ("last", "publish_timestamp"),
        ("publish_timestamp", "publish_timestamp"),
        (timestamp_param, "timestamp"),
    ):
        clause = _timestamp_range(params.get(name), name, field_name)
        if clause:
            must.append(clause)

    date_bounds = {}
    if not _is_empty(params.get("from")):
        date_bounds["gte"] = _parse_date(params["from"], "from")
    if not _is_empty(params.get("to")):
        date_bounds["lte"] = _parse_date(params["to"], "to")
    if not _is_empty(params.get("date")):
        date_bounds["gte"] = _parse_date(params["date"], "date")
    if date_bounds:
        must.append({"range": {"date": {**date_bounds, "format": "yyyy-MM-dd"}}})

    return _bool_query(must, must_not)


def _deleted_clause(params: dict) -> Optional[dict]:
    deleted = _parse_bool(params.get("deleted"), "deleted")
    if deleted is None and not _is_empty(params.get("deleted")):
        return None  # [0, 1]: both
    return {"term": {"deleted": bool(deleted)}}


def build_attribute_query(params: dict, client=None) -> dict:
    client = client or get_opensearch_client()
    must: list = []
    must_not: list = []

    deleted = _deleted_clause(params)
    if deleted:
        must.append(deleted)

    _keyword_filter(must, must_not, params.get("value"), "value")
    _keyword_filter(must, must_not, params.get("type"), "type")
    _keyword_filter(must, must_not, params.get("category"), "category")
    _keyword_filter(must, must_not, params.get("object_relation"), "object_relation")
    # MISP matches `uuid` against both the attribute and its event.
    _apply_filter(
        must,
        must_not,
        params.get("uuid"),
        lambda v: {
            "bool": {
                "should": [
                    {"term": {"uuid.keyword": v}},
                    {"term": {"event_uuid": v}},
                ],
                "minimum_should_match": 1,
            }
        },
    )

    to_ids = _parse_bool(params.get("to_ids"), "to_ids")
    if to_ids is not None:
        must.append({"term": {"to_ids": to_ids}})

    for name in ("timestamp", "attribute_timestamp"):
        clause = _timestamp_range(params.get(name), name, "timestamp")
        if clause:
            must.append(clause)

    resolver = _EventResolver(client)

    # MISP's attribute tag filter also matches tags inherited from the event.
    if not _is_empty(params.get("tags")):
        events_base = {"bool": {"must_not": [{"term": {"deleted": True}}]}}

        def tag_clause(value: str) -> dict:
            event_query = {"bool": {"filter": [events_base, _tag_clause(value)]}}
            return {
                "bool": {
                    "should": [_tag_clause(value), resolver.clause(event_query)],
                    "minimum_should_match": 1,
                }
            }

        _apply_filter(must, must_not, params.get("tags"), tag_clause)

    if any(not _is_empty(params.get(p)) for p in _ATTRIBUTE_EVENT_LEVEL_PARAMS):
        event_query = _build_event_level_query(params, "event_timestamp")
        must.append(resolver.clause(event_query))

    return _bool_query(must, must_not)


_ATTRIBUTE_LEVEL_PARAMS_FOR_EVENTS = (
    "value",
    "type",
    "category",
    "object_relation",
    "to_ids",
    "attribute_timestamp",
)


def build_event_query(params: dict, client=None) -> dict:
    client = client or get_opensearch_client()
    event_query = _build_event_level_query(params, "timestamp")
    must = [event_query]
    must_not: list = []

    _apply_filter(must, must_not, params.get("tags"), _tag_clause)
    _apply_filter(
        must,
        must_not,
        params.get("uuid"),
        lambda v: {"term": {"uuid.keyword": v}},
    )

    # Attribute-level filters select events containing a matching attribute.
    if any(not _is_empty(params.get(p)) for p in _ATTRIBUTE_LEVEL_PARAMS_FOR_EVENTS):
        attribute_params = {
            p: params[p] for p in _ATTRIBUTE_LEVEL_PARAMS_FOR_EVENTS if p in params
        }
        attribute_query = build_attribute_query(attribute_params, client)
        event_uuids = _collect_event_uuids(client, attribute_query)
        if not event_uuids:
            must.append({"match_none": {}})
        else:
            must.append(_terms_any("uuid.keyword", event_uuids))

    return _bool_query(must, must_not)


def _collect_event_uuids(client, attribute_query: dict) -> list[str]:
    """Distinct event uuids of matching attributes, via a composite agg."""
    uuids: list[str] = []
    after = None
    while True:
        composite: dict = {
            "size": MAX_RESULT_WINDOW,
            "sources": [{"event_uuid": {"terms": {"field": "event_uuid"}}}],
        }
        if after:
            composite["after"] = after
        response = client.search(
            index=ATTRIBUTES_INDEX,
            body={
                "size": 0,
                "query": attribute_query,
                "aggs": {"events": {"composite": composite}},
            },
        )
        agg = response["aggregations"]["events"]
        uuids.extend(b["key"]["event_uuid"] for b in agg["buckets"])
        after = agg.get("after_key")
        if not after or not agg["buckets"]:
            return uuids


# --------------------------------------------------------------------------
# Paging
# --------------------------------------------------------------------------


def iter_pages(
    client,
    index: str,
    query: dict,
    source: Any = True,
    limit: Optional[int] = None,
    offset: int = 0,
) -> Iterator[list[dict]]:
    """Yield pages of hits sorted by uuid, honouring MISP's limit/page."""
    sort = [{"uuid.keyword": "asc"}]

    if limit is not None and offset + limit <= MAX_RESULT_WINDOW:
        for start in range(offset, offset + limit, PAGE_SIZE):
            size = min(PAGE_SIZE, offset + limit - start)
            hits = client.search(
                index=index,
                body={
                    "query": query,
                    "_source": source,
                    "from": start,
                    "size": size,
                    "sort": sort,
                },
            )["hits"]["hits"]
            if hits:
                yield hits
            if len(hits) < size:
                return
        return

    search_after = None

    # Deep pages: walk past the offset without fetching sources.
    to_skip = offset
    while to_skip > 0:
        size = min(to_skip, MAX_RESULT_WINDOW)
        body = {"query": query, "_source": False, "size": size, "sort": sort}
        if search_after:
            body["search_after"] = search_after
        hits = client.search(index=index, body=body)["hits"]["hits"]
        if not hits:
            return
        to_skip -= len(hits)
        search_after = hits[-1]["sort"]

    remaining = limit
    while remaining is None or remaining > 0:
        size = PAGE_SIZE if remaining is None else min(PAGE_SIZE, remaining)
        body = {"query": query, "_source": source, "size": size, "sort": sort}
        if search_after:
            body["search_after"] = search_after
        hits = client.search(index=index, body=body)["hits"]["hits"]
        if not hits:
            return
        yield hits
        if remaining is not None:
            remaining -= len(hits)
        if len(hits) < size:
            return
        search_after = hits[-1]["sort"]


def _mget_sources(client, index: str, ids: set, fields: Optional[list] = None) -> dict:
    if not ids:
        return {}
    kwargs = {"_source_includes": fields} if fields else {}
    response = client.mget(index=index, body={"ids": list(ids)}, **kwargs)
    return {d["_id"]: d["_source"] for d in response["docs"] if d.get("found")}


# --------------------------------------------------------------------------
# Serialization
# --------------------------------------------------------------------------


def _str_or_none(value: Any) -> Optional[str]:
    return None if value is None else str(value)


def _iso_seen(value: Any) -> Optional[str]:
    if value is None:
        return None
    try:
        return datetime.fromtimestamp(int(value), tz=timezone.utc).isoformat(
            timespec="microseconds"
        )
    except (TypeError, ValueError, OverflowError):
        return None


def _misp_tag(tag: dict, inherited: bool = False) -> dict:
    out = {
        "id": _str_or_none(tag.get("id")),
        "name": tag.get("name"),
        "colour": tag.get("colour"),
        "exportable": tag.get("exportable", True),
        "hide_tag": tag.get("hide_tag", False),
        "is_galaxy": tag.get("is_galaxy", False),
        "is_custom_galaxy": tag.get("is_custom_galaxy", False),
        "local": tag.get("local_only", False),
    }
    if inherited:
        out["inherited"] = 1
    return out


def _event_id(event: Optional[dict], event_uuid: Optional[str]) -> Optional[str]:
    """MISP's numeric id when the event has one, else its uuid.

    Events created locally have no numeric id; MISP accepts uuids wherever an
    event id is expected, so clients can still link back to the event.
    """
    if event and event.get("id") is not None:
        return str(event["id"])
    return event_uuid


def _attribute_to_misp(
    source: dict,
    event: Optional[dict],
    include_event_tags: bool,
    include_context: bool,
) -> dict:
    event_uuid = source.get("event_uuid")
    tags = [_misp_tag(t) for t in source.get("tags") or []]
    if include_event_tags and event:
        tags.extend(_misp_tag(t, inherited=True) for t in event.get("tags") or [])

    attribute = {
        "id": _str_or_none(source.get("id")) or source.get("uuid"),
        "event_id": _event_id(event, event_uuid),
        "object_id": source.get("object_uuid") or "0",
        "object_relation": source.get("object_relation"),
        "category": source.get("category"),
        "type": source.get("type"),
        "to_ids": bool(source.get("to_ids")),
        "uuid": source.get("uuid"),
        "timestamp": _str_or_none(source.get("timestamp")),
        "distribution": _str_or_none(source.get("distribution")),
        "sharing_group_id": _str_or_none(source.get("sharing_group_id") or 0),
        "comment": source.get("comment") or "",
        "deleted": bool(source.get("deleted")),
        "disable_correlation": bool(source.get("disable_correlation")),
        "first_seen": _iso_seen(source.get("first_seen")),
        "last_seen": _iso_seen(source.get("last_seen")),
        "value": source.get("value"),
        "Event": _event_context(event, event_uuid, include_context),
        "Tag": tags,
    }
    if not tags:
        del attribute["Tag"]
    return attribute


def _event_context(
    event: Optional[dict], event_uuid: Optional[str], full: bool
) -> dict:
    event = event or {}
    context = {
        "org_id": _str_or_none(event.get("org_id")),
        "distribution": _str_or_none(event.get("distribution")),
        "id": _event_id(event, event_uuid),
        "info": event.get("info"),
        "orgc_id": _str_or_none(event.get("orgc_id")),
        "uuid": event_uuid,
    }
    if full:
        org = event.get("organisation") or {}
        context.update(
            {
                "date": (event.get("date") or "")[:10] or None,
                "threat_level_id": _str_or_none(event.get("threat_level")),
                "analysis": _str_or_none(event.get("analysis")),
                "published": bool(event.get("published")),
                "timestamp": _str_or_none(event.get("timestamp")),
                "publish_timestamp": _str_or_none(event.get("publish_timestamp")),
                "Orgc": {
                    "id": _str_or_none(org.get("id")),
                    "name": org.get("name"),
                    "uuid": org.get("uuid"),
                },
                "Tag": [_misp_tag(t) for t in event.get("tags") or []],
            }
        )
    return context


def csv_line(row: list) -> str:
    buffer = io.StringIO()
    csv.writer(buffer, lineterminator="\n").writerow(row)
    return buffer.getvalue()


def _attribute_csv_row(
    source: dict, event: Optional[dict], obj: Optional[dict]
) -> list:
    timestamp = source.get("timestamp")
    date = (
        datetime.fromtimestamp(int(timestamp), tz=timezone.utc).strftime("%Y%m%d")
        if timestamp
        else ""
    )
    obj = obj or {}
    return [
        source.get("uuid"),
        _event_id(event, source.get("event_uuid")),
        source.get("category"),
        source.get("type"),
        source.get("value"),
        source.get("comment") or "",
        1 if source.get("to_ids") else 0,
        date,
        source.get("object_relation") or "",
        ",".join(t.get("name", "") for t in source.get("tags") or []),
        source.get("object_uuid") or "",
        obj.get("name") or "",
        obj.get("meta_category") or "",
    ]


# --------------------------------------------------------------------------
# Public entry points
# --------------------------------------------------------------------------


@dataclass
class PreparedSearch:
    """A validated search, ready to be streamed."""

    return_format: str
    media_type: str
    query: dict
    params: dict
    limit: Optional[int] = None
    offset: int = 0
    client: Any = field(default=None, repr=False)


_MEDIA_TYPES = {"json": "application/json", "csv": "text/csv", "text": "text/plain"}


def _return_format(params: dict, allowed: tuple) -> str:
    fmt = str(params.get("returnformat") or "json").lower()
    if fmt not in allowed:
        raise RestSearchError(
            f"Unsupported returnFormat {fmt!r}; supported: {', '.join(allowed)}"
        )
    return fmt


def prepare_attribute_search(params: dict) -> PreparedSearch:
    params = normalize_params(params)
    fmt = _return_format(params, ATTRIBUTE_RETURN_FORMATS)
    limit, offset = _parse_pagination(params)
    client = get_opensearch_client()
    return PreparedSearch(
        return_format=fmt,
        media_type=_MEDIA_TYPES[fmt],
        query=build_attribute_query(params, client),
        params=params,
        limit=limit,
        offset=offset,
        client=client,
    )


def prepare_event_search(params: dict) -> PreparedSearch:
    params = normalize_params(params)
    fmt = _return_format(params, EVENT_RETURN_FORMATS)
    limit, offset = _parse_pagination(params)
    client = get_opensearch_client()
    return PreparedSearch(
        return_format=fmt,
        media_type=_MEDIA_TYPES[fmt],
        query=build_event_query(params, client),
        params=params,
        limit=limit,
        offset=offset,
        client=client,
    )


def stream_attributes(search: PreparedSearch) -> Iterator[str]:
    client = search.client
    params = search.params
    fmt = search.return_format
    include_event_tags = _parse_flag(params, "includeeventtags")
    include_context = _parse_flag(params, "includecontext")
    needs_events = fmt in ("json", "csv")

    pages = iter_pages(
        client,
        ATTRIBUTES_INDEX,
        search.query,
        source=True if fmt != "text" else ["value"],
        limit=search.limit,
        offset=search.offset,
    )

    if fmt == "json":
        yield '{"response": {"Attribute": ['
    elif fmt == "csv":
        yield csv_line(CSV_COLUMNS)

    first = True
    for hits in pages:
        sources = [h["_source"] for h in hits]

        if fmt == "text":
            yield "".join(f"{s.get('value')}\n" for s in sources)
            continue

        events = (
            _mget_sources(
                client,
                EVENTS_INDEX,
                {s["event_uuid"] for s in sources if s.get("event_uuid")},
                EVENT_CONTEXT_FIELDS,
            )
            if needs_events
            else {}
        )

        if fmt == "csv":
            objects = _mget_sources(
                client,
                OBJECTS_INDEX,
                {s["object_uuid"] for s in sources if s.get("object_uuid")},
                ["name", "meta_category"],
            )
            yield "".join(
                csv_line(
                    _attribute_csv_row(
                        s,
                        events.get(s.get("event_uuid")),
                        objects.get(s.get("object_uuid")),
                    )
                )
                for s in sources
            )
            continue

        chunk = []
        for s in sources:
            attribute = _attribute_to_misp(
                s,
                events.get(s.get("event_uuid")),
                include_event_tags,
                include_context,
            )
            chunk.append(("" if first else ",") + json.dumps(attribute, default=str))
            first = False
        yield "".join(chunk)

    if fmt == "json":
        yield "]}}"


def stream_events(search: PreparedSearch) -> Iterator[str]:
    client = search.client
    params = search.params
    metadata = _parse_flag(params, "metadata")
    with_attachments = _parse_flag(params, "withattachments")

    pages = iter_pages(
        client,
        EVENTS_INDEX,
        search.query,
        source=True,
        limit=search.limit,
        offset=search.offset,
    )

    yield '{"response": ['
    first = True
    for hits in pages:
        chunk = []
        for hit in hits:
            source = hit["_source"]
            if metadata:
                source["attributes"] = []
                source["objects"] = []
                event = event_schemas.Event.model_validate(source)
            else:
                event = events_repository.get_event_from_opensearch(
                    source["uuid"], full=True
                )
                if event is None:
                    continue
            payload = event.to_misp_format(include_attachments=with_attachments)
            payload["Event"]["id"] = _event_id(source, str(source.get("uuid")))
            payload["Event"]["org_id"] = _str_or_none(source.get("org_id"))
            payload["Event"]["orgc_id"] = _str_or_none(source.get("orgc_id"))
            chunk.append(("" if first else ",") + json.dumps(payload, default=str))
            first = False
        yield "".join(chunk)
    yield "]}"
