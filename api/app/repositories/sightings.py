import logging
from typing import Union
from app.dependencies import get_opensearch_client
from fastapi import HTTPException, status
from opensearchpy import helpers as opensearch_helpers
import datetime

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
    if params.get("sighting_type"):
        query["query"]["bool"]["must"].append(
            {"term": {"sighting_type.keyword": params["sighting_type"]}}
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
    sighting["sighting_type"] = sighting.get("sighting_type", "positive")
    sighting["observer"] = sighting.get(
        "observer",
        {
            "organization": user.organisation.name,
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

    try:
        response = opensearch_helpers.bulk(OpenSearchClient, docs)
        return {"result": "Sightings created successfully", "response": response}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )
