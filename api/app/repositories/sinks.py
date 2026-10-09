"""Outbound sinks: CRUD, dispatch on publish, and delivery.

Publishing an event enqueues one ``deliver_to_sink`` task per enabled sink on
the dedicated ``sinks`` queue, so a slow or unreachable SIEM never holds up
the workers that ingest and correlate. Each task pages through the event's
attributes, keeps those the sink's filters select, and sends them in batches.
Delivery is at-least-once: a retry after a partial failure resends the
batches that had already gone through.
"""

import fnmatch
import logging
from datetime import datetime, timezone
from typing import Iterator, Optional

from sqlalchemy.orm import Session

from app.models import sink as sink_models
from app.repositories import stream_exports
from app.schemas import sink as sink_schemas
from app.services.opensearch import get_opensearch_client
from app.services.sinks import formatters
from app.services.sinks.transports import SinkDeliveryError, open_transport

logger = logging.getLogger(__name__)

SINKS_QUEUE = "sinks"
# Attributes per request/frame batch.
BATCH_SIZE = 500


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ── CRUD ──────────────────────────────────────────────────────────────────


def get_sinks(db: Session) -> list[sink_models.Sink]:
    return db.query(sink_models.Sink).order_by(sink_models.Sink.name.asc()).all()


def get_sink(db: Session, sink_id: int) -> Optional[sink_models.Sink]:
    return db.query(sink_models.Sink).filter(sink_models.Sink.id == sink_id).first()


def create_sink(db: Session, sink: sink_schemas.SinkCreate) -> sink_models.Sink:
    now = _now()
    db_sink = sink_models.Sink(
        name=sink.name,
        type=sink.type,
        enabled=sink.enabled,
        config=sink.config,
        filters=sink.filters.model_dump(),
        created_at=now,
        updated_at=now,
    )
    db.add(db_sink)
    db.commit()
    db.refresh(db_sink)
    return db_sink


# Everything that decides who can read a secret in transit: where it goes,
# and how that connection is authenticated. A stored secret is only reused
# while all of these stay as they were; turning verification off or swapping
# the CA would expose it as surely as a new host.
SECRET_BINDING_FIELDS = ("url", "host", "port", "tls", "verify_tls", "ca_cert")


class SecretRequired(ValueError):
    """The connection settings changed but the secret was not re-entered."""


def _binding(sink_type: str, config: dict) -> dict:
    """The secret-binding settings, with model defaults for omitted ones."""
    fields = sink_schemas.CONFIG_MODELS[sink_type].model_fields
    return {
        name: config.get(name, fields[name].default)
        for name in SECRET_BINDING_FIELDS
        if name in fields
    }


def _merge_secrets(sink_type: str, stored: dict, incoming: dict) -> dict:
    """Keep stored secrets the client sent back masked (or left out).

    Only while the connection settings stay the same: otherwise anyone allowed
    to edit a sink could point it at their own server (or drop TLS
    verification, or swap in their own CA), send the mask back and receive the
    stored token. Changing them needs the secret re-entered.
    """
    merged = dict(incoming)
    unchanged = _binding(sink_type, merged) == _binding(sink_type, stored)
    for field in sink_schemas.SECRET_FIELDS.get(sink_type, ()):
        if merged.get(field) in (None, sink_schemas.SECRET_MASK) and stored.get(field):
            if not unchanged:
                raise SecretRequired(
                    f"the connection settings changed: re-enter {field} to keep using it"
                )
            merged[field] = stored[field]
    return merged


def update_sink(
    db: Session, db_sink: sink_models.Sink, payload: sink_schemas.SinkUpdate
) -> sink_models.Sink:
    if payload.name is not None:
        db_sink.name = payload.name
    if payload.enabled is not None:
        db_sink.enabled = payload.enabled
    if payload.config is not None:
        db_sink.config = sink_schemas.validate_config(
            db_sink.type,
            _merge_secrets(db_sink.type, db_sink.config or {}, payload.config),
        )
    if payload.filters is not None:
        db_sink.filters = payload.filters.model_dump()
    db_sink.updated_at = _now()
    db.commit()
    db.refresh(db_sink)
    return db_sink


def delete_sink(db: Session, db_sink: sink_models.Sink) -> None:
    db.delete(db_sink)
    db.commit()


# ── Dispatch ──────────────────────────────────────────────────────────────


def dispatch_published_event(db: Session, event_uuid: str) -> int:
    """Queue a delivery of ``event_uuid`` to every enabled sink."""
    from app.worker import tasks

    sink_ids = [
        sink_id
        for (sink_id,) in db.query(sink_models.Sink.id)
        .filter(sink_models.Sink.enabled.is_(True))
        .all()
    ]
    for sink_id in sink_ids:
        tasks.deliver_to_sink.apply_async((sink_id, event_uuid), queue=SINKS_QUEUE)
    return len(sink_ids)


# ── Delivery ──────────────────────────────────────────────────────────────


