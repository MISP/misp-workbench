"""Streaming, incremental exports of attributes and events.

Backs ``GET /attributes/export`` and ``GET /events/export``. Results are paged
out of an OpenSearch point-in-time (PIT) snapshot with ``search_after`` and
written to the response as they arrive, so memory stays flat however many
documents match, and a long export sees one consistent view of the index:
writes landing mid-export can't shift pages, duplicating or skipping documents.

Incremental pulls (``since=``) key off ``updated_at``, which the attributes'
final ingest pipeline stamps on every write, partial updates included, so
edits, tag changes and soft deletes all move it. In a delta, soft-deleted
attributes are kept as tombstones (``deleted: true``) so consumers can prune
them. Hard deletes (force-deleting an event, retention) remove the document
and cannot show up in a delta; consumers should still do a periodic full pull.

``prepare_*`` validates the request and runs one cheap aggregation (match
count + newest ``updated_at``) that both answers conditional requests with a
304 and is reused as the ETag, all before the stream starts.
"""

import hashlib
import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from email.utils import format_datetime, parsedate_to_datetime
from typing import Any, Iterator, Optional

from fastapi import HTTPException, Response
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import StreamingResponse

from app.repositories.rest_search import (
    PAGE_SIZE,
    RestSearchError,
    csv_line,
    parse_timestamp,
)
from app.services.opensearch import get_opensearch_client
from app.services.redis import get_redis_client

logger = logging.getLogger(__name__)

# How long the snapshot outlives the last page request. Renewed on every page,
# so it only has to cover the time the client takes to read one page.
PIT_KEEP_ALIVE = "5m"

# A running export's claim on one of its user's slots, renewed on every page.
# Outlasts PIT_KEEP_ALIVE: a stream stalled past that has lost its snapshot
# anyway, and a slot whose stream never ran its cleanup (worker killed, client
# gone before the body started) frees itself once the lease runs out.
SLOT_LEASE_SECONDS = 6 * 60
RETRY_AFTER_SECONDS = "30"

ATTRIBUTES_INDEX = "misp-attributes"
EVENTS_INDEX = "misp-events"

ATTRIBUTE_FORMATS = ("json", "ndjson", "csv", "text", "cdb")
EVENT_FORMATS = ("json", "ndjson")
# Formats that can express a deletion, and so can carry a delta.
DELTA_FORMATS = ("json", "ndjson", "csv")

MEDIA_TYPES = {
    "json": "application/json",
    "ndjson": "application/x-ndjson",
    "csv": "text/csv",
    "text": "text/plain",
    "cdb": "text/plain",
}

CSV_COLUMNS = [
    "uuid",
    "event_uuid",
    "object_uuid",
    "category",
    "type",
    "value",
    "comment",
    "to_ids",
    "deleted",
    "timestamp",
    "updated_at",
    "tags",
]


class ExportError(RestSearchError):
    """Invalid export parameters; surfaced to the client as a 400."""


@dataclass
class PreparedExport:
    index: str
    format: str
    query: dict
    # Unix time the export was taken at: the `since` to send next time.
    # Taken before the first page is read, so a write landing mid-export is
    # picked up again by the next delta rather than lost.
    export_timestamp: int
    etag: str
    last_modified: Optional[datetime]
    client: Any = field(default=None, repr=False)

    @property
    def media_type(self) -> str:
        return MEDIA_TYPES[self.format]

    def headers(self) -> dict:
        headers = {
            "ETag": self.etag,
            "X-Export-Timestamp": str(self.export_timestamp),
            "Cache-Control": "no-cache",
        }
        if self.last_modified is not None:
            headers["Last-Modified"] = format_datetime(self.last_modified, usegmt=True)
        return headers

    def not_modified(
        self, if_none_match: Optional[str], if_modified_since: Optional[str]
    ) -> bool:
        # If-None-Match wins over If-Modified-Since when both are sent (RFC 9110).
        if if_none_match:
            tags = {t.strip() for t in if_none_match.split(",")}
            return self.etag in tags or "*" in tags
        if if_modified_since and self.last_modified is not None:
            try:
                since = parsedate_to_datetime(if_modified_since)
            except (TypeError, ValueError):
                return False
            # HTTP dates have second precision.
            return self.last_modified.replace(microsecond=0) <= since
        return False


