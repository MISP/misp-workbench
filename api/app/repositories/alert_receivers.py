"""Inbound alert webhooks: SIEMs and SOARs post their alerts, in their own
shape, and a receiver's JMESPath mapping reads the values they hit out of
them. Those become sightings, the organisation's, through the same bulk path
as POST /sightings: scoring, hit-rate expiry and false-positive feedback
learn from them without any code on the sender's side.

A request is all or nothing: one record the mapping can't read refuses the
whole request, so a sender retrying it doesn't report the others twice.
"""

import hashlib
import ipaddress
import json
import logging
import math
import secrets
from datetime import datetime, timezone
from functools import lru_cache
from typing import Any, Optional

import jmespath
from jmespath import exceptions as jmespath_exceptions
from jmespath import functions as jmespath_functions
from sqlalchemy.orm import Session

from app.models import alert_receiver as alert_receiver_models
from app.repositories import sightings as sightings_repository
from app.schemas import alert_receiver as alert_receiver_schemas

logger = logging.getLogger(__name__)

TOKEN_PREFIX = "awh_"
# The largest body taken. A SIEM batching alerts stays well under it.
MAX_BODY = 1024 * 1024
# The last body is kept, cut to this, to try the mapping on.
LAST_PAYLOAD_MAX = 64 * 1024
# Longer values are no indicator, or a mapping picking up a whole message.
MAX_VALUE_LENGTH = 2048
# Attributes a request may name by uuid or id, looked up in one request.
MAX_ATTRIBUTE_REFS = 1000
# Values past the keyword limit are each a phrase query: few a request.
MAX_LONG_VALUES = 200
# Senders' clocks drift; a sighting further in the future is taken as now,
# so a wrong clock can't keep an indicator alive past its hit-rate expiry.
FUTURE_SKEW_SECONDS = 300

# Sighting types by what senders call them (MISP's numbers included).
SIGHTING_TYPES = {
    **sightings_repository.MISP_SIGHTING_TYPES,
    "false_positive": sightings_repository.FALSE_POSITIVE,
    "falsepositive": sightings_repository.FALSE_POSITIVE,
    "fp": sightings_repository.FALSE_POSITIVE,
}


# ── Presets ───────────────────────────────────────────────────────────────

# Indicator-bearing fields in Elastic Common Schema, nested or flattened.
_ECS_FIELDS = [
    "source.ip",
    "destination.ip",
    "url.full",
    "url.domain",
    "dns.question.name",
    "file.hash.md5",
    "file.hash.sha1",
    "file.hash.sha256",
]

