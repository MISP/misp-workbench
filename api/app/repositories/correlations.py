from app.dependencies import get_opensearch_client
from fastapi import HTTPException, status
from opensearchpy import helpers as opensearch_helpers
import datetime

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


def get_correlations(page: int = 0, from_value: int = 0, size: int = 100):
    OpenSearchClient = get_opensearch_client()

    response = OpenSearchClient.search(
        index="misp-attribute-correlations",
        body={"query": {"match_all": {}}, "from": from_value, "size": size},
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


def get_all_attributes():
    OpenSearchClient = get_opensearch_client()

    scroll = opensearch_helpers.scan(
        client=OpenSearchClient,
        index="misp-attributes",
        query={"query": {"bool": {"must": [{"term": {"disable_correlation": False}}]}}},
        scroll="2m",
        size=500,
    )
    for doc in scroll:
        yield doc


def build_query(uuid, value, match_type):

    query = {
        "query": {"bool": {"must": [], "must_not": [{"term": {"uuid.keyword": uuid}}]}}
    }

    if match_type == "term":
        query["query"]["bool"]["must"] = [{"term": {"value.keyword": value}}]
    elif match_type == "prefix":
        query["query"]["bool"]["must"] = [
            {"prefix": {"value.keyword": value[:CORRELATION_PREFIX_LENGTH]}}
        ]
    elif match_type == "fuzzy":
        query["query"]["bool"]["must"] = [
            {"fuzzy": {"value": {"value": value, "fuzziness": CORRELATION_FUZZYNESS}}}
        ]
    else:
        raise ValueError(f"Unsupported match_type: {match_type}")

    return query


def build_cidr_query(uuid, doc):
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
                "must_not": [{"term": {"uuid.keyword": uuid}}],
            }
        }
    }


def store_correlations_bulk(source_id, hits, match_type):
    if not hits:
        return

    OpenSearchClient = get_opensearch_client()

    correlations = []

    for hit in hits:
        correlation_doc = {
            "_index": "misp-attribute-correlations",
            "_id": f"{source_id}|{hit['_id']|{match_type}}",
            "_source": {
                "source_id": source_id,
                "target_id": hit["_id"],
                "match_type": match_type,
                "score": hit["_score"],
                "@timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            },
        }

        correlations.append(correlation_doc)

    opensearch_helpers.bulk(OpenSearchClient, correlations)


def correlate_document(doc):
    OpenSearchClient = get_opensearch_client()

    value = doc["_source"].get("value")
    doc_id = doc["_id"]

    if not value:
        return

    # match_types = ["term", "fuzzy", "prefix", "cidr", "phrase"]  # customizable
    match_types = ["term", "cidr"]

    for match_type in match_types:
        if match_type == "cidr":
            if (
                doc["_source"]["type"] in POSSIBLE_CIDR_ATTRIBUTES_TYPES
                and "/" in value
            ):
                query = build_cidr_query(doc["_id"], doc)
            else:
                continue
        else:
            query = build_query(doc["_id"], value, match_type)

        res = OpenSearchClient.search(
            index="misp-attributes",
            body=query,
            size=MAX_CORRELATIONS_PER_DOC,
        )

        store_correlations_bulk(doc_id, res["hits"]["hits"], match_type)


def run_correlations():

    for doc in get_all_attributes():
        correlate_document(doc)

    return {
        "status": "success",
        "message": "Correlations generated successfully.",
    }