def _validate_format(fmt: str, allowed: tuple) -> str:
    fmt = (fmt or "json").lower()
    if fmt not in allowed:
        raise ExportError(
            f"Unsupported format {fmt!r}; supported: {', '.join(allowed)}"
        )
    return fmt


def _base_query(query: Optional[str], default_field: str) -> dict:
    return {
        "query_string": {
            "query": query or "*",
            "default_field": default_field,
        }
    }


def _fingerprint(client, index: str, query: dict, request_key: str):
    """ETag and Last-Modified from the match count and newest write.

    Any write to a matching document moves ``updated_at``; a hard delete
    lowers the count. Either changes the ETag.
    """
    response = client.search(
        index=index,
        body={
            "size": 0,
            "track_total_hits": True,
            "query": query,
            "aggs": {"newest": {"max": {"field": "updated_at"}}},
        },
    )
    total = response["hits"]["total"]["value"]
    newest = (response.get("aggregations") or {}).get("newest", {}).get("value")
    last_modified = (
        datetime.fromtimestamp(newest / 1000, tz=timezone.utc)
        if newest is not None
        else None
    )
    digest = hashlib.sha256(
        f"{request_key}|{total}|{newest}".encode("utf-8")
    ).hexdigest()[:32]
    return f'"{digest}"', last_modified


def prepare_attribute_export(
    query: Optional[str],
    fmt: str,
    since: Optional[str] = None,
    include_deleted: bool = False,
    enforce_warninglist: bool = False,
) -> PreparedExport:
    fmt = _validate_format(fmt, ATTRIBUTE_FORMATS)
    export_timestamp = int(time.time())

    filters: list = []
    if since not in (None, ""):
        if fmt not in DELTA_FORMATS:
            raise ExportError(
                f"since= needs a format that can carry deletions "
                f"({', '.join(DELTA_FORMATS)}); {fmt!r} cannot"
            )
        since_ts = parse_timestamp(since, "since", now=export_timestamp)
        filters.append(
            {"range": {"updated_at": {"gte": since_ts, "format": "epoch_second"}}}
        )
        # Tombstones are the point of a delta.
        include_deleted = True
    if not include_deleted:
        filters.append({"term": {"deleted": False}})

    os_query = {"bool": {"must": [_base_query(query, "value")], "filter": filters}}
    # A full export leaves warninglisted attributes out. A delta keeps them, with
    # their warninglist_hits, so a consumer drops a value that became listed.
    if enforce_warninglist and since in (None, ""):
        from app.repositories.warninglists import WARNINGLISTED

        os_query["bool"]["must_not"] = [WARNINGLISTED]

    client = get_opensearch_client()
    request_key = json.dumps(
        [ATTRIBUTES_INDEX, query, fmt, since, include_deleted, enforce_warninglist]
    )
    etag, last_modified = _fingerprint(client, ATTRIBUTES_INDEX, os_query, request_key)
    return PreparedExport(
        index=ATTRIBUTES_INDEX,
        format=fmt,
        query=os_query,
        export_timestamp=export_timestamp,
        etag=etag,
        last_modified=last_modified,
        client=client,
    )


def prepare_event_export(
    query: Optional[str],
    fmt: str,
    include_deleted: bool = False,
) -> PreparedExport:
    fmt = _validate_format(fmt, EVENT_FORMATS)
    filters = [] if include_deleted else [{"term": {"deleted": False}}]
    os_query = {"bool": {"must": [_base_query(query, "info")], "filter": filters}}

    client = get_opensearch_client()
    request_key = json.dumps([EVENTS_INDEX, query, fmt, include_deleted])
    etag, last_modified = _fingerprint(client, EVENTS_INDEX, os_query, request_key)
    return PreparedExport(
        index=EVENTS_INDEX,
        format=fmt,
        query=os_query,
        export_timestamp=int(time.time()),
        etag=etag,
        last_modified=last_modified,
        client=client,
    )


def _single_line(value: Any) -> Optional[str]:
    """Line formats can't hold a newline; such values (text attributes) are skipped."""
    if value is None:
        return None
    value = str(value)
    if "\n" in value or "\r" in value:
        return None
    return value