PRESETS: dict[str, dict] = {
    "generic": {
        "name": "Generic JSON",
        "mapping": {
            "records": "@",
            "values": "[value, values]",
            "type": "type",
            "source": "source",
            "timestamp": "timestamp",
            "attribute_uuid": "uuid",
        },
        "setup": (
            "POST JSON to the URL: an object, or an array of them, each with "
            "value (or values), and optionally type (positive, false-positive "
            "or MISP's 0, 1, 2), source and timestamp. Or post your own shape "
            "and change the mapping."
        ),
        "sample": [
            {
                "values": ["185.220.101.42", "invoice-portal.test"],
                "source": "proxy-01",
                "timestamp": 1791969120,
            },
            {"value": "evil.example", "type": "false-positive", "source": "soc"},
        ],
    },
    "splunk": {
        "name": "Splunk webhook alert action",
        "mapping": {
            "records": "@",
            "values": (
                "result.[src_ip, dest_ip, src, dest, url, domain, query, "
                "file_hash, md5, sha1, sha256]"
            ),
            "source": "search_name",
            "timestamp": "result._time",
        },
        "setup": (
            "In the saved search's alert actions, add Webhook with this URL. "
            "Splunk posts the first result row only: set Trigger to For each "
            "result to report every row. Name the fields holding indicators "
            "like the mapping does (src_ip, dest_ip, url, domain, file_hash), "
            "or change the mapping to yours."
        ),
        "sample": {
            "sid": "scheduler__admin__search__RMD5c2d3e4f5a6b7_at_1791969120_42",
            "search_name": "Outbound to known C2",
            "app": "search",
            "owner": "admin",
            "results_link": "https://splunk.example:8000/app/search/@go?sid=scheduler__admin__search__RMD5c2d3e4f5a6b7_at_1791969120_42",
            "result": {
                "_time": "1791969120",
                "src_ip": "10.1.2.3",
                "dest_ip": "185.220.101.42",
                "dest_port": "443",
                "count": "3",
            },
        },
    },
    "elastic": {
        "name": "Elastic / Kibana rule action",
        "mapping": {
            "records": "alerts",
            "values": "["
            + ", ".join(_ECS_FIELDS + [f'"{field}"' for field in _ECS_FIELDS])
            + "]",
            "source": "root().rule",
            "timestamp": '"@timestamp"',
        },
        "setup": (
            "Create a Webhook connector (POST, this URL, header Content-Type: "
            "application/json) and add it to the rule's actions with the body "
            '{"rule": "{{rule.name}}", "alerts": {{context.alerts}}}. The '
            "alerts' ECS fields are read: source.ip, destination.ip, url.full, "
            "url.domain, dns.question.name and file.hash.*."
        ),
        "sample": {
            "rule": "Connection to known C2",
            "alerts": [
                {
                    "@timestamp": "2026-10-14T09:12:00.000Z",
                    "source": {"ip": "10.1.2.3"},
                    "destination": {"ip": "185.220.101.42", "port": 443},
                },
                {
                    "@timestamp": "2026-10-14T09:13:30.000Z",
                    "url.full": "http://invoice-portal.test/download/48812",
                },
            ],
        },
    },
    "graylog": {
        "name": "Graylog HTTP notification",
        "mapping": {
            "records": "@",
            "values": (
                "[event.fields.*, event.group_by_fields.*, event.key_tuple, "
                "backlog[].fields.[src_ip, dst_ip, source_ip, destination_ip, "
                "url, domain, file_hash]]"
            ),
            "source": "event_definition_title",
            "timestamp": "event.timestamp",
        },
        "setup": (
            "Under Alerts → Notifications, create an HTTP Notification with "
            "this URL and add it to the event definition. The event's custom "
            "fields, its group-by fields and key are read, and the backlog's "
            "indicator fields when you include a backlog."
        ),
        "sample": {
            "event_definition_id": "6530a1b2c3d4e5f6a7b8c9d0",
            "event_definition_type": "aggregation-v1",
            "event_definition_title": "Outbound to known C2",
            "event_definition_description": "",
            "job_definition_id": "6530a1b2c3d4e5f6a7b8c9d1",
            "job_trigger_id": "6530a1b2c3d4e5f6a7b8c9d2",
            "event": {
                "id": "01HC9Z6V5W4X3Y2Z1A0B9C8D7E",
                "event_definition_type": "aggregation-v1",
                "event_definition_id": "6530a1b2c3d4e5f6a7b8c9d0",
                "timestamp": "2026-10-14T09:12:00.000Z",
                "timestamp_processing": "2026-10-14T09:12:03.000Z",
                "message": "Outbound to known C2",
                "source": "graylog",
                "key_tuple": ["185.220.101.42"],
                "key": "185.220.101.42",
                "priority": 2,
                "alert": True,
                "fields": {"src_ip": "10.1.2.3"},
                "group_by_fields": {"dst_ip": "185.220.101.42"},
            },
            "backlog": [],
        },
    },
    "wazuh": {
        "name": "Wazuh integration",
        "mapping": {
            "records": "@",
            "values": (
                "[(all_fields || @).data.[srcip, dstip, src_ip, dst_ip, url, "
                "hostname, md5, sha1, sha256], (all_fields || @).syscheck"
                ".[md5_after, sha1_after, sha256_after]]"
            ),
            "source": "(all_fields || @).rule.description",
            "timestamp": "(all_fields || @).timestamp",
        },
        "setup": (
            "In ossec.conf, add an integration posting JSON alerts to this "
            "URL: <integration><name>shuffle</name><hook_url>URL</hook_url>"
            "<level>10</level><alert_format>json</alert_format></integration>"
            ", then restart the manager. The alert's data and syscheck "
            "indicator fields are read, whether the alert is posted as it is "
            "or wrapped in all_fields."
        ),
        "sample": {
            "severity": 2,
            "pretext": "WAZUH Alert",
            "title": "Connection to a known C2 address",
            "rule_id": "100200",
            "timestamp": "2026-10-14T09:12:00.123+0000",
            "id": "1791969120.4242",
            "all_fields": {
                "timestamp": "2026-10-14T09:12:00.123+0000",
                "rule": {
                    "level": 10,
                    "description": "Connection to a known C2 address",
                    "id": "100200",
                },
                "agent": {"id": "001", "name": "web-01"},
                "data": {"srcip": "10.1.2.3", "dstip": "185.220.101.42"},
            },
        },
    },
    "sentinel": {
        "name": "Microsoft Sentinel playbook",
        "mapping": {
            "records": "@",
            "values": ("entities[].properties.[address, url, hashValue, domainName]"),
            "type": (
                "classification == 'FalsePositive' && 'false-positive' " "|| 'positive'"
            ),
            "source": "incident",
        },
        "setup": (
            "In a playbook with the Microsoft Sentinel incident trigger, add "
            "an HTTP action: POST to this URL, with the body "
            "{\"incident\": \"@{triggerBody()?['object']?['properties']?['title']}\", "
            "\"classification\": \"@{triggerBody()?['object']?['properties']?['classification']}\", "
            "\"entities\": @{triggerBody()?['object']?['properties']?['relatedEntities']}}. "
            "IP, URL, file hash and DNS entities are read; an incident closed "
            "as FalsePositive reports false positives."
        ),
        "sample": {
            "incident": "Connection to known C2",
            "classification": "TruePositive",
            "entities": [
                {"kind": "Ip", "properties": {"address": "185.220.101.42"}},
                {
                    "kind": "Url",
                    "properties": {"url": "http://invoice-portal.test/download/48812"},
                },
                {"kind": "Host", "properties": {"hostName": "web-01"}},
            ],
        },
    },
}


