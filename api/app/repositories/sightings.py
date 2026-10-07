import logging
import datetime
from typing import Optional, Union
from app.schemas import sighting as sighting_schemas
from app.services.opensearch import get_opensearch_client
from fastapi import HTTPException, status
from opensearchpy import helpers as opensearch_helpers
from app.worker import tasks

logger = logging.getLogger(__name__)


def get_sightings(params: sighting_schemas.SightingQueryParams, page: int = 0, from_value: int = 0, size: int = 100):
    OpenSearchClient = get_opensearch_client()

    query = {
        "from": from_value,
        "size": size,
        "query": {
            "bool": {
                "must": [],
            },
        },
    }

    if params.attribute_uuid:
        query["query"]["bool"]["must"].append(
            {"term": {"attribute_uuid.keyword": params.attribute_uuid}}
        )
    if params.type:
        query["query"]["bool"]["must"].append(
            {"term": {"type.keyword": params.type}}
        )

    response = OpenSearchClient.search(
        index="misp-sightings",
        body=query,
    )

    return {
        "page": page,
        "size": size,
        "total": response["hits"]["total"]["value"],
        "took": response["took"],
        "timed_out": response["timed_out"],
        "max_score": response["hits"]["max_score"],
        "results": response["hits"]["hits"],
    }


def create_sighting_doc(user, sighting: dict):
    if not sighting.get("value"):
        logger.warning("Sighting value is required, skipping sighting creation.")
        return None

    sighting["@timestamp"] = (
        datetime.datetime.fromtimestamp(sighting["timestamp"]).isoformat()
        if sighting.get("timestamp")
        else datetime.datetime.now().isoformat()
    )
    sighting["type"] = sighting.get("type", "positive")
    # The reporting organisation is always the caller's: a client can name its
    # sensor (``source``) but not report on another organisation's behalf,
    # which false-positive feedback counts on.
    observer = dict(sighting.get("observer") or {})
    observer["organisation"] = user.organisation.name
    sighting["observer"] = observer

    return sighting


# One request can carry a SIEM's worth of hits, but not unbounded.
MAX_SIGHTINGS_PER_REQUEST = 10_000
# Sightings post-processed (notifications, reactor, false-positive feedback)
# per task: one task per batch instead of one per sighting.
TASK_BATCH_SIZE = 1000
# keyword sub-fields are mapped with ignore_above: 256.
KEYWORD_IGNORE_ABOVE = 256

FALSE_POSITIVE = "false-positive"


class TooManySightings(ValueError):
    pass


def _task_item(sighting: dict) -> dict:
    """What post-processing needs from a sighting, kept small for the broker."""
    return {
        "value": sighting["value"],
        "type": sighting["type"],
        "organisation": sighting["observer"].get("organisation"),
        "timestamp": sighting.get("timestamp")
        or datetime.datetime.now().timestamp(),
    }


def create_sightings(user, sightings: Union[list, dict]):
    """Index sightings in bulk and queue their post-processing in batches.

    A list of 10,000 sightings costs one bulk request and ten tasks, rather
    than ten thousand tasks each searching OpenSearch on its own.
    """
    single = isinstance(sightings, dict)
    items = [sightings] if single else list(sightings)
    if len(items) > MAX_SIGHTINGS_PER_REQUEST:
        raise TooManySightings(
            f"at most {MAX_SIGHTINGS_PER_REQUEST} sightings per request, got {len(items)}"
        )

    docs = []
    for item in items:
        sighting = create_sighting_doc(user, item)
        if sighting is not None:
            docs.append(sighting)

    try:
        response = opensearch_helpers.bulk(
            get_opensearch_client(),
            ({"_index": "misp-sightings", "_source": doc} for doc in docs),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )

    for start in range(0, len(docs), TASK_BATCH_SIZE):
        tasks.handle_created_sightings.delay(
            [_task_item(doc) for doc in docs[start : start + TASK_BATCH_SIZE]]
        )

    if single:
        return {"result": "Sighting created successfully"}
    return {"result": "Sightings created successfully", "response": response}


# MISP sighting types by number, plus the names misp-workbench stores.
MISP_SIGHTING_TYPES = {
    "0": "positive",
    "1": FALSE_POSITIVE,
    "2": "expiration",
    "positive": "positive",
    "sighting": "positive",
    FALSE_POSITIVE: FALSE_POSITIVE,
    "expiration": "expiration",
}