def _cdb_line(source: dict) -> Optional[str]:
    """Wazuh CDB list entry, ``key:value``, with the attribute type as value.

    Keys containing ``:`` (IPv6, URLs) must be double-quoted; a key that itself
    contains a quote can't be represented and is skipped.
    """
    key = _single_line(source.get("value"))
    if not key or '"' in key:
        return None
    if ":" in key:
        key = f'"{key}"'
    return f"{key}:{source.get('type') or ''}\n"


def _csv_row(source: dict) -> list:
    return [
        source.get("uuid"),
        source.get("event_uuid"),
        source.get("object_uuid") or "",
        source.get("category"),
        source.get("type"),
        source.get("value"),
        source.get("comment") or "",
        1 if source.get("to_ids") else 0,
        1 if source.get("deleted") else 0,
        source.get("timestamp"),
        source.get("updated_at") or "",
        ",".join(t.get("name", "") for t in source.get("tags") or []),
    ]


class SnapshotUnavailable(Exception):
    """OpenSearch refused a PIT, typically because too many are open."""


def open_snapshot(client, index: str) -> str:
    """Open the PIT an export will read from.

    Done before the response starts, so a refusal (the cluster caps open PITs,
    ``point_in_time.max_open_contexts``) becomes a 503 rather than a 200 whose
    body stops before the first byte.
    """
    try:
        return client.create_pit(index=index, params={"keep_alive": PIT_KEEP_ALIVE})[
            "pit_id"
        ]
    except Exception as error:
        logger.warning("could not open export PIT on %s: %s", index, error)
        raise SnapshotUnavailable(str(error)) from error


# Drop expired leases, then claim a slot if one is free, atomically, so
# concurrent requests from the same user on different workers can't both take
# the last slot.
_ACQUIRE_SLOT = """
redis.call('ZREMRANGEBYSCORE', KEYS[1], '-inf', ARGV[1])
if redis.call('ZCARD', KEYS[1]) >= tonumber(ARGV[3]) then
    return 0
end
redis.call('ZADD', KEYS[1], ARGV[2], ARGV[4])
redis.call('EXPIRE', KEYS[1], ARGV[5])
return 1
"""


def _slots_key(user_id) -> str:
    return f"exports:active:{user_id}"


@dataclass
class ExportSlot:
    """One of a user's concurrent-export slots, held while a stream runs."""

    user_id: Any
    token: str

    def renew(self) -> None:
        try:
            get_redis_client().zadd(
                _slots_key(self.user_id),
                {self.token: time.time() + SLOT_LEASE_SECONDS},
                xx=True,
            )
        except Exception:
            logger.warning("could not renew export slot", exc_info=True)

    def release(self) -> None:
        try:
            get_redis_client().zrem(_slots_key(self.user_id), self.token)
        except Exception:
            # The lease runs out on its own.
            logger.warning("could not release export slot", exc_info=True)


class TooManyExports(Exception):
    """The user already runs as many exports as allowed."""


def acquire_slot(user_id, limit: int) -> Optional[ExportSlot]:
    """Claim a concurrent-export slot for ``user_id``.

    Returns None when the limit is disabled (``limit <= 0``) or Redis is
    unreachable: an outage of the limiter shouldn't take exports down with it.
    """
    if not limit or limit <= 0:
        return None
    token = uuid.uuid4().hex
    now = time.time()
    try:
        acquired = get_redis_client().eval(
            _ACQUIRE_SLOT,
            1,
            _slots_key(user_id),
            now,
            now + SLOT_LEASE_SECONDS,
            int(limit),
            token,
            SLOT_LEASE_SECONDS,
        )
    except Exception:
        logger.exception("export slot limiter unavailable; allowing the export")
        return None
    if not acquired:
        raise TooManyExports()
    return ExportSlot(user_id=user_id, token=token)


