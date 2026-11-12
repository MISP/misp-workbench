"""What an indicator is derived from: the attributes it merges, the objects
they sit in and the events holding them (``GET /indicators/{uuid}/graph``).

An indicator doesn't keep its attributes' uuids, so they are resolved live
from ``misp-attributes`` by type and value, leaving out deleted attributes
and deleted events as the merge does (``indicators.build_indicator``). A
popular value can be in hundreds of events: the newest ``MAX_EVENTS`` are
kept, and the rest only counted.
"""

from typing import Optional

from app.repositories import indicators, stream_exports
from app.services.opensearch import get_opensearch_client

EVENTS_INDEX = "misp-events"
OBJECTS_INDEX = "misp-objects"
# Events drawn, newest first; the others are counted, not drawn.
MAX_EVENTS = indicators.MAX_EVENTS_LISTED
# Attributes read for one value before giving up on the rest: a value in more
# than this many live attributes is reported as truncated.
MAX_ATTRIBUTES = 10_000
# An object's other attributes (its context), shown per object at most.
MAX_SIBLINGS = 25

ATTRIBUTE_FIELDS = [
    "uuid",
    "type",
    "value",
    "category",
    "to_ids",
    "comment",
    "timestamp",
    "tags",
    "event_uuid",
    "object_uuid",
    "object_relation",
]
EVENT_FIELDS = [
    "uuid",
    "info",
    "date",
    "timestamp",
    *indicators._Events.FIELDS,
]
OBJECT_FIELDS = ["uuid", "name", "meta_category", "comment", "event_uuid", "deleted"]


def _attribute(source: dict) -> dict:
    return {
        "uuid": source.get("uuid"),
        "type": source.get("type"),
        "value": source.get("value"),
        "category": source.get("category"),
        "to_ids": bool(source.get("to_ids")),
        "comment": source.get("comment") or None,
        "timestamp": indicators._as_int(source.get("timestamp")),
        "tags": indicators._tag_names(source.get("tags")),
        "event_uuid": source.get("event_uuid"),
        "object_uuid": source.get("object_uuid") or None,
        "object_relation": source.get("object_relation") or None,
    }


def _live_attributes(client, type_: str, value: str) -> tuple[list[dict], bool]:
    """The live attributes of ``type_`` and ``value``, and whether there were
    more than MAX_ATTRIBUTES."""
    found: list[dict] = []
    for clause in indicators.value_clauses([value]):
        query = indicators._live_attributes([clause, {"term": {"type.keyword": type_}}])
        pages = stream_exports.iter_pit_pages(
            client, indicators.ATTRIBUTES_INDEX, query, source=ATTRIBUTE_FIELDS
        )
        try:
            for hits in pages:
                for hit in hits:
                    source = hit["_source"]
                    # Long values are matched by phrase: keep exact ones.
                    if source.get("value") != value:
                        continue
                    if len(found) >= MAX_ATTRIBUTES:
                        return found, True
                    found.append(_attribute(source))
        finally:
            pages.close()
    return found, False


def _events(client, uuids: list[str]) -> dict[str, dict]:
    summaries = indicators._Events(client, indicators._organisation_names())
    found: dict[str, dict] = {}
    for chunk in indicators._chunks(uuids, indicators.TERMS_CHUNK):
        response = client.mget(
            index=EVENTS_INDEX, body={"ids": chunk}, _source_includes=EVENT_FIELDS
        )
        for doc in response["docs"]:
            if not doc.get("found"):
                continue
            source = doc["_source"]
            summary = summaries._summary(source)
            found[doc["_id"]] = {
                "uuid": doc["_id"],
                "info": source.get("info"),
                "date": source.get("date"),
                "timestamp": indicators._as_int(source.get("timestamp")),
                "deleted": summary["deleted"],
                "source": summary["source"],
                "org": summary["org"],
            }
    return found


