from app.dependencies import get_opensearch_client
from fastapi import HTTPException, status
from opensearchpy import helpers as opensearch_helpers
import datetime

MAX_CORRELATIONS_PER_DOC = 1000
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
        query={"query": {"match_all": {}}},
        scroll="2m",
        size=500,
    )
    for doc in scroll:
        yield doc


def build_query(value, match_type):
    if match_type == "term":
        return {"term": {"value.keyword": value}}
    elif match_type == "prefix":
        return {"prefix": {"value.keyword": value[:10]}}  # safety limit
    elif match_type == "fuzzy":
        return {"fuzzy": {"value": {"value": value, "fuzziness": "AUTO"}}}
    elif match_type == "wildcard":
        return {"wildcard": {"value.keyword": f"*{value}*"}}
    else:
        raise ValueError(f"Unsupported match_type: {match_type}")


def store_correlation(source_id, target_id, match_type, score):
    OpenSearchClient = get_opensearch_client()

    correlation_doc = {
        "source_id": source_id,
        "target_id": target_id,
        "match_type": match_type,
        "score": score,
        "@timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }
    OpenSearchClient.index(index="misp-attribute-correlations", body=correlation_doc)


def build_cidr_query(doc):
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

    return {"term": {"expanded.ip": cidr}}


def correlate_document(doc):
    OpenSearchClient = get_opensearch_client()

    value = doc["_source"].get("value")
    doc_id = doc["_id"]

    if not value:
        return

    # match_types = ["term", "fuzzy", "prefix", "cidr"]  # customizable
    match_types = ["term", "cidr"]

    for match_type in match_types:
        if match_type == "cidr":
            if (
                doc["_source"]["type"] in POSSIBLE_CIDR_ATTRIBUTES_TYPES
                and "/" in value
            ):
                query = build_cidr_query(doc)
            else:
                continue
        else:
            query = build_query(value, match_type)

        res = OpenSearchClient.search(
            index="misp-attributes",
            body={"query": query},
            size=MAX_CORRELATIONS_PER_DOC,
        )

        for hit in res["hits"]["hits"]:
            if hit["_id"] == doc_id:
                continue  # skip self

            store_correlation(doc_id, hit["_id"], match_type, hit["_score"])


def run_correlations():
    for doc in get_all_attributes():
        correlate_document(doc)