def iter_pit_pages(
    client,
    index: str,
    query: dict,
    source: Any = True,
    pit_id: Optional[str] = None,
) -> Iterator[list[dict]]:
    """Yield pages of hits from a point-in-time snapshot of ``index``.

    Takes ownership of ``pit_id`` (opening one if not given) and always closes
    it: on exhaustion, on error, and when the client disconnects mid-stream
    (closing the generator runs the ``finally``). A stream that never starts
    leaves its PIT to expire after ``PIT_KEEP_ALIVE``; a reader stalling longer
    than that between pages loses the snapshot and the stream ends early, which
    bounds how long one slow client can hold a context.
    """
    if pit_id is None:
        pit_id = open_snapshot(client, index)
    try:
        search_after = None
        while True:
            body = {
                "query": query,
                "_source": source,
                "size": PAGE_SIZE,
                # uuid is unique per document, so it alone orders pages.
                "sort": [{"uuid.keyword": "asc"}],
                "pit": {"id": pit_id, "keep_alive": PIT_KEEP_ALIVE},
            }
            if search_after:
                body["search_after"] = search_after
            # A PIT search names no index: the snapshot already pins it.
            response = client.search(body=body)
            # The id can change between requests; always continue with the latest.
            pit_id = response.get("pit_id", pit_id)
            hits = response["hits"]["hits"]
            if not hits:
                return
            yield hits
            if len(hits) < PAGE_SIZE:
                return
            search_after = hits[-1]["sort"]
    finally:
        try:
            client.delete_pit(body={"pit_id": [pit_id]})
        except Exception:
            # It expires on its own after PIT_KEEP_ALIVE; not worth failing for.
            logger.warning("could not delete export PIT on %s", index, exc_info=True)


def stream(
    export: PreparedExport,
    pit_id: Optional[str] = None,
    slot: Optional[ExportSlot] = None,
) -> Iterator[str]:
    try:
        yield from _stream(export, pit_id, slot)
    finally:
        if slot is not None:
            slot.release()


def _stream(
    export: PreparedExport, pit_id: Optional[str], slot: Optional[ExportSlot]
) -> Iterator[str]:
    fmt = export.format
    source: Any = ["value", "type"] if fmt in ("text", "cdb") else True
    pages = iter_pit_pages(
        export.client, export.index, export.query, source=source, pit_id=pit_id
    )

    if fmt == "json":
        yield "["
    elif fmt == "csv":
        yield csv_line(CSV_COLUMNS)

    first = True
    for hits in pages:
        if slot is not None:
            slot.renew()
        if fmt == "json":
            chunk = []
            for hit in hits:
                doc = {
                    "_index": hit["_index"],
                    "_id": hit["_id"],
                    "_source": hit["_source"],
                }
                chunk.append(("" if first else ",") + json.dumps(doc, default=str))
                first = False
            yield "".join(chunk)
        elif fmt == "ndjson":
            yield "".join(
                json.dumps(hit["_source"], default=str) + "\n" for hit in hits
            )
        elif fmt == "csv":
            yield "".join(csv_line(_csv_row(hit["_source"])) for hit in hits)
        elif fmt == "text":
            lines = (_single_line(hit["_source"].get("value")) for hit in hits)
            yield "".join(f"{line}\n" for line in lines if line)
        elif fmt == "cdb":
            lines = (_cdb_line(hit["_source"]) for hit in hits)
            yield "".join(line for line in lines if line)

    if fmt == "json":
        yield "]"


async def to_response(
    export: PreparedExport, request, user_id=None, max_concurrent: int = 0
) -> Response:
    """304 when the client's copy is current, else the streamed export.

    A 304 costs neither a slot nor a snapshot. Past ``max_concurrent``
    running exports for this user the answer is a 429; when OpenSearch won't
    open a snapshot, a 503. Both carry Retry-After and are decided before the
    response starts, so a client never gets a broken 200.
    """
    headers = export.headers()
    if export.not_modified(
        request.headers.get("if-none-match"),
        request.headers.get("if-modified-since"),
    ):
        return Response(status_code=304, headers=headers)

    try:
        slot = await run_in_threadpool(acquire_slot, user_id, max_concurrent)
    except TooManyExports:
        raise HTTPException(
            status_code=429,
            detail=(
                f"You already have {max_concurrent} exports running; "
                "wait for one to finish"
            ),
            headers={"Retry-After": RETRY_AFTER_SECONDS},
        )

    try:
        pit_id = await run_in_threadpool(open_snapshot, export.client, export.index)
    except SnapshotUnavailable:
        if slot is not None:
            slot.release()
        raise HTTPException(
            status_code=503,
            detail="Too many exports in progress, retry shortly",
            headers={"Retry-After": RETRY_AFTER_SECONDS},
        )
    return StreamingResponse(
        stream(export, pit_id, slot), media_type=export.media_type, headers=headers
    )
