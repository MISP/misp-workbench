"""Sending to sinks from code: notebooks (``mwlab``) and reactor scripts (``ctx``).

User code only ever names a sink. Its config and credentials stay server-side,
and delivery is queued on the dedicated ``sinks`` worker (with its retries
and status tracking) rather than done from the notebook kernel or the reactor
sandbox. Every send is permission-checked against the code's owner, limited
in size and rate, and written to the audit log.
"""

import logging
import time
import uuid
from dataclasses import dataclass
from typing import Optional, Union

from sqlalchemy.orm import Session

from app.auth.utils import role_has_scope
from app.models import sink as sink_models
from app.models import user as user_models
from app.repositories import sinks as sinks_repository
from app.services import audit
from app.services.redis import get_redis_client
from app.services.runtime_settings import RuntimeSettings

logger = logging.getLogger(__name__)

SEND_SCOPE = "sinks:send"
# Items (attributes or records) one call may send.
MAX_ITEMS_PER_SEND = 10_000
# Items per queued delivery task, so no broker message gets large.
ITEMS_PER_TASK = 1_000
DEFAULT_SENDS_PER_MINUTE = 30
# A record's fields, and how long a string field may be.
RECORD_FIELDS = ("value", "type", "category", "comment", "to_ids", "tags")
MAX_FIELD_LENGTH = 4096


class SinkSendError(Exception):
    """Base class: the message is safe to show to the code's author."""


class SinkSendPermissionDenied(SinkSendError):
    pass


class SinkSendRateLimited(SinkSendError):
    pass


@dataclass
class SendResult:
    sink: str
    mode: str
    items: int
    tasks: list

    def as_dict(self) -> dict:
        return {
            "sink": self.sink,
            "mode": self.mode,
            "queued": self.items,
            "task_ids": self.tasks,
        }


def _require_scope(db: Session, user_id: int) -> None:
    user = db.query(user_models.User).filter(user_models.User.id == user_id).first()
    if user is None or user.disabled:
        raise SinkSendPermissionDenied("owner not found or disabled")
    if not role_has_scope(list(user.role.scopes or []), SEND_SCOPE):
        raise SinkSendPermissionDenied(
            f"sending to sinks needs the {SEND_SCOPE} scope on the owner's role"
        )


def visible_sinks(db: Session, user_id: int) -> list[dict]:
    """Sinks code can name: id, name, type, enabled. Never config or secrets."""
    _require_scope(db, user_id)
    return [
        {"id": s.id, "name": s.name, "type": s.type, "enabled": s.enabled}
        for s in sinks_repository.get_sinks(db)
    ]


def _resolve_sink(db: Session, sink: Union[int, str]) -> sink_models.Sink:
    query = db.query(sink_models.Sink)
    if isinstance(sink, int) or (isinstance(sink, str) and sink.isdigit()):
        found = query.filter(sink_models.Sink.id == int(sink)).first()
    else:
        found = query.filter(sink_models.Sink.name == str(sink)).first()
    if found is None:
        raise SinkSendError(f"no sink {sink!r}")
    if not found.enabled:
        raise SinkSendError(f"sink {found.name!r} is disabled")
    return found


def _check_rate(db: Session, user_id: int) -> None:
    limit = int(
        RuntimeSettings(db).get_value(
            "sinks.sends_per_minute", default=DEFAULT_SENDS_PER_MINUTE
        )
        or 0
    )
    if limit <= 0:
        return
    key = f"sinks:send:rate:{user_id}:{int(time.time() // 60)}"
    try:
        redis = get_redis_client()
        count = redis.incr(key)
        if count == 1:
            redis.expire(key, 120)
    except Exception:
        # The limiter is best-effort: an outage of Redis shouldn't block sends.
        logger.exception("sink send rate limiter unavailable")
        return
    if count > limit:
        raise SinkSendRateLimited(
            f"at most {limit} sends per minute; try again shortly"
        )


def _canonical_uuid(value, what: str) -> str:
    """A UUID in canonical form, or SinkSendError.

    Caller-supplied identifiers end up in task arguments, worker log lines and
    the audit log: only well-formed UUIDs get that far, so a crafted string
    (newlines included) can't forge log entries or reach OpenSearch as an id.
    """
    try:
        return str(uuid.UUID(str(value)))
    except (ValueError, AttributeError, TypeError):
        raise SinkSendError(f"{what} must be a UUID") from None


def _attribute_uuids(attributes: list) -> list[str]:
    uuids = []
    for item in attributes:
        value = item.get("uuid") if isinstance(item, dict) else item
        if not value:
            raise SinkSendError("attributes must be uuids or dicts with a uuid")
        uuids.append(_canonical_uuid(value, "attribute uuid"))
    return list(dict.fromkeys(uuids))


