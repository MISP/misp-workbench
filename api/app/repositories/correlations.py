from app.services.opensearch import get_opensearch_client
from app.schemas import correlation as correlation_schemas
from fastapi import HTTPException, status
from opensearchpy import helpers as opensearch_helpers
from opensearchpy.exceptions import NotFoundError
from app.services.runtime_settings import RuntimeSettings
from app.worker import tasks
import datetime
import json
import logging

logger = logging.getLogger(__name__)

MAX_CORRELATIONS_PER_DOC = 1000
# Match types that find a value without matching it exactly.
APPROXIMATE_MATCH_TYPES = ("fuzzy", "prefix")
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
BULK_SIZE = 100
# Correlation queries batched into a single multi-search request. Raising it
# means fewer round trips but a larger response to hold in memory, since every
# query can bring back up to ``maxCorrelationsPerDoc`` hits.
MSEARCH_CHUNK_SIZE = 25
MGET_CHUNK_SIZE = 500
DELETE_CHUNK_SIZE = 1000
NOTIFICATION_CHUNK_SIZE = 200
# Only the fields correlation needs, so batched responses stay small.
CORRELATION_SOURCE_FIELDS = [
    "type",
    "value",
    "event_uuid",
    "disable_correlation",
    "deleted",
]


def get_correlations(params: correlation_schemas.CorrelationQueryParams, page: int = 0, from_value: int = 0, size: int = 100):
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

    if params.source_attribute_uuid:
        query["query"]["bool"]["must"].append(
            {"term": {"source_attribute_uuid.keyword": params.source_attribute_uuid}}
        )
    if params.source_event_uuid:
        query["query"]["bool"]["must"].append(
            {"term": {"source_event_uuid.keyword": params.source_event_uuid}}
        )
    if params.target_attribute_uuid:
        query["query"]["bool"]["must"].append(
            {"term": {"target_attribute_uuid.keyword": params.target_attribute_uuid}}
        )
    if params.target_event_uuid:
        query["query"]["bool"]["must"].append(
            {"term": {"target_event_uuid.keyword": params.target_event_uuid}}
        )
    if params.match_type:
        query["query"]["bool"]["must"].append(
            {"term": {"match_type.keyword": params.match_type}}
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

    query = {
        "query": {"bool": {"must": [{"term": {"disable_correlation": False}}]}},
        "_source": CORRELATION_SOURCE_FIELDS,
    }

    if filters.get("event_uuid"):
        query["query"]["bool"]["must"].append(
            {"term": {"event_uuid": filters["event_uuid"]}}
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


def value_parts(value, attribute_type=None):
    """The components of a composite value, or just the value itself.

    MISP composite types - ``domain|ip``, ``filename|sha256`` and friends - join
    two values with a pipe, and each component is an indicator in its own right.
    The port of a ``...|port`` type is not: it would correlate with every address
    sharing it, so only the address counts.

    Kept in step with the misp-attributes_value_parts ingest pipeline, which
    fills the field this is matched against.
    """
    components = str(value or "").split("|")

    if str(attribute_type or "").endswith("|port"):
        components = components[:1]

    parts = []
    for part in components:
        part = part.strip()
        if part and part not in parts:
            parts.append(part)

    return parts


def build_term_match(value, attribute_type=None):
    """Match a value exactly, or on any component it shares with another.

    Without this a ``domain|ip`` of ``evil.com|1.2.3.4`` would only ever
    correlate with the identical composite, never with a bare ``domain`` of
    ``evil.com``. The components are matched through ``expanded.value_parts``,
    which the misp-attributes_value_parts ingest pipeline fills in; the exact
    clause is kept so attributes indexed before that pipeline existed still
    correlate on their full value.
    """
    return {
        "bool": {
            "should": [
                {"term": {"value.keyword": value}},
                {
                    "terms": {
                        "expanded.value_parts": value_parts(value, attribute_type)
                    }
                },
            ],
            "minimum_should_match": 1,
        }
    }


def build_query(
    uuid,
    event_uuid,
    value,
    match_type,
    runtimeSettings: RuntimeSettings,
    attribute_type=None,
):

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
                    {"term": {"event_uuid": event_uuid}},
                ],
            }
        }
    }

    if match_type == "term":
        query["query"]["bool"]["must"] = [build_term_match(value, attribute_type)]
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
        cidr = doc["_source"]["value"].split("|")[0]
    elif doc["_source"]["type"] == "domain|ip":
        cidr = doc["_source"]["value"].split("|")[1]
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
                    {"term": {"event_uuid": event_uuid}},
                ],
            }
        }
    }


