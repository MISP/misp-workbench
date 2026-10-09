"""Render indicator records into each sink protocol's wire format.

A *record* is the protocol-neutral view of one attribute and its event, built
by :func:`build_record`. Every formatter is a pure function of records and
sink config, so they can be tested without a network.
"""

import json
from datetime import datetime, timezone
from typing import Iterable, Optional

PRODUCT = "misp-workbench"
PRODUCT_VERSION = "1.0"

# MISP attribute type -> CEF extension key holding the value, so SIEM field
# extraction (src/dst/dhost/request/fileHash) works without custom parsing.
CEF_VALUE_KEYS = {
    "ip-src": "src",
    "ip-dst": "dst",
    "domain": "dhost",
    "hostname": "dhost",
    "url": "request",
    "uri": "request",
    "filename": "fname",
    "md5": "fileHash",
    "sha1": "fileHash",
    "sha256": "fileHash",
    "sha512": "fileHash",
    "email-src": "suser",
    "email-dst": "duser",
}

# MISP threat level (1 high … 4 undefined) -> CEF severity (0-10).
CEF_SEVERITY = {1: 8, 2: 5, 3: 3, 4: 1}


def tag_names(tags) -> list[str]:
    return [t.get("name") for t in tags or [] if isinstance(t, dict) and t.get("name")]


def build_record(attribute: dict, event: dict) -> dict:
    """One attribute with the event context a SIEM needs to triage it."""
    organisation = event.get("organisation") or {}
    return {
        "uuid": attribute.get("uuid"),
        "type": attribute.get("type"),
        "category": attribute.get("category"),
        "value": attribute.get("value"),
        "to_ids": bool(attribute.get("to_ids")),
        "comment": attribute.get("comment") or "",
        "timestamp": attribute.get("timestamp"),
        "first_seen": attribute.get("first_seen"),
        "last_seen": attribute.get("last_seen"),
        "object_uuid": attribute.get("object_uuid"),
        "object_relation": attribute.get("object_relation"),
        "tags": tag_names(attribute.get("tags")),
        "event": {
            "uuid": event.get("uuid"),
            "info": event.get("info"),
            "date": (str(event.get("date") or "")[:10]) or None,
            "threat_level_id": event.get("threat_level"),
            "analysis": event.get("analysis"),
            "publish_timestamp": event.get("publish_timestamp"),
            "org": organisation.get("name"),
            "tags": tag_names(event.get("tags")),
        },
    }


def all_tags(record: dict) -> list[str]:
    return record["tags"] + record["event"]["tags"]


def _event_time(record: dict) -> float:
    return float(record.get("timestamp") or datetime.now(timezone.utc).timestamp())


# ── Splunk HEC ────────────────────────────────────────────────────────────


def splunk_hec_body(records: Iterable[dict], config: dict) -> str:
    """HEC batch: event objects concatenated in one request body."""
    lines = []
    for record in records:
        envelope = {
            "time": _event_time(record),
            "host": PRODUCT,
            "source": config.get("source") or PRODUCT,
            "sourcetype": config.get("sourcetype") or "misp:attribute",
            "event": record,
        }
        if config.get("index"):
            envelope["index"] = config["index"]
        lines.append(json.dumps(envelope, default=str))
    return "\n".join(lines)


# ── GELF ──────────────────────────────────────────────────────────────────


def gelf_message(record: dict) -> dict:
    """GELF 1.1; MISP fields become ``_misp_*`` additional fields."""
    event = record["event"]
    message = {
        "version": "1.1",
        "host": PRODUCT,
        "short_message": f"MISP indicator {record['type']}: {record['value']}",
        "timestamp": _event_time(record),
        "level": 6,
        "_misp_attribute_uuid": record["uuid"],
        "_misp_type": record["type"],
        "_misp_category": record["category"],
        "_misp_value": record["value"],
        "_misp_to_ids": int(record["to_ids"]),
        "_misp_comment": record["comment"],
        "_misp_tags": ",".join(all_tags(record)),
        "_misp_event_uuid": event["uuid"],
        "_misp_event_info": event["info"],
        "_misp_event_org": event["org"],
        "_misp_threat_level_id": event["threat_level_id"],
    }
    # GELF drops null additional fields at best and rejects them at worst.
    return {k: v for k, v in message.items() if v is not None and v != ""}


def gelf_frames(records: Iterable[dict]) -> bytes:
    """GELF TCP: one JSON message per frame, each terminated by a null byte."""
    return b"".join(
        json.dumps(gelf_message(r), default=str).encode("utf-8") + b"\0"
        for r in records
    )


# ── Syslog / CEF ──────────────────────────────────────────────────────────


def _cef_header(value) -> str:
    return str(value).replace("\\", "\\\\").replace("|", "\\|")


def _cef_extension(value) -> str:
    return (
        str(value)
        .replace("\\", "\\\\")
        .replace("=", "\\=")
        .replace("\r", "\\r")
        .replace("\n", "\\n")
    )


def cef_message(record: dict) -> str:
    event = record["event"]
    severity = CEF_SEVERITY.get(event.get("threat_level_id"), 1)
    extension = {
        "rt": int(_event_time(record) * 1000),
        "msg": event.get("info"),
        "cs1Label": "mispValue",
        "cs1": record["value"],
        "cs2Label": "mispType",
        "cs2": record["type"],
        "cs3Label": "mispCategory",
        "cs3": record["category"],
        "cs4Label": "mispEventUuid",
        "cs4": event.get("uuid"),
        "cs5Label": "mispTags",
        "cs5": ",".join(all_tags(record)),
        "cs6Label": "mispAttributeUuid",
        "cs6": record["uuid"],
        "cn1Label": "mispToIds",
        "cn1": int(record["to_ids"]),
    }
    value_key = CEF_VALUE_KEYS.get(record["type"])
    if value_key:
        extension[value_key] = record["value"]
    rendered = " ".join(
        f"{key}={_cef_extension(value)}"
        for key, value in extension.items()
        if value not in (None, "")
    )
    header = "|".join(
        _cef_header(part)
        for part in (
            "CEF:0",
            "MISP",
            PRODUCT,
            PRODUCT_VERSION,
            f"misp:{record['type']}",
            "MISP indicator",
            severity,
        )
    )
    return f"{header}|{rendered}"


def syslog_line(record: dict, hostname: str, now: Optional[datetime] = None) -> str:
    """RFC 5424: ``<PRI>1 TIMESTAMP HOSTNAME APP-NAME PROCID MSGID SD MSG``.

    PRI 134 is facility local0, severity informational.
    """
    timestamp = (now or datetime.now(timezone.utc)).isoformat(timespec="milliseconds")
    host = (hostname or "-").replace(" ", "_")
    return (
        f"<134>1 {timestamp} {host} {PRODUCT} - misp-indicator - {cef_message(record)}"
    )


# ── Webhook ───────────────────────────────────────────────────────────────


def webhook_body(records: list[dict]) -> str:
    """One request per batch; the shared event context is sent once."""
    event = records[0]["event"] if records else {}
    attributes = [{k: v for k, v in r.items() if k != "event"} for r in records]
    return json.dumps(
        {"source": PRODUCT, "event": event, "attributes": attributes}, default=str
    )