def _clean_record(item) -> dict:
    """Shape a caller-supplied record like a delivery record, nothing more."""
    if not isinstance(item, dict):
        raise SinkSendError("records must be dicts")
    value, type_ = item.get("value"), item.get("type")
    if (
        not isinstance(value, str)
        or not value
        or not isinstance(type_, str)
        or not type_
    ):
        raise SinkSendError("every record needs a non-empty string value and type")
    record = {
        "uuid": None,
        "type": type_[:MAX_FIELD_LENGTH],
        "category": str(item.get("category") or "")[:MAX_FIELD_LENGTH] or None,
        "value": value[:MAX_FIELD_LENGTH],
        "to_ids": bool(item.get("to_ids", True)),
        "comment": str(item.get("comment") or "")[:MAX_FIELD_LENGTH],
        "timestamp": None,
        "first_seen": None,
        "last_seen": None,
        "object_uuid": None,
        "object_relation": None,
        "tags": [str(t)[:MAX_FIELD_LENGTH] for t in (item.get("tags") or [])][:50],
        "event": {
            "uuid": None,
            "info": None,
            "date": None,
            "threat_level_id": None,
            "analysis": None,
            "publish_timestamp": None,
            "org": None,
            "tags": [],
        },
    }
    unknown = set(item) - set(RECORD_FIELDS)
    if unknown:
        raise SinkSendError(
            f"unknown record fields {sorted(unknown)}; allowed: {', '.join(RECORD_FIELDS)}"
        )
    return record


def send_to_sink(
    db: Session,
    *,
    user_id: int,
    sink: Union[int, str],
    attributes: Optional[list] = None,
    event_uuid: Optional[str] = None,
    records: Optional[list] = None,
    apply_filters: bool = True,
    actor_type: str,
    actor_credential_id: Optional[int] = None,
    audit_metadata: Optional[dict] = None,
) -> dict:
    """Queue a delivery to ``sink`` on the owner's behalf.

    Exactly one of ``attributes`` (uuids or attribute dicts), ``event_uuid``
    or ``records`` (dicts with at least ``value`` and ``type``).
    ``apply_filters=False`` skips the sink's selection filters, never its
    exclusions (see ``sinks_repository.effective_filters``).
    """
    from app.worker import tasks

    given = [x is not None for x in (attributes, event_uuid, records)]
    if sum(given) != 1:
        raise SinkSendError("pass exactly one of attributes, event_uuid or records")

    # Validate the whole request first: a rejected one mustn't use up the
    # caller's rate budget, nor make us clean 10,000 records to refuse them.
    if event_uuid is not None:
        mode, event_uuid = "event", _canonical_uuid(event_uuid, "event_uuid")
        payload: list = []
        items = 1
    else:
        mode = "attributes" if attributes is not None else "records"
        raw = list(attributes if attributes is not None else records)
        if len(raw) > MAX_ITEMS_PER_SEND:
            raise SinkSendError(
                f"at most {MAX_ITEMS_PER_SEND} {mode} per send, got {len(raw)}"
            )
        payload = (
            _attribute_uuids(raw)
            if mode == "attributes"
            else [_clean_record(r) for r in raw]
        )
        items = len(payload)

    _require_scope(db, user_id)
    db_sink = _resolve_sink(db, sink)
    _check_rate(db, user_id)

    if mode == "event":
        result = tasks.deliver_to_sink.apply_async(
            (db_sink.id, event_uuid),
            {"apply_filters": apply_filters},
            queue=sinks_repository.SINKS_QUEUE,
        )
        task_ids = [result.id]
    else:
        task_ids = []
        for start in range(0, items, ITEMS_PER_TASK):
            result = tasks.deliver_items_to_sink.apply_async(
                (db_sink.id, mode, payload[start : start + ITEMS_PER_TASK]),
                {"apply_filters": apply_filters},
                queue=sinks_repository.SINKS_QUEUE,
            )
            task_ids.append(result.id)

    audit.record(
        db,
        action="sink.send",
        resource_type="sink",
        resource_id=db_sink.id,
        actor_user_id=user_id,
        actor_type=actor_type,
        actor_credential_id=actor_credential_id,
        metadata={
            "sink": db_sink.name,
            "mode": mode,
            "items": items,
            "event_uuid": event_uuid,
            "apply_filters": apply_filters,
            **(audit_metadata or {}),
        },
    )
    db.commit()
    return SendResult(db_sink.name, mode, items, task_ids).as_dict()