def presets() -> list[dict]:
    return [{"preset": key, **preset} for key, preset in PRESETS.items()]


def preset_mapping(preset: str) -> dict:
    if preset not in PRESETS:
        raise ValueError(f"unknown preset {preset!r}: one of {', '.join(PRESETS)}")
    return dict(PRESETS[preset]["mapping"])


# ── Mapping ───────────────────────────────────────────────────────────────


class MappingError(ValueError):
    pass


@lru_cache(maxsize=512)
def compile_expression(expression: str):
    try:
        return jmespath.compile(expression)
    except jmespath_exceptions.JMESPathError as error:
        raise ValueError(f"{expression!r} is no JMESPath expression: {error}")


class _Functions(jmespath_functions.Functions):
    """root(): the whole body, from inside a record."""

    def __init__(self, root: Any):
        super().__init__()
        self._root = root

    @jmespath_functions.signature()
    def _func_root(self):
        return self._root


def _search(expression: Optional[str], data: Any, options, field: str) -> Any:
    if not expression:
        return None
    try:
        return compile_expression(expression).search(data, options)
    except jmespath_exceptions.JMESPathError as error:
        raise MappingError(f"{field}: {error}")
    except RecursionError:
        raise MappingError(f"{field}: the body is nested too deep")


def _flatten(value: Any) -> list[str]:
    """The strings in a value, however nested: numbers count, objects and
    booleans don't. Iterative, so no nesting runs out of stack."""
    texts: list[str] = []
    stack = [value]
    while stack:
        item = stack.pop()
        if item is None or isinstance(item, (bool, dict)):
            continue
        if isinstance(item, list):
            stack.extend(reversed(item))
            continue
        if isinstance(item, float) and item.is_integer():
            item = int(item)
        text = str(item).strip()
        if text and len(text) <= MAX_VALUE_LENGTH:
            texts.append(text)
    return texts


def sighting_type(value: Any) -> str:
    if value is None or value == "":
        return "positive"
    key = str(value).strip().lower().replace(" ", "-")
    if key in SIGHTING_TYPES:
        return SIGHTING_TYPES[key]
    raise MappingError(
        f"type {value!r} is none of positive, false-positive, expiration "
        "(or MISP's 0, 1, 2)"
    )


def timestamp_of(value: Any, now: float) -> float:
    """Epoch seconds from seconds, milliseconds, microseconds or ISO 8601;
    no later than a few minutes from now."""
    if value is None or value == "":
        return now
    seconds: Optional[float] = None
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        seconds = float(value)
    elif isinstance(value, str):
        text = value.strip()
        try:
            seconds = float(text)
        except ValueError:
            try:
                parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
            except ValueError:
                raise MappingError(f"timestamp {value!r} is no date")
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            seconds = parsed.timestamp()
    if seconds is None or not math.isfinite(seconds) or seconds < 0:
        raise MappingError(f"timestamp {value!r} is no date")
    # Milliseconds, or microseconds, since the epoch.
    while seconds > 1e11:
        seconds /= 1000
    return min(seconds, now + FUTURE_SKEW_SECONDS)