def is_approximate_match(match_type) -> bool:
    return match_type in APPROXIMATE_MATCH_TYPES


def chunked(iterable, size):
    """Yield successive ``size`` long chunks of an iterable (streams generators)."""
    chunk = []

    for item in iterable:
        chunk.append(item)
        if len(chunk) >= size:
            yield chunk
            chunk = []

    if chunk:
        yield chunk


def attribute_ref(doc):
    """Reduce an OpenSearch attribute hit to the fields a correlation doc needs."""
    return {
        "uuid": doc["_id"],
        "type": doc["_source"].get("type"),
        "value": doc["_source"].get("value"),
        "event_uuid": doc["_source"].get("event_uuid"),
    }


def is_correlatable(doc):
    """Whether an indexed attribute may take part in correlations.

    TODO: exclude warninglisted values. Values like 8.8.8.8, the RFC1918
    ranges, the empty file hashes or anything in the Alexa/Cisco top lists
    correlate with almost everything and bury the real signal - which is what
    ``correlations.maxCorrelationsPerDoc`` is currently papering over. MISP
    ships warninglists for exactly this; enforcing them here (and at ingest,
    see the TODO in attributes_repository.create_attribute_from_pulled_attribute)
    would cut both the noise and the correlation volume.
    """
    source = doc["_source"]

    if not source.get("value"):
        return False

    if not source.get("event_uuid"):
        logger.warning(
            "is_correlatable: skipping attribute %s - event_uuid is None", doc["_id"]
        )
        return False

    if source.get("disable_correlation"):
        return False

    if source.get("deleted"):
        return False

    return True


def event_correlation_disabled(event_uuid):
    """Read the event level disable_correlation flag straight from the index."""
    OpenSearchClient = get_opensearch_client()

    try:
        doc = OpenSearchClient.get(
            index="misp-events",
            id=str(event_uuid),
            _source_includes=["disable_correlation"],
        )
    except NotFoundError:
        return False

    return bool(doc["_source"].get("disable_correlation", False))


