"""Transform OpenSearch hit ``_source`` dicts into export artifacts.

Each converter takes the list of OpenSearch ``_source`` documents (attributes
or events) plus the ``index_target`` and returns ``(bytes, file_extension,
content_type)``. ``json`` is a passthrough dump; ``csv`` flattens the most
useful fields; ``stix`` builds pymisp objects and runs the misp-stix
MISP→STIX 2.1 converter.
"""

import csv
import io
import json
import logging
from typing import Iterable

logger = logging.getLogger(__name__)

# STIX 2.1 conversion (misp-stix + python-stix2 serialization) is pure-Python
# and scales poorly: python-stix2's pretty serializer sorts every property via
# a recursive scan of the whole bundle, so tens of thousands of attributes can
# peg a CPU core for hours. Cap STIX exports well below the generic record cap.
MAX_STIX_RECORDS = 10_000


def _tag_names(tags) -> list[str]:
    """Normalise the ``tags`` field (list of dicts or strings) to names."""
    names = []
    for tag in tags or []:
        if isinstance(tag, dict):
            name = tag.get("name")
            if name:
                names.append(name)
        elif isinstance(tag, str):
            names.append(tag)
    return names


# ── JSON ──────────────────────────────────────────────────────────────────


def to_json(hits: list[dict], index_target: str) -> tuple[bytes, str, str]:
    payload = json.dumps(hits, default=str, indent=2).encode("utf-8")
    return payload, "json", "application/json"


# ── CSV ───────────────────────────────────────────────────────────────────

ATTRIBUTE_CSV_FIELDS = [
    "uuid",
    "event_uuid",
    "object_uuid",
    "object_relation",
    "category",
    "type",
    "value",
    "to_ids",
    "comment",
    "timestamp",
    "first_seen",
    "last_seen",
    "tags",
]

EVENT_CSV_FIELDS = [
    "uuid",
    "info",
    "date",
    "threat_level",
    "analysis",
    "published",
    "timestamp",
    "org_id",
    "orgc_id",
    "tags",
]


def to_csv(hits: list[dict], index_target: str) -> tuple[bytes, str, str]:
    fields = EVENT_CSV_FIELDS if index_target == "events" else ATTRIBUTE_CSV_FIELDS
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    for hit in hits:
        row = {key: hit.get(key) for key in fields}
        row["tags"] = "|".join(_tag_names(hit.get("tags")))
        writer.writerow(row)
    return buffer.getvalue().encode("utf-8"), "csv", "text/csv"


# ── STIX 2.1 ────────────────────────────────────────────────────────────────


def _build_misp_attribute(doc: dict):
    from pymisp import MISPAttribute

    attribute = MISPAttribute()
    payload = {
        "type": doc.get("type"),
        "value": doc.get("value"),
        "category": doc.get("category"),
        "to_ids": doc.get("to_ids", True),
        "comment": doc.get("comment") or "",
    }
    if doc.get("uuid"):
        payload["uuid"] = doc["uuid"]
    if doc.get("timestamp"):
        payload["timestamp"] = doc["timestamp"]
    attribute.from_dict(**payload)
    for name in _tag_names(doc.get("tags")):
        attribute.add_tag(name)
    return attribute


def _build_misp_event(uuid_value: str | None, info: str, docs: Iterable[dict]):
    import uuid as uuid_module

    from pymisp import MISPEvent

    event = MISPEvent()
    event.uuid = uuid_value or str(uuid_module.uuid4())
    event.info = info or "misp-workbench export"
    return event


def _events_from_attribute_hits(hits: list[dict]) -> list:
    """Group attribute docs by their parent event into MISPEvents."""
    grouped: dict[str, list[dict]] = {}
    order: list[str] = []
    for hit in hits:
        if not hit.get("value") or not hit.get("type"):
            continue
        event_uuid = hit.get("event_uuid") or "__ungrouped__"
        if event_uuid not in grouped:
            grouped[event_uuid] = []
            order.append(event_uuid)
        grouped[event_uuid].append(hit)

    events = []
    for event_uuid in order:
        docs = grouped[event_uuid]
        real_uuid = None if event_uuid == "__ungrouped__" else event_uuid
        event = _build_misp_event(
            real_uuid, f"Export of {len(docs)} attribute(s)", docs
        )
        for doc in docs:
            try:
                event.attributes.append(_build_misp_attribute(doc))
            except Exception as e:  # pragma: no cover - skip malformed rows
                logger.warning("Skipping attribute in STIX export: %s", e)
        events.append(event)
    return events


def _events_from_event_hits(hits: list[dict]) -> list:
    events = []
    for hit in hits:
        if not hit.get("uuid"):
            continue
        event = _build_misp_event(hit["uuid"], hit.get("info"), [])
        for name in _tag_names(hit.get("tags")):
            event.add_tag(name)
        events.append(event)
    return events


def to_stix21(hits: list[dict], index_target: str) -> tuple[bytes, str, str]:
    from misp_stix_converter import MISPtoSTIX21Parser

    if len(hits) > MAX_STIX_RECORDS:
        raise ValueError(
            f"STIX export is limited to {MAX_STIX_RECORDS} records "
            f"(query matched {len(hits)}). Narrow the query or use JSON/CSV."
        )

    if index_target == "events":
        events = _events_from_event_hits(hits)
    else:
        events = _events_from_attribute_hits(hits)

    parser = MISPtoSTIX21Parser()
    for event in events:
        parser.parse_misp_event(event)

    bundle = parser.bundle
    # pretty=True triggers python-stix2's recursive property sort, which is
    # pathologically slow on large bundles; serialize compactly instead.
    payload = bundle.serialize().encode("utf-8")
    return payload, "json", "application/stix+json"


CONVERTERS = {
    "json": to_json,
    "csv": to_csv,
    "stix": to_stix21,
}


def convert(fmt: str, hits: list[dict], index_target: str) -> tuple[bytes, str, str]:
    if fmt not in CONVERTERS:
        raise ValueError(f"Unsupported export format: {fmt}")
    return CONVERTERS[fmt](hits, index_target)