def map_payload(
    payload: Any, mapping: dict, default_source: str, now: Optional[float] = None
) -> tuple[int, list[dict]]:
    """The records in a body, and the sightings they report: value (or
    attribute_uuid), type, source and timestamp. Raises MappingError."""
    now = now if now is not None else datetime.now(timezone.utc).timestamp()
    options = jmespath.Options(custom_functions=_Functions(payload))
    found = _search(mapping.get("records") or "@", payload, options, "records")
    if found is None:
        records: list = []
    elif isinstance(found, list):
        records = found
    else:
        records = [found]

    sightings: list[dict] = []
    for index, record in enumerate(records):
        where = f"record {index + 1}" if len(records) > 1 else "the alert"
        try:
            kind = sighting_type(_search(mapping.get("type"), record, options, "type"))
            source = _flatten(_search(mapping.get("source"), record, options, "source"))
            moment = timestamp_of(
                _search(mapping.get("timestamp"), record, options, "timestamp"), now
            )
            uuid = _flatten(
                _search(
                    mapping.get("attribute_uuid"), record, options, "attribute_uuid"
                )
            )
            values = (
                []
                if uuid
                else _flatten(_search(mapping.get("values"), record, options, "values"))
            )
        except MappingError as error:
            raise MappingError(f"{where}: {error}")
        base = {
            "type": kind,
            "source": (source[0] if source else default_source)[:255],
            "timestamp": moment,
        }
        if uuid:
            sightings.append({**base, "value": None, "attribute_uuid": uuid[0]})
            continue
        for value in dict.fromkeys(values):
            sightings.append({**base, "value": value, "attribute_uuid": None})
    return len(records), sightings


def check_limits(sightings: list[dict]) -> None:
    """Refuse a request whose lookups would cost more than an alert's worth:
    raises sightings_repository.TooManySightings."""
    limit = sightings_repository.MAX_SIGHTINGS_PER_REQUEST
    if len(sightings) > limit:
        raise sightings_repository.TooManySightings(
            f"{len(sightings)} sightings: at most {limit} a request"
        )
    refs = {s["attribute_uuid"] for s in sightings if s.get("attribute_uuid")}
    if len(refs) > MAX_ATTRIBUTE_REFS:
        raise sightings_repository.TooManySightings(
            f"{len(refs)} attributes named: at most {MAX_ATTRIBUTE_REFS} a request"
        )
    long = {
        s["value"]
        for s in sightings
        if s.get("value")
        and len(s["value"]) > sightings_repository.KEYWORD_IGNORE_ABOVE
    }
    if len(long) > MAX_LONG_VALUES:
        raise sightings_repository.TooManySightings(
            f"{len(long)} values over "
            f"{sightings_repository.KEYWORD_IGNORE_ABOVE} characters: at most "
            f"{MAX_LONG_VALUES} a request"
        )


def _attributes(refs: list[str]) -> dict[str, dict]:
    """Attributes by uuid, or by numeric MISP id for pulled ones, as
    sightings_repository._resolve_attribute finds them; in one request
    for each kind rather than one a reference."""
    from app.services.opensearch import get_opensearch_client

    if not refs:
        return {}
    client = get_opensearch_client()
    source = ["uuid", "value", "event_uuid", "id"]
    found: dict[str, dict] = {}
    ids = sorted({ref for ref in refs if ref.isdigit()})
    uuids = sorted({ref for ref in refs if not ref.isdigit()})
    if uuids:
        response = client.mget(
            index="misp-attributes", body={"ids": uuids}, _source=source
        )
        for doc in response.get("docs", []):
            if doc.get("found"):
                found[doc["_id"]] = doc["_source"]
    if ids:
        hits = client.search(
            index="misp-attributes",
            body={
                "query": {"terms": {"id": [int(i) for i in ids]}},
                "size": len(ids),
                "_source": source,
            },
        )["hits"]["hits"]
        for hit in hits:
            found.setdefault(str(hit["_source"].get("id")), hit["_source"])
    return found