def _matches(patterns: list[str], tags: list[str]) -> bool:
    return any(fnmatch.fnmatchcase(tag, p) for p in patterns for tag in tags)


def select_records(attributes: list[dict], event: dict, filters: dict) -> list[dict]:
    """The records a sink's tag filters keep (type/to_ids are done in the query)."""
    include = filters.get("tags") or []
    exclude = filters.get("exclude_tags") or []
    records = []
    for attribute in attributes:
        record = formatters.build_record(attribute, event)
        tags = formatters.all_tags(record)
        if include and not _matches(include, tags):
            continue
        if exclude and _matches(exclude, tags):
            continue
        records.append(record)
    return records


def _attribute_query(event_uuid: str, filters: dict) -> dict:
    query: list = [{"term": {"event_uuid": event_uuid}}]
    if filters.get("to_ids_only", True):
        query.append({"term": {"to_ids": True}})
    if filters.get("types"):
        query.append({"terms": {"type.keyword": filters["types"]}})
    return {"bool": {"filter": query, "must_not": [{"term": {"deleted": True}}]}}


def _iter_attribute_batches(event_uuid: str, filters: dict) -> Iterator[list[dict]]:
    client = get_opensearch_client()
    for hits in stream_exports.iter_pit_pages(
        client, "misp-attributes", _attribute_query(event_uuid, filters)
    ):
        yield [hit["_source"] for hit in hits]


def _get_event(event_uuid: str) -> Optional[dict]:
    response = get_opensearch_client().get(
        index="misp-events", id=event_uuid, ignore=[404]
    )
    return response.get("_source") if response.get("found") else None


def deliver_event(sink: sink_models.Sink, event_uuid: str) -> int:
    """Send the attributes of ``event_uuid`` that ``sink`` selects.

    Returns how many were sent; raises SinkDeliveryError when the sink
    can't be reached or rejects a batch.
    """
    event = _get_event(event_uuid)
    if event is None or event.get("deleted"):
        logger.info("sink %s: event %s is gone, nothing to send", sink.id, event_uuid)
        return 0

    filters = sink.filters or {}
    # Event tags apply to every attribute, so an excluded event is skipped
    # without reading any.
    event_tags = formatters.tag_names(event.get("tags"))
    if filters.get("exclude_tags") and _matches(filters["exclude_tags"], event_tags):
        return 0

    transport = open_transport(sink.type, sink.config)
    sent = 0
    try:
        pending: list[dict] = []
        for attributes in _iter_attribute_batches(event_uuid, filters):
            pending.extend(select_records(attributes, event, filters))
            while len(pending) >= BATCH_SIZE:
                transport.send(pending[:BATCH_SIZE])
                sent += BATCH_SIZE
                pending = pending[BATCH_SIZE:]
        if pending:
            transport.send(pending)
            sent += len(pending)
    finally:
        transport.close()
    return sent


def record_success(db: Session, sink_id: int, delivered: int) -> None:
    now = _now()
    db.query(sink_models.Sink).filter(sink_models.Sink.id == sink_id).update(
        {
            sink_models.Sink.last_attempt_at: now,
            sink_models.Sink.last_success_at: now,
            sink_models.Sink.delivered_count: sink_models.Sink.delivered_count
            + delivered,
        },
        synchronize_session=False,
    )
    db.commit()


def record_failure(db: Session, sink_id: int, error: str, final: bool) -> None:
    """Keep the error visible; count the delivery as failed once retries end."""
    now = _now()
    values = {
        sink_models.Sink.last_attempt_at: now,
        sink_models.Sink.last_error: error[:2000],
        sink_models.Sink.last_error_at: now,
    }
    if final:
        values[sink_models.Sink.failed_count] = sink_models.Sink.failed_count + 1
    db.query(sink_models.Sink).filter(sink_models.Sink.id == sink_id).update(
        values, synchronize_session=False
    )
    db.commit()


# ── Test ──────────────────────────────────────────────────────────────────

TEST_RECORD_ATTRIBUTE = {
    "uuid": "00000000-0000-4000-8000-000000000000",
    "type": "ip-dst",
    "category": "Network activity",
    "value": "192.0.2.1",
    "to_ids": True,
    "comment": "misp-workbench sink test message",
    "tags": [{"name": "misp-workbench:test"}],
}
TEST_RECORD_EVENT = {
    "uuid": "00000000-0000-4000-8000-000000000001",
    "info": "misp-workbench sink test",
    "threat_level": 4,
    "tags": [],
}


def send_test(sink: sink_models.Sink) -> sink_schemas.SinkTestResult:
    """Send one synthetic indicator (192.0.2.1, TEST-NET-1) to the sink."""
    record = formatters.build_record(TEST_RECORD_ATTRIBUTE, TEST_RECORD_EVENT)
    transport = open_transport(sink.type, sink.config)
    try:
        transport.send([record])
    except SinkDeliveryError as error:
        return sink_schemas.SinkTestResult(ok=False, error=str(error))
    finally:
        transport.close()
    return sink_schemas.SinkTestResult(ok=True)
