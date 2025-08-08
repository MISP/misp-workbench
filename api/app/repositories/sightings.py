import logging
import datetime
from typing import Union
from app.services.opensearch import get_opensearch_client
from fastapi import HTTPException, status
from opensearchpy import helpers as opensearch_helpers
from app.worker import tasks

logger = logging.getLogger(__name__)


def get_sightings(params: dict, page: int = 0, from_value: int = 0, size: int = 100):
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

    if params.get("attribute_uuid"):
        query["query"]["bool"]["must"].append(
            {"term": {"attribute_uuid.keyword": params["attribute_uuid"]}}
        )
    if params.get("type"):
        query["query"]["bool"]["must"].append(
            {"term": {"type.keyword": params["type"]}}
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
    sighting["observer"] = sighting.get(
        "observer",
        {
            "organisation": user.organisation.name,
        },
    )

    return sighting


def create_sightings(user, sightings: Union[list, dict]):
    OpenSearchClient = get_opensearch_client()

    docs = []
    if isinstance(sightings, dict):
        sighting = create_sighting_doc(user, sightings)

        OpenSearchClient.index(
            index="misp-sightings",
            body=sighting,
        )

        tasks.handle_created_sighting.delay(
            sighting["value"],
            sighting["observer"]["organisation"],
            sighting["type"],
            sighting.get("timestamp", datetime.datetime.now().timestamp()),
        )

        return {"result": "Sighting created successfully"}

    for sighting in sightings:
        if not sighting.get("value"):
            logger.warning("Sighting value is required, skipping sighting creation.")
            continue

        sighting = create_sighting_doc(user, sighting)

        docs.append(
            {
                "_index": "misp-sightings",
                "_source": sighting,
            }
        )

        tasks.handle_created_sighting.delay(
            sighting["value"],
            sighting["observer"]["organisation"],
            sighting["type"],
            sighting.get("timestamp", datetime.datetime.now().timestamp()),
        )

    try:
        response = opensearch_helpers.bulk(OpenSearchClient, docs)
        return {"result": "Sightings created successfully", "response": response}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


def get_sightings_activity_by_value(params: dict):
    OpenSearchClient = get_opensearch_client()

    value = params.get("value")
    if not value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Value parameter is required",
        )

    period = params.get("period", "7d")
    interval = params.get("interval", "1h")

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


def get_sightings_stats_by_value(params: dict):
    OpenSearchClient = get_opensearch_client()

    value = params.get("value")
    if not value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Value parameter is required",
        )

    period = params.get("period", "7d")

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