def resolve(sightings: list[dict], only_known: bool) -> tuple[list[dict], int]:
    """The sightings to report, each marked ``known`` when an attribute
    holds its value; and how many were left out. Call check_limits first."""
    attributes = _attributes(
        sorted(
            {
                str(s["attribute_uuid"]).strip()
                for s in sightings
                if s.get("attribute_uuid")
            }
        )
    )
    known = set(
        sightings_repository.find_sighted_attributes(
            sorted({s["value"] for s in sightings if s.get("value")})
        )
    )

    kept: list[dict] = []
    skipped = 0
    for sighting in sightings:
        uuid = sighting.get("attribute_uuid")
        if uuid:
            attribute = attributes.get(str(uuid).strip())
            if attribute is None:
                skipped += 1
                continue
            kept.append(
                {
                    **sighting,
                    "value": attribute["value"],
                    "attribute_uuid": attribute["uuid"],
                    "event_uuid": attribute.get("event_uuid"),
                    "known": True,
                }
            )
            continue
        is_known = sighting["value"] in known
        if only_known and not is_known:
            skipped += 1
            continue
        kept.append({**sighting, "known": is_known})
    return kept, skipped


def try_mapping(data: alert_receiver_schemas.MappingTest, default_source: str) -> dict:
    """What a body would report, written nowhere."""
    try:
        records, sightings = map_payload(
            data.payload, data.mapping.model_dump(), default_source
        )
    except MappingError as error:
        return {"error": str(error)}
    try:
        check_limits(sightings)
    except sightings_repository.TooManySightings as error:
        return {"records": records, "error": str(error)}
    kept, skipped = resolve(sightings, data.only_known)
    return {"records": records, "sightings": kept, "skipped": skipped}


# ── Visibility and CRUD ───────────────────────────────────────────────────


class ReceiverNotFound(LookupError):
    pass


def _now() -> datetime:
    return datetime.now(timezone.utc)


def sees_all(user) -> bool:
    """Admins see and manage every organisation's receivers."""
    return "*" in list(getattr(getattr(user, "role", None), "scopes", None) or [])


def visible(db: Session, user) -> list:
    query = db.query(alert_receiver_models.AlertReceiver)
    if not sees_all(user):
        query = query.filter(alert_receiver_models.AlertReceiver.org_id == user.org_id)
    return query.order_by(alert_receiver_models.AlertReceiver.name).all()


def get_receiver(db: Session, user, receiver_id: int):
    receiver = db.get(alert_receiver_models.AlertReceiver, receiver_id)
    if receiver is None or not (sees_all(user) or receiver.org_id == user.org_id):
        raise ReceiverNotFound(receiver_id)
    return receiver


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _new_token() -> tuple[str, str, str]:
    """A token's value, prefix and hash."""
    value = TOKEN_PREFIX + secrets.token_urlsafe(32)
    return value, value[: len(TOKEN_PREFIX) + 8], hash_token(value)


def path_of(token: str) -> str:
    return f"/webhooks/alerts/{token}"


def create_receiver(
    db: Session, data: alert_receiver_schemas.AlertReceiverCreate, user
) -> tuple[Any, str]:
    """A new receiver, and its token, shown once."""
    mapping = data.mapping.model_dump() if data.mapping else preset_mapping(data.preset)
    preset_mapping(data.preset)
    value, prefix, token_hash = _new_token()
    receiver = alert_receiver_models.AlertReceiver(
        **data.model_dump(exclude={"mapping"}),
        mapping=mapping,
        token_prefix=prefix,
        token_hash=token_hash,
        org_id=user.org_id,
        created_by=user.id,
        created_at=_now(),
    )
    db.add(receiver)
    db.commit()
    db.refresh(receiver)
    return receiver, value


def update_receiver(
    db: Session, receiver, data: alert_receiver_schemas.AlertReceiverUpdate
):
    patch = data.model_dump(exclude_unset=True)
    for key in ("name", "preset", "mapping", "only_known", "rate_limit", "enabled"):
        if key in patch and patch[key] is None:
            raise ValueError(f"{key} can't be empty")
    if "allowed_ips" in patch and patch["allowed_ips"] is None:
        patch["allowed_ips"] = []
    if "preset" in patch:
        mapping = preset_mapping(patch["preset"])
        # A new preset brings its mapping, unless one comes with it.
        if patch["preset"] != receiver.preset and "mapping" not in patch:
            patch["mapping"] = mapping
    for key, value in patch.items():
        setattr(receiver, key, value)
    receiver.updated_at = _now()
    db.commit()
    db.refresh(receiver)
    return receiver