def _objects(client, uuids: list[str]) -> dict[str, dict]:
    found: dict[str, dict] = {}
    for chunk in indicators._chunks(uuids, indicators.TERMS_CHUNK):
        response = client.mget(
            index=OBJECTS_INDEX, body={"ids": chunk}, _source_includes=OBJECT_FIELDS
        )
        for doc in response["docs"]:
            source = doc.get("_source") or {}
            if doc.get("found") and not source.get("deleted"):
                found[doc["_id"]] = {
                    "uuid": doc["_id"],
                    "name": source.get("name"),
                    "meta_category": source.get("meta_category"),
                    "comment": source.get("comment") or None,
                    "event_uuid": source.get("event_uuid"),
                    "attributes": [],
                    "attribute_count": 0,
                }
    return found


def _add_siblings(client, objects: dict[str, dict], drawn: set) -> None:
    """Each object's other live attributes (up to MAX_SIBLINGS), the context
    that makes the object useful."""
    if not objects:
        return
    for chunk in indicators._chunks(list(objects), indicators.TERMS_CHUNK):
        query = {
            "bool": {
                "filter": [{"terms": {"object_uuid": chunk}}],
                "must_not": [{"term": {"deleted": True}}],
            }
        }
        for hits in stream_exports.iter_pit_pages(
            client, indicators.ATTRIBUTES_INDEX, query, source=ATTRIBUTE_FIELDS
        ):
            for hit in hits:
                source = hit["_source"]
                obj = objects.get(source.get("object_uuid"))
                if obj is None or source.get("uuid") in drawn:
                    continue
                obj["attribute_count"] += 1
                if len(obj["attributes"]) < MAX_SIBLINGS:
                    obj["attributes"].append(_attribute(source))
    for obj in objects.values():
        obj["attributes"].sort(
            key=lambda a: (a.get("object_relation") or "", a.get("value") or "")
        )


def empty(indicator: dict) -> dict:
    return {
        "indicator": {
            "uuid": indicator["uuid"],
            "type": indicator["type"],
            "value": indicator["value"],
            "deleted": bool(indicator.get("deleted")),
        },
        "attributes": [],
        "objects": [],
        "events": [],
        "attribute_count": 0,
        "event_count": 0,
        "omitted_events": 0,
        "truncated": False,
    }


def graph(indicator: dict, max_events: Optional[int] = None) -> dict:
    """The attributes ``indicator`` is derived from, their objects and their
    events (the newest ``max_events`` of them). A tombstoned indicator has
    none."""
    result = empty(indicator)
    if indicator.get("deleted"):
        return result
    max_events = max_events or MAX_EVENTS
    client = get_opensearch_client()

    attributes, truncated = _live_attributes(
        client, indicator["type"], indicator["value"]
    )
    events = _events(
        client,
        list(dict.fromkeys(a["event_uuid"] for a in attributes if a["event_uuid"])),
    )
    # As the merge: an attribute in a deleted event doesn't count. One whose
    # event isn't indexed (yet) still does, drawn without its event.
    attributes = [
        a for a in attributes if not (events.get(a["event_uuid"]) or {}).get("deleted")
    ]
    live_events = sorted(
        (e for e in events.values() if not e["deleted"]),
        key=lambda e: (e["timestamp"] or 0, e["uuid"]),
        reverse=True,
    )
    kept = live_events[:max_events]
    kept_uuids = {e["uuid"] for e in kept}
    drawn = [
        a
        for a in attributes
        if a["event_uuid"] in kept_uuids or a["event_uuid"] not in events
    ]
    drawn.sort(key=lambda a: a["timestamp"] or 0, reverse=True)

    objects = _objects(
        client, list(dict.fromkeys(a["object_uuid"] for a in drawn if a["object_uuid"]))
    )
    _add_siblings(client, objects, {a["uuid"] for a in drawn})
    for attribute in drawn:
        # An attribute whose object is gone (or deleted) hangs off its event.
        if attribute["object_uuid"] not in objects:
            attribute["object_uuid"] = None

    for event in kept:
        del event["deleted"]
    result.update(
        attributes=drawn,
        objects=list(objects.values()),
        events=kept,
        attribute_count=len(attributes),
        event_count=len(live_events),
        omitted_events=len(live_events) - len(kept),
        truncated=truncated,
    )
    return result