def build_correlation_doc(source, target, match_type, score):
    """Build the bulk action for a single directed source -> target correlation."""
    return {
        "_index": "misp-attribute-correlations",
        "_id": f"{source['uuid']}|{target['uuid']}|{match_type}",
        "_source": {
            "source_attribute_uuid": source["uuid"],
            "source_attribute_type": source["type"],
            "source_event_uuid": source["event_uuid"],
            "target_attribute_uuid": target["uuid"],
            "target_attribute_type": target["type"],
            "target_attribute_value": target["value"],
            "target_event_uuid": target["event_uuid"],
            "match_type": match_type,
            "score": score,
            "@timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        },
    }


def correlation_notification_payload(correlation_source):
    """The subset of a correlation doc that notifications and the reactor consume."""
    return {
        "source_attribute_uuid": correlation_source["source_attribute_uuid"],
        "source_event_uuid": correlation_source["source_event_uuid"],
        "target_event_uuid": correlation_source["target_event_uuid"],
        "target_attribute_uuid": correlation_source["target_attribute_uuid"],
        "target_attribute_type": correlation_source["target_attribute_type"],
        "target_attribute_value": correlation_source["target_attribute_value"],
    }


def dispatch_correlation_notifications(correlation_docs):
    """Hand new correlations to the notification worker in batches.

    One task per correlation is what makes a bulk ingest expensive, so the
    payloads are grouped and a single task handles each group.
    """
    payloads = [
        correlation_notification_payload(doc["_source"]) for doc in correlation_docs
    ]

    for chunk in chunked(payloads, NOTIFICATION_CHUNK_SIZE):
        tasks.handle_created_correlations.delay(chunk)


def min_score_for(match_type, runtimeSettings: RuntimeSettings):
    """The score floor to apply to a match type, or None to apply none.

    Only approximate matching produces a score worth thresholding. A term or
    cidr hit is exact, and its score says nothing about the quality of the
    match, so a floor there would only throw away correct correlations.
    """
    if not is_approximate_match(match_type):
        return None

    min_score = runtimeSettings.get_value("correlations.minScore", CORRELATION_MIN_SCORE)

    return min_score if min_score and min_score > 0 else None


def build_correlation_queries(doc, runtimeSettings: RuntimeSettings):
    """Return the ``(match_type, query)`` pairs configured for an attribute."""
    queries = []
    value = doc["_source"].get("value")
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
            queries.append(
                (
                    match_type,
                    build_cidr_query(doc["_id"], doc["_source"]["event_uuid"], doc),
                )
            )
        else:
            try:
                queries.append(
                    (
                        match_type,
                        build_query(
                            doc["_id"],
                            doc["_source"]["event_uuid"],
                            value,
                            match_type,
                            runtimeSettings,
                            doc["_source"].get("type"),
                        ),
                    )
                )
            except ValueError as e:
                logger.error(f"build_correlation_queries: {str(e)}")

    return queries


def correlation_query_key(match_type, query):
    """Key identifying a correlation query, so identical ones run only once.

    The self-exclusion on ``uuid`` is deliberately left out of the key: the
    query also excludes the attribute's whole event, and an attribute always
    belongs to its own event, so two attributes of the same event looking for
    the same value get exactly the same hits either way.
    """
    bool_query = query["query"]["bool"]
    must_not = [
        clause
        for clause in bool_query["must_not"]
        if "uuid.keyword" not in clause.get("term", {})
    ]

    return json.dumps(
        {
            "match_type": match_type,
            "must": bool_query["must"],
            "must_not": must_not,
        },
        sort_keys=True,
    )


def run_correlation_msearch(queries, size):
    """Run several correlation queries in a single multi-search request."""
    OpenSearchClient = get_opensearch_client()

    body = []
    for query, min_score in queries:
        search = {**query, "size": size, "_source": CORRELATION_SOURCE_FIELDS}

        if min_score is not None:
            search["min_score"] = min_score

        body.append({"index": "misp-attributes"})
        body.append(search)

    responses = OpenSearchClient.msearch(body=body)["responses"]

    results = []
    for response in responses:
        if "error" in response:
            logger.error("correlation multi-search failed: %s", response["error"])
            results.append([])
            continue

        results.append([hit for hit in response["hits"]["hits"] if is_correlatable(hit)])

    return results


def max_correlations_per_doc(runtimeSettings: RuntimeSettings):
    return runtimeSettings.get_value(
        "correlations.maxCorrelationsPerDoc",
        runtimeSettings.get_value(
            "correlations.opensearchFlushBulkSize", MAX_CORRELATIONS_PER_DOC
        ),
    )


def build_chunk_correlation_docs(
    docs, runtimeSettings: RuntimeSettings, bidirectional: bool
):
    """Build the correlation docs for a chunk of attributes in one round trip."""
    plan = []
    queries = {}

    for doc in docs:
        if not is_correlatable(doc):
            continue

        for match_type, query in build_correlation_queries(doc, runtimeSettings):
            key = correlation_query_key(match_type, query)
            queries.setdefault(key, (query, min_score_for(match_type, runtimeSettings)))
            plan.append((doc, match_type, key))

    if not plan:
        return []

    keys = list(queries)
    hits_by_key = dict(
        zip(
            keys,
            run_correlation_msearch(
                [queries[key] for key in keys], max_correlations_per_doc(runtimeSettings)
            ),
        )
    )

    correlation_docs = {}
    for doc, match_type, key in plan:
        source = attribute_ref(doc)

        for hit in hits_by_key.get(key, []):
            if hit["_id"] == doc["_id"]:
                continue

            target = attribute_ref(hit)
            score = hit["_score"]

            forward = build_correlation_doc(source, target, match_type, score)
            correlation_docs.setdefault(forward["_id"], forward)

            if bidirectional:
                reverse = build_correlation_doc(target, source, match_type, score)
                correlation_docs.setdefault(reverse["_id"], reverse)

    return list(correlation_docs.values())


def index_correlation_docs(correlation_docs):
    """Index correlation docs and return the ones that were actually new.

    Documents are written with ``op_type=create``, so re-correlating an
    attribute that already has its correlations stored costs nothing and, more
    importantly, does not notify followers a second time.
    """
    OpenSearchClient = get_opensearch_client()

    actions = [{**doc, "_op_type": "create"} for doc in correlation_docs]

    _, errors = opensearch_helpers.bulk(
        OpenSearchClient, actions, raise_on_error=False
    )

    skipped = set()
    for error in errors:
        info = error.get("create", {})
        skipped.add(info.get("_id"))

        if info.get("status") != 409:
            logger.error(
                "failed to index correlation %s: %s",
                info.get("_id"),
                info.get("error"),
            )

    return [doc for doc in correlation_docs if doc["_id"] not in skipped]


def correlate_attributes(
    runtimeSettings: RuntimeSettings,
    docs,
    bidirectional: bool = True,
    known_correlation_ids=None,
):
    """Correlate a batch of indexed attributes with as few round trips as possible.

    ``docs`` may be a generator, so a whole event or the entire index can be
    streamed through without being held in memory. Per chunk there is one
    multi-search for the matching and one bulk request for the writing, and the
    resulting notifications are dispatched in batches.

    Correlations are stored in both directions unless ``bidirectional`` is off:
    the attributes that were already indexed have to expose the incoming ones as
    well, and every consumer looks correlations up by ``source_attribute_uuid``.
    A full run visits every attribute anyway, so it can skip the reverse writes.
    """
    known = known_correlation_ids or set()
    chunk_size = runtimeSettings.get_value(
        "correlations.msearchChunkSize", MSEARCH_CHUNK_SIZE
    )
    flush_size = runtimeSettings.get_value(
        "correlations.opensearchFlushBulkSize", BULK_SIZE
    )

    stored = 0
    pending = []

    def flush():
        nonlocal stored, pending

        if not pending:
            return

        created = index_correlation_docs(pending)
        stored += len(created)
        dispatch_correlation_notifications(
            [doc for doc in created if doc["_id"] not in known]
        )
        pending = []

    for chunk in chunked(docs, chunk_size):
        pending.extend(
            build_chunk_correlation_docs(chunk, runtimeSettings, bidirectional)
        )

        if len(pending) >= flush_size:
            flush()

    flush()

    if stored:
        refresh_correlations_index()

    return {"stored": stored}


def refresh_correlations_index():
    """Make the correlations just written visible to searches.

    Only called after a write reported documents as created, so a missing index
    means something removed it underneath the run - a concurrent
    ``delete_correlations``, most likely. The correlations are lost, but the run
    itself has nothing left to do about it, so it is logged and not raised.
    """
    try:
        get_opensearch_client().indices.refresh(index="misp-attribute-correlations")
    except NotFoundError:
        logger.error(
            "refresh_correlations_index: index misp-attribute-correlations is missing, "
            "the correlations just written were dropped with it"
        )


def skip_uncorrelated_events(docs):
    """Drop the attributes whose event has correlation disabled.

    The flag is read once per event rather than once per attribute: a bulk
    ingest batch normally belongs to a single event.
    """
    disabled_by_event = {}

    for doc in docs:
        event_uuid = doc["_source"].get("event_uuid")

        if event_uuid not in disabled_by_event:
            disabled_by_event[event_uuid] = event_correlation_disabled(event_uuid)

        if not disabled_by_event[event_uuid]:
            yield doc


def get_attributes_by_uuid(attribute_uuids):
    """Yield the indexed attributes for a list of uuids, one mget per chunk."""
    OpenSearchClient = get_opensearch_client()

    for chunk in chunked(attribute_uuids, MGET_CHUNK_SIZE):
        response = OpenSearchClient.mget(
            index="misp-attributes",
            body={"ids": [str(attribute_uuid) for attribute_uuid in chunk]},
            _source_includes=CORRELATION_SOURCE_FIELDS,
        )

        for doc in response["docs"]:
            if doc.get("found"):
                yield doc
            else:
                logger.warning(
                    "get_attributes_by_uuid: attribute %s is not indexed", doc["_id"]
                )


def correlate_attribute(runtimeSettings: RuntimeSettings, attribute_uuid: str):
    """Correlate a single attribute, as fired when one is created or changed."""
    OpenSearchClient = get_opensearch_client()

    try:
        doc = OpenSearchClient.get(
            index="misp-attributes",
            id=str(attribute_uuid),
            _source_includes=CORRELATION_SOURCE_FIELDS,
        )
    except NotFoundError:
        logger.warning(
            "correlate_attribute: attribute %s is not indexed", attribute_uuid
        )
        return {"stored": 0}

    # Anything stored before is stale: the value, the type or the correlation
    # flag may have changed since the attribute was last correlated.
    known_correlation_ids = get_attribute_correlation_ids(attribute_uuid)
    delete_attributes_correlations([attribute_uuid])

    if not is_correlatable(doc) or event_correlation_disabled(
        doc["_source"]["event_uuid"]
    ):
        return {"stored": 0}

    return correlate_attributes(
        runtimeSettings, [doc], known_correlation_ids=known_correlation_ids
    )


def correlate_attribute_uuids(
    runtimeSettings: RuntimeSettings, attribute_uuids, rebuild: bool = False
):
    """Correlate the batch of attributes a bulk ingest produced.

    ``rebuild`` is for attributes that already existed: their stored
    correlations are dropped first because the value they matched on may have
    changed. Freshly created attributes have nothing to drop, and the
    ``op_type=create`` write keeps the run idempotent either way.
    """
    if not attribute_uuids:
        return {"stored": 0}

    if rebuild:
        delete_attributes_correlations(attribute_uuids)

    docs = skip_uncorrelated_events(get_attributes_by_uuid(attribute_uuids))

    return correlate_attributes(runtimeSettings, docs)


def search_correlations(
    query: str = None,
    page: int = 0,
    from_value: int = 0,
    size: int = 10,
    sort_by: str = "@timestamp",
    sort_order: str = "desc",
):
    OpenSearchClient = get_opensearch_client()

    search_body = {
        "query": {
            "query_string": {
                "query": query or "*",
                "default_field": "target_attribute_value",
            }
        },
        "from": from_value,
        "size": size,
        "sort": [{sort_by: {"order": sort_order}}],
    }

    try:
        response = OpenSearchClient.search(
            index="misp-attribute-correlations",
            body=search_body,
        )
    except NotFoundError:
        return {
            "page": page,
            "size": size,
            "total": 0,
            "took": 0,
            "timed_out": False,
            "max_score": None,
            "results": [],
        }

    return {
        "page": page,
        "size": size,
        "total": response["hits"]["total"]["value"],
        "took": response["took"],
        "timed_out": response["timed_out"],
        "max_score": response["hits"]["max_score"],
        "results": response["hits"]["hits"],
    }


def search_correlations_histogram(query: str = None, interval: str = "1d"):
    OpenSearchClient = get_opensearch_client()

    search_body = {
        "size": 0,
        "query": {
            "query_string": {
                "query": query or "*",
                "default_field": "target_attribute_value",
            }
        },
        "aggs": {
            "correlations_over_time": {
                "date_histogram": {
                    "field": "@timestamp",
                    "calendar_interval": interval,
                    "min_doc_count": 0,
                }
            }
        },
    }

    try:
        response = OpenSearchClient.search(
            index="misp-attribute-correlations",
            body=search_body,
        )
    except NotFoundError:
        return {"buckets": []}

    return {
        "buckets": response["aggregations"]["correlations_over_time"]["buckets"]
    }


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
    # A full run visits every attribute, so each pair is written when its own
    # side comes up and the reverse writes would only duplicate the work.
    correlate_attributes(
        runtimeSettings, get_attributes(filters), bidirectional=bool(filters)
    )

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


# TODO: aggregate event pairs server side, for the overview network view. A
# terms aggregation on source_event_uuid with a sub-aggregation on
# target_event_uuid would give every connected pair and its weight over the
# whole index in one request. The frontend currently samples the 300 most
# recent correlation documents and folds them client side, which is honest
# about being a sample but is neither complete nor cheap.
def get_correlations_stats():
    try:
        return {
            "top_correlated_events": get_top_correlating_events(),
            "top_correlated_attributes": get_top_correlating_attributes(),
            "total_correlations": get_total_correlations(),
        }
    except NotFoundError:
        return {
            "top_correlated_events": [],
            "top_correlated_attributes": [],
            "total_correlations": 0,
        }


def delete_correlations():
    """Drop and recreate the correlations index, keeping its mapping.

    The mapping is carried over from the live index rather than reapplied from
    ``opensearch/mappings/misp-attribute-correlations.json``, which is what the
    opensearch container provisions it from, so a recreate here cannot drift
    from what was actually in use.
    """
    OpenSearchClient = get_opensearch_client()

    try:
        try:
            mapping = OpenSearchClient.indices.get_mapping(
                index="misp-attribute-correlations"
            )["misp-attribute-correlations"]["mappings"]
        except NotFoundError:
            # Nothing to drop. The index is recreated so the provisioned
            # mapping is not silently replaced by a dynamic one on first write.
            logger.info(
                "delete_correlations: index is missing, recreating it empty"
            )
            mapping = None

        if mapping is not None:
            OpenSearchClient.indices.delete(index="misp-attribute-correlations")

        OpenSearchClient.indices.create(
            index="misp-attribute-correlations",
            body={"mappings": mapping} if mapping else None,
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


def build_attribute_correlations_query(attribute_uuids):
    """Match every correlation doc referencing the attributes, in both directions."""
    ids = [str(attribute_uuid) for attribute_uuid in attribute_uuids]

    return {
        "query": {
            "bool": {
                "should": [
                    {"terms": {"source_attribute_uuid.keyword": ids}},
                    {"terms": {"target_attribute_uuid.keyword": ids}},
                ]
            }
        }
    }


def get_attribute_correlation_ids(attribute_uuid: str):
    """Ids of the correlation docs currently stored for the attribute.

    Used to tell an actually new correlation from one that is merely being
    rebuilt, so re-correlating an attribute does not re-notify its followers.
    """
    OpenSearchClient = get_opensearch_client()

    body = build_attribute_correlations_query([attribute_uuid])
    body["_source"] = False
    body["size"] = MAX_CORRELATIONS_PER_DOC * 2

    try:
        response = OpenSearchClient.search(
            index="misp-attribute-correlations", body=body
        )
    except NotFoundError:
        return set()

    return {hit["_id"] for hit in response["hits"]["hits"]}


def delete_attributes_correlations(attribute_uuids):
    """Delete every correlation referencing the attributes, in both directions."""
    OpenSearchClient = get_opensearch_client()

    for chunk in chunked(attribute_uuids, DELETE_CHUNK_SIZE):
        try:
            OpenSearchClient.delete_by_query(
                index="misp-attribute-correlations",
                body=build_attribute_correlations_query(chunk),
                refresh=True,
                conflicts="proceed",
            )
        except NotFoundError:
            logger.info(
                "delete_attributes_correlations: correlations index is missing, nothing to delete"
            )
            return True

    return True


def delete_attribute_correlations(attribute_uuid: str):
    """Delete every correlation referencing the attribute, in both directions."""
    return delete_attributes_correlations([attribute_uuid])


def correlate_event(runtimeSettings: RuntimeSettings, event_uuid: str):
    run_correlations(runtimeSettings, filters={"event_uuid": event_uuid})

    return {"message": f"Correlations for event {event_uuid} created successfully."}