def delete_receiver(db: Session, receiver) -> None:
    db.delete(receiver)
    db.commit()


def rotate_token(db: Session, receiver) -> str:
    """A new token for the receiver; the old one stops working now."""
    value, prefix, token_hash = _new_token()
    receiver.token_prefix = prefix
    receiver.token_hash = token_hash
    receiver.updated_at = _now()
    db.commit()
    db.refresh(receiver)
    return value


# ── Receiving ─────────────────────────────────────────────────────────────


def find_by_token(db: Session, value: str):
    if not value.startswith(TOKEN_PREFIX) or len(value) > 128:
        return None
    return (
        db.query(alert_receiver_models.AlertReceiver)
        .filter(alert_receiver_models.AlertReceiver.token_hash == hash_token(value))
        .first()
    )


def refused(receiver, ip: Optional[str]) -> Optional[str]:
    """Why a receiver takes no alert from this address now (disabled,
    address), or None."""
    if not receiver.enabled:
        return "disabled"
    if receiver.allowed_ips:
        try:
            address = ipaddress.ip_address(ip or "")
        except ValueError:
            return "address"
        if not any(
            address in ipaddress.ip_network(network, strict=False)
            for network in receiver.allowed_ips
        ):
            return "address"
    return None


def rate_limited(receiver, now: Optional[float] = None) -> Optional[int]:
    """Seconds until the receiver takes requests again, or None. Counted
    per minute in Redis, shared by every API worker."""
    from app.services.redis import get_redis_client

    now = now if now is not None else datetime.now(timezone.utc).timestamp()
    minute = int(now // 60)
    key = f"alert-receivers:{receiver.id}:rate:{minute}"
    try:
        redis = get_redis_client()
        count = redis.incr(key)
        if count == 1:
            redis.expire(key, 120)
    except Exception:
        # Better to take alerts unlimited than to drop them with Redis down.
        logger.warning("alert receiver rate limit unavailable", exc_info=True)
        return None
    if count > receiver.rate_limit:
        return max(1, 60 - int(now % 60))
    return None


def _counters(db: Session, receiver, **values) -> None:
    """Counters updated in SQL, so concurrent requests all count."""
    model = alert_receiver_models.AlertReceiver
    db.query(model).filter(model.id == receiver.id).update(
        values, synchronize_session=False
    )


def received(db: Session, receiver, body: bytes, ip: Optional[str]) -> None:
    """Note a request: when, from where, and its body."""
    model = alert_receiver_models.AlertReceiver
    _counters(
        db,
        receiver,
        last_received_at=_now(),
        last_ip=ip,
        received_count=model.received_count + 1,
        last_payload=body[:LAST_PAYLOAD_MAX].decode("utf-8", errors="replace"),
    )


def failed(db: Session, receiver, error: str) -> None:
    _counters(db, receiver, last_error=error[:2000], last_error_at=_now())


def receive(db: Session, receiver, payload: Any) -> dict:
    """Report a body's sightings. Raises MappingError when the mapping can't
    read it, sightings_repository.TooManySightings past the limit."""
    records, sightings = map_payload(payload, receiver.mapping, receiver.name)
    check_limits(sightings)
    kept, _ = resolve(sightings, receiver.only_known)
    docs = []
    for sighting in kept:
        doc = {
            "value": sighting["value"],
            "type": sighting["type"],
            "timestamp": sighting["timestamp"],
            "observer": {"source": sighting["source"]},
            "metadata": {"sensor_type": receiver.preset},
        }
        if sighting.get("attribute_uuid"):
            doc["attribute_uuid"] = sighting["attribute_uuid"]
            doc["event_uuid"] = sighting.get("event_uuid")
        docs.append(doc)
    if docs:
        # The receiver stands for its organisation, as a user would.
        sightings_repository.create_sightings(receiver, docs)
    model = alert_receiver_models.AlertReceiver
    _counters(
        db,
        receiver,
        sightings_count=model.sightings_count + len(docs),
        last_error=None,
        last_error_at=None,
    )
    # Only the records taken: how many values were known would tell whoever
    # holds the token which indicators this instance tracks.
    return {"records": records}


def parse_body(body: bytes) -> Any:
    try:
        return json.loads(body)
    except (ValueError, UnicodeDecodeError) as error:
        raise MappingError(f"the body is no JSON: {error}")
    except RecursionError:
        raise MappingError("the body is nested too deep")
