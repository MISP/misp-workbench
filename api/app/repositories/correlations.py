from app.services.opensearch import get_opensearch_client
from fastapi import HTTPException, status
from opensearchpy import helpers as opensearch_helpers
from app.services.runtime_settings import RuntimeSettings
from app.worker import tasks
import datetime
import logging

logger = logging.getLogger(__name__)

MAX_CORRELATIONS_PER_DOC = 1000
CORRELATION_PREFIX_LENGTH = 10
CORRELATION_MIN_SCORE = 2
CORRELATION_FUZZYNESS = "AUTO"
POSSIBLE_CIDR_ATTRIBUTES_TYPES = [
    "ip-src",
    "ip-src|port",
    "ip-dst",
    "ip-dst|port",
    "domain|ip",
]
BULK_BUFFER = []
BULK_SIZE = 100


def get_correlations(params: dict, page: int = 0, from_value: int = 0, size: int = 100):
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

    if params.get("source_attribute_uuid"):
        query["query"]["bool"]["must"].append(
            {"term": {"source_attribute_uuid.keyword": params["source_attribute_uuid"]}}
        )
    if params.get("source_event_uuid"):
        query["query"]["bool"]["must"].append(
            {"term": {"source_event_uuid.keyword": params["source_event_uuid"]}}
        )
    if params.get("target_attribute_uuid"):
        query["query"]["bool"]["must"].append(
            {"term": {"target_attribute_uuid.keyword": params["target_attribute_uuid"]}}
        )
    if params.get("target_event_uuid"):
        query["query"]["bool"]["must"].append(
            {"term": {"target_event_uuid.keyword": params["target_event_uuid"]}}
        )
    if params.get("match_type"):
        query["query"]["bool"]["must"].append(
            {"term": {"match_type.keyword": params["match_type"]}}
        )
    if not query["query"]["bool"]["must"]:
        query = {"query": {"match_all": {}}, "from": from_value, "size": size}

    response = OpenSearchClient.search(
        index="misp-attribute-correlations",
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


def get_attributes(filters: dict = {}):
    OpenSearchClient = get_opensearch_client()

    query = {"query": {"bool": {"must": [{"term": {"disable_correlation": False}}]}}}

    if filters.get("event_uuid"):
        query["query"]["bool"]["must"].append(
            {"term": {"event_uuid.keyword": filters["event_uuid"]}}
        )

    scroll = opensearch_helpers.scan(
        client=OpenSearchClient,
        index="misp-attributes",
        query=query,
        scroll="2m",
        size=500,
    )
    for doc in scroll:
        yield doc


def build_query(uuid, event_uuid, value, match_type, runtimeSettings: RuntimeSettings):

    if uuid is None:
        logger.error(f"build_query: UUID is None, event_uuid={event_uuid}")
        raise ValueError("uuid cannot be None in build_query")    
    if event_uuid is None:
        logger.error(f"build_query: event_uuid is None, uuid={uuid}")
        raise ValueError("event_uuid cannot be None in build_query")

    query = {
        "query": {
            "bool": {
                "must": [],
                "must_not": [
                    {"term": {"uuid.keyword": uuid}},
                    {"term": {"event_uuid.keyword": event_uuid}},
                ],
            }
        }
    }

    if match_type == "term":
        query["query"]["bool"]["must"] = [{"term": {"value.keyword": value}}]
    elif match_type == "prefix":
        query["query"]["bool"]["must"] = [
            {
                "prefix": {
                    "value.keyword": value[
                        : runtimeSettings.get_value(
                            "correlations.prefixLength", CORRELATION_PREFIX_LENGTH
                        )
                    ]
                }
            }
        ]
    elif match_type == "fuzzy":
        query["query"]["bool"]["must"] = [
            {
                "fuzzy": {
                    "value": {
                        "value": value,
                        "fuzziness": runtimeSettings.get_value(
                            "correlations.fuzzynessAlgo", CORRELATION_FUZZYNESS
                        ),
                    }
                }
            }
        ]
    else:
        raise ValueError(f"Unsupported match_type: {match_type}")

    return query


def build_cidr_query(uuid, event_uuid, doc):
    if (
        doc["_source"]["type"] in ["ip-src", "ip-dst"]
        and "/" in doc["_source"]["value"]
    ):
        cidr = doc["_source"]["value"]
    elif doc["_source"]["type"] in ["ip-src|port", "ip-dst|port"]:
        cidr = doc["_source"]["value"].split("/")[0]
    elif doc["_source"]["type"] == "domain|ip":
        cidr = doc["_source"]["value"].split("/")[1]
    else:
        raise ValueError(f"Unsupported CIDR type: {doc['_source']['type']}")

    if "/" not in cidr:
        raise ValueError(f"Invalid CIDR format: {cidr}")

    return {
        "query": {
            "bool": {
                "must": [{"term": {"expanded.ip": cidr}}],
                "must_not": [
                    {"term": {"uuid.keyword": uuid}},
                    {"term": {"event_uuid.keyword": event_uuid}},
                ],
            }
        }
    }


def flush_bulk_correlations():
    global BULK_BUFFER

    OpenSearchClient = get_opensearch_client()

    if not BULK_BUFFER:
        return

    opensearch_helpers.bulk(OpenSearchClient, BULK_BUFFER)
    BULK_BUFFER = []


def store_correlations_bulk(
    attribute_uuid, event_uuid, hits, match_type, runtimeSettings: RuntimeSettings
):
    if not hits:
        return

    for hit in hits:
        correlation_doc = {
            "_index": "misp-attribute-correlations",
            "_id": f"{attribute_uuid}|{hit['_id']}|{match_type}",
            "_source": {
                "source_attribute_uuid": attribute_uuid,
                "source_attribute_type": hit["_source"]["type"],
                "source_event_uuid": event_uuid,
                "target_attribute_uuid": hit["_id"],
                "target_attribute_type": hit["_source"]["type"],
                "target_attribute_value": hit["_source"]["value"],
                "target_event_uuid": hit["_source"]["event_uuid"],
                "match_type": match_type,
                "score": hit["_score"],
                "@timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            },
        }

        BULK_BUFFER.append(correlation_doc)

        tasks.handle_created_correlation.delay(
            attribute_uuid,
            correlation_doc["_source"]["source_event_uuid"],
            correlation_doc["_source"]["target_event_uuid"],
            correlation_doc["_source"]["target_attribute_uuid"],
            correlation_doc["_source"]["target_attribute_type"],
            correlation_doc["_source"]["target_attribute_value"],
        )

        if len(BULK_BUFFER) >= runtimeSettings.get_value(
            "correlations.opensearchFlushBulkSize", BULK_SIZE
        ):
            flush_bulk_correlations()


def correlate_document(doc, runtimeSettings: RuntimeSettings):
    OpenSearchClient = get_opensearch_client()

    value = doc["_source"].get("value")
    event_uuid = doc["_source"].get("event_uuid")

    if not value:
        return

    if not event_uuid:
        logger.warning(
            f"correlate_document: skipping attribute {doc['_id']} - event_uuid is None"
        )
        return

    match_types = runtimeSettings.get_value("correlations.matchTypes", ["term", "cidr"])

    for match_type in match_types:
        if match_type == "cidr":
            if (
                doc["_source"]["type"]
                not in runtimeSettings.get_value(
                    "correlations.possibleCdirAttributeTypes",
                    POSSIBLE_CIDR_ATTRIBUTES_TYPES,
                )
                or "/" not in value
            ):
                continue
            query = build_cidr_query(doc["_id"], doc["_source"]["event_uuid"], doc)
        else:
            try:
                query = build_query(
                    doc["_id"],
                    doc["_source"]["event_uuid"],
                    value,
                    match_type,
                    runtimeSettings,
                )
            except ValueError as e:
                logger.error(f"correlate_document: {str(e)}")
                continue

        res = OpenSearchClient.search(
            index="misp-attributes",
            body=query,
            size=runtimeSettings.get_value(
                "correlations.maxCorrelationsPerDoc",
                runtimeSettings.get_value(
                    "correlations.opensearchFlushBulkSize", MAX_CORRELATIONS_PER_DOC
                ),
            ),
        )

        store_correlations_bulk(
            doc["_id"],
            doc["_source"]["event_uuid"],
            res["hits"]["hits"],
            match_type,
            runtimeSettings,
        )


def get_top_correlated_events(source_event_uuid: str):
    OpenSearchClient = get_opensearch_client()

    query = {
        "size": 0,
        "query": {"term": {"source_event_uuid.keyword": source_event_uuid}},
        "aggs": {
            "by_target_event": {
                "terms": {"field": "target_event_uuid.keyword", "size": 10}
            }
        },
    }

    response = OpenSearchClient.search(
        index="misp-attribute-correlations",
        body=query,
    )

    return (
        response.get("aggregations", {}).get("by_target_event", {}).get("buckets", [])
    )


def run_correlations(runtimeSettings: RuntimeSettings, filters: dict = {}):

    for doc in get_attributes(filters):
        correlate_document(doc, runtimeSettings)

    flush_bulk_correlations()

    return True


def get_top_correlating_events():
    OpenSearchClient = get_opensearch_client()

    top_correlated_events_query = {
        "size": 0,
        "aggs": {
            "by_source_event": {
                "terms": {"field": "source_event_uuid.keyword", "size": 10}
            }
        },
    }

    top_correlated_events = OpenSearchClient.search(
        index="misp-attribute-correlations",
        body=top_correlated_events_query,
    )

    return (
        top_correlated_events.get("aggregations", {})
        .get("by_source_event", {})
        .get("buckets", [])
    )


def get_top_correlating_attributes():
    OpenSearchClient = get_opensearch_client()

    top_correlated_attributes_query = {
        "size": 0,
        "aggs": {
            "by_target_attribute": {
                "terms": {"field": "target_attribute_uuid.keyword", "size": 10},
                "aggs": {
                    "top_attribute_info": {
                        "top_hits": {
                            "size": 1,
                            "_source": {
                                "includes": [
                                    "target_attribute_type",
                                    "target_attribute_value",
                                    "target_event_uuid",
                                ]
                            },
                        }
                    }
                },
            }
        },
    }

    top_correlated_attributes = OpenSearchClient.search(
        index="misp-attribute-correlations",
        body=top_correlated_attributes_query,
    )

    return (
        top_correlated_attributes.get("aggregations", {})
        .get("by_target_attribute", {})
        .get("buckets", [])
    )


def get_total_correlations():
    OpenSearchClient = get_opensearch_client()

    total_correlations = OpenSearchClient.count(index="misp-attribute-correlations")

    return total_correlations["count"]


def get_correlations_stats():

    return {
        "top_correlated_events": get_top_correlating_events(),
        "top_correlated_attributes": get_top_correlating_attributes(),
        "total_correlations": get_total_correlations(),
    }


def delete_correlations():
    OpenSearchClient = get_opensearch_client()

    try:
        mapping = OpenSearchClient.indices.get_mapping(
            index="misp-attribute-correlations"
        )

        OpenSearchClient.indices.delete(index="misp-attribute-correlations")

        OpenSearchClient.indices.create(
            index="misp-attribute-correlations",
            body={
                "mappings": mapping["misp-attribute-correlations"]["mappings"],
            },
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete correlations index: {str(e)}",
        )

    return {"message": "Correlations index deleted successfully."}


def delete_event_correlations(event_uuid: str):
    OpenSearchClient = get_opensearch_client()

    query = {
        "query": {
            "bool": {
                "should": [
                    {"term": {"source_event_uuid.keyword": str(event_uuid)}},
                    {"term": {"target_event_uuid.keyword": str(event_uuid)}},
                ]
            }
        }
    }

    try:
        OpenSearchClient.delete_by_query(
            index="misp-attribute-correlations",
            body=query,
            refresh=True,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete correlations for event {event_uuid}: {str(e)}",
        )

    return {"message": f"Correlations for event {event_uuid} deleted successfully."}

def correlate_event(runtimeSettings: RuntimeSettings, event_uuid: str):
    run_correlations(
        runtimeSettings,
        filters={"event_uuid": event_uuid}
    )

    return {"message": f"Correlations for event {event_uuid} created successfully."}