class SightingTargetNotFound(LookupError):
    pass


def _resolve_attribute(ref: str) -> Optional[dict]:
    """An attribute by uuid, or by numeric MISP id for pulled ones."""
    client = get_opensearch_client()
    ref = str(ref).strip()
    if ref.isdigit():
        hits = client.search(
            index="misp-attributes",
            body={"query": {"term": {"id": int(ref)}}, "size": 1},
        )["hits"]["hits"]
        return hits[0]["_source"] if hits else None
    response = client.get(index="misp-attributes", id=ref, ignore=[404])
    return response.get("_source") if response.get("found") else None


def sightings_from_misp(
    payload: sighting_schemas.MispSightingAdd, attribute_ref: Optional[str] = None
) -> list[dict]:
    """Translate a MISP ``/sightings/add`` request into sighting documents.

    Raises ValueError for a malformed request, SightingTargetNotFound when the
    referenced attribute doesn't exist.
    """
    sighting_type = MISP_SIGHTING_TYPES.get(str(payload.type if payload.type is not None else 0).lower())
    if sighting_type is None:
        raise ValueError(
            f"unknown sighting type {payload.type!r}: use 0 (sighting), "
            "1 (false positive) or 2 (expiration)"
        )

    base: dict = {"type": sighting_type}
    if payload.timestamp:
        base["timestamp"] = payload.timestamp
    if payload.source:
        base["observer"] = {"source": payload.source}

    ref = attribute_ref or payload.uuid or payload.id
    if ref:
        attribute = _resolve_attribute(ref)
        if attribute is None:
            raise SightingTargetNotFound(f"attribute {ref} not found")
        return [
            {
                **base,
                "value": attribute["value"],
                "attribute_uuid": attribute["uuid"],
                "event_uuid": attribute.get("event_uuid"),
            }
        ]

    values = list(payload.values or [])
    if payload.value:
        values.append(payload.value)
    values = [str(v) for v in values if str(v).strip()]
    if not values:
        raise ValueError("one of value, values, uuid or id is required")
    return [{**base, "value": value} for value in values]


def _value_query(values: list[str]) -> dict:
    """Attributes whose value is one of ``values``, long ones included."""
    short = [v for v in values if len(v) <= KEYWORD_IGNORE_ABOVE]
    should: list = []
    for start in range(0, len(short), 1000):
        should.append({"terms": {"value.keyword": short[start : start + 1000]}})
    should.extend(
        {"match_phrase": {"value": v}} for v in values if len(v) > KEYWORD_IGNORE_ABOVE
    )
    return {
        "bool": {
            "should": should or [{"match_none": {}}],
            "minimum_should_match": 1,
            "must_not": [{"term": {"deleted": True}}],
        }
    }


def find_sighted_attributes(values: list[str]) -> dict[str, list[dict]]:
    """Map each sighted value to the attributes holding it, in one paged query."""
    from app.repositories import stream_exports

    by_value: dict[str, list[dict]] = {}
    if not values:
        return by_value
    wanted = set(values)
    for hits in stream_exports.iter_pit_pages(
        get_opensearch_client(),
        "misp-attributes",
        _value_query(sorted(wanted)),
        source=["uuid", "type", "value", "event_uuid"],
    ):
        for hit in hits:
            value = hit["_source"].get("value")
            # match_phrase is looser than equality; keep exact matches only.
            if value in wanted:
                by_value.setdefault(value, []).append(hit)
    return by_value


def apply_false_positive_feedback(values: list[str], threshold: int) -> list[str]:
    """Stop flagging values for IDS once enough organisations report them benign.

    Counts the **distinct organisations** that reported a false-positive
    sighting for each value, not the sightings: one reporter repeating
    itself (or a compromised sensor flooding reports) can't suppress an
    indicator on its own. Values reaching ``threshold`` organisations get
    ``to_ids`` turned off on all their live attributes; returns them.
    ``threshold <= 0`` turns the feedback off.
    """
    if threshold <= 0 or not values:
        return []
    client = get_opensearch_client()
    # The sightings this batch belongs to were bulk-indexed moments ago.
    client.indices.refresh(index="misp-sightings")
    unique = sorted(set(values))
    response = client.search(
        index="misp-sightings",
        body={
            "size": 0,
            "query": {
                "bool": {
                    "filter": [
                        {"term": {"type": FALSE_POSITIVE}},
                        {"terms": {"value.keyword": unique}},
                    ]
                }
            },
            "aggs": {
                "values": {
                    "terms": {"field": "value.keyword", "size": len(unique)},
                    "aggs": {
                        "organisations": {
                            "cardinality": {"field": "observer.organisation"}
                        }
                    },
                }
            },
        },
    )
    crossed = [
        bucket["key"]
        for bucket in response["aggregations"]["values"]["buckets"]
        if bucket["organisations"]["value"] >= threshold
    ]
    if not crossed:
        return []

    query = _value_query(crossed)
    query["bool"]["filter"] = [{"term": {"to_ids": True}}]
    result = client.update_by_query(
        index="misp-attributes",
        body={
            "query": query,
            "script": {"lang": "painless", "source": "ctx._source.to_ids = false"},
        },
        conflicts="proceed",
        refresh=True,
    )
    logger.info(
        "false-positive feedback: to_ids turned off on %s attributes for %s values",
        result.get("updated"),
        len(crossed),
    )
    return crossed


def process_created_sightings(db, items: list[dict]) -> dict:
    """Post-process a batch of new sightings: notifications and FP feedback.

    Reactor dispatch stays with the task, which owns that helper.
    """
    from app.repositories import notifications as notifications_repository
    from app.services.runtime_settings import RuntimeSettings

    values = sorted({item["value"] for item in items})
    attributes_by_value = find_sighted_attributes(values)

    pairs = []
    for item in items:
        sighting = {
            "value": item["value"],
            "type": item["type"],
            "observer": {"organisation": item.get("organisation")},
            "timestamp": item.get("timestamp"),
        }
        for attribute in attributes_by_value.get(item["value"], []):
            pairs.append((attribute, sighting))
    notifications = notifications_repository.create_sighting_notifications_bulk(
        db, "created", pairs
    )

    threshold = int(
        RuntimeSettings(db).get_value("sightings.false_positive_threshold", default=0)
        or 0
    )
    disabled = apply_false_positive_feedback(
        [item["value"] for item in items if item["type"] == FALSE_POSITIVE],
        threshold,
    )
    return {"notifications": len(notifications), "to_ids_disabled": disabled}


def get_sightings_activity_by_value(params: sighting_schemas.SightingActivityParams):
    OpenSearchClient = get_opensearch_client()

    value = params.value
    period = params.period
    interval = params.interval

    query = {
        "size": 0,
        "query": {
            "bool": {
                "must": [
                    {"term": {"value": value}},
                    {"term": {"type": "positive"}},
                    {"range": {"@timestamp": {"gte": f"now-{period}/d", "lte": "now"}}},
                ]
            }
        },
        "aggs": {
            "sightings_over_time": {
                "date_histogram": {
                    "field": "@timestamp",
                    "fixed_interval": interval,
                    "min_doc_count": 0,
                    "extended_bounds": {"min": f"now-{period}/d", "max": "now"},
                }
            }
        },
    }

    response = OpenSearchClient.search(
        index="misp-sightings",
        body=query,
    )

    return response["aggregations"]


def get_sightings_stats_by_value(params: sighting_schemas.SightingActivityParams):
    OpenSearchClient = get_opensearch_client()

    value = params.value
    period = params.period

    query_total_period = {
        "track_total_hits": True,
        "size": 0,
        "query": {
            "bool": {
                "must": [
                    {"term": {"value": value}},
                    {"term": {"type": "positive"}},
                    {"range": {"@timestamp": {"gte": f"now-{period}/d", "lte": "now"}}},
                ]
            }
        },
    }
    total_period = OpenSearchClient.search(
        index="misp-sightings",
        body=query_total_period,
    )

    query_prev_period = query_total_period.copy()
    query_prev_period["query"]["bool"]["must"].append(
        {
            "range": {
                "@timestamp": {"gte": f"now-{period}/d-1d", "lte": f"now-{period}/d"}
            }
        }
    )

    total_prev_period = OpenSearchClient.search(
        index="misp-sightings",
        body=query_prev_period,
    )

    return {
        "total": total_period["hits"]["total"]["value"],
        "previous_total": total_prev_period["hits"]["total"]["value"],
    }
