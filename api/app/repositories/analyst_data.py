import logging
from typing import Optional

from app.repositories.sync import ANALYST_DATA_INDEX
from app.schemas import analyst_data as analyst_data_schemas
from app.services.opensearch import get_opensearch_client
from opensearchpy.exceptions import NotFoundError

logger = logging.getLogger(__name__)

# A single event's analyst data, threads included. Far above any realistic
# volume, and it keeps the thread assembly to one round trip.
MAX_ANALYST_DATA_PER_EVENT = 10000

_TYPE_TO_FIELD = {
    "Note": "notes",
    "Opinion": "opinions",
    "Relationship": "relationships",
}


def _search(query: dict, size: int = MAX_ANALYST_DATA_PER_EVENT) -> list[dict]:
    OpenSearchClient = get_opensearch_client()

    body = {
        "query": {
            "bool": {
                "must": [query],
                "filter": [{"term": {"deleted": False}}],
            }
        },
        "size": size,
        "sort": [{"created": {"order": "asc", "missing": "_last"}}],
    }

    try:
        response = OpenSearchClient.search(index=ANALYST_DATA_INDEX, body=body)
    except NotFoundError:
        # The index is created by the OpenSearch entrypoint; treat a missing
        # one as "nothing captured yet" rather than an error.
        return []

    return [hit["_source"] for hit in response["hits"]["hits"]]


def _to_thread(document: dict) -> analyst_data_schemas.AnalystDataThread:
    return analyst_data_schemas.AnalystDataThread(
        uuid=document["uuid"],
        analyst_type=document["analyst_type"],
        object_uuid=document["object_uuid"],
        object_type=document["object_type"],
        data=document,
    )


def _build_threads(
    documents: list[dict],
    root_uuid: str,
    root_type: Optional[str] = None,
) -> analyst_data_schemas.AnalystDataListResponse:
    """
    Rebuild the analyst data threads for one parent out of flat documents.

    Ingest stores every note/opinion/relationship as its own document keyed by
    `object_uuid` + `object_type`, so a reply to a note points at the note's
    uuid. Grouping by that pair and then walking down from the root recovers
    the nesting MISP sent, at any depth.
    """
    children: dict[tuple, list[dict]] = {}
    for document in documents:
        key = (document.get("object_uuid"), document.get("object_type"))
        children.setdefault(key, []).append(document)

    def attach(parent_uuid: str, parent_type: Optional[str], seen: set):
        response = analyst_data_schemas.AnalystDataListResponse()

        # A parent's analyst data is keyed by the parent's own object type. The
        # root's type is matched loosely when unknown, since callers reading by
        # attribute or object uuid need not know which label MISP used.
        matches = []
        for (object_uuid, object_type), group in children.items():
            if object_uuid != parent_uuid:
                continue
            if parent_type is not None and object_type != parent_type:
                continue
            matches.extend(group)

        for document in matches:
            uuid = document["uuid"]
            if uuid in seen:
                continue
            seen.add(uuid)

            thread = _to_thread(document)
            nested = attach(uuid, document["analyst_type"], seen)
            thread.notes = nested.notes
            thread.opinions = nested.opinions
            thread.relationships = nested.relationships

            field = _TYPE_TO_FIELD.get(document["analyst_type"])
            if field:
                getattr(response, field).append(thread)

        return response

    return attach(root_uuid, root_type, set())


def get_analyst_data_by_event_uuid(
    event_uuid: str,
) -> analyst_data_schemas.AnalystDataListResponse:
    """
    Analyst data attached directly to an event, with its threads.

    Analyst data on the event's attributes and objects is captured under the
    same `event_uuid` but is not returned here -- read it by that object's
    uuid instead.
    """
    documents = _search({"term": {"event_uuid": str(event_uuid)}})

    return _build_threads(documents, str(event_uuid), "Event")


def get_analyst_data_by_object_uuid(
    object_uuid: str,
    object_type: Optional[str] = None,
) -> analyst_data_schemas.AnalystDataListResponse:
    """
    Analyst data attached to any object MISP supports -- an attribute, an
    object, an event report, a galaxy cluster -- with its threads.

    Nested replies are fetched by following the thread, so this issues one
    query per level rather than loading a whole event.
    """
    documents = _search(
        {"term": {"object_uuid": str(object_uuid)}},
    )

    # Replies live under their parent note's uuid, not the object's, so pull
    # the descendants in as well before assembling.
    frontier = [document["uuid"] for document in documents]
    collected = {document["uuid"]: document for document in documents}

    while frontier:
        nested = _search({"terms": {"object_uuid": frontier}})
        frontier = []
        for document in nested:
            if document["uuid"] not in collected:
                collected[document["uuid"]] = document
                frontier.append(document["uuid"])

    return _build_threads(list(collected.values()), str(object_uuid), object_type)


def get_all_analyst_data_for_event(event_uuid: str) -> list[dict]:
    """
    Every analyst data document captured for an event, flat and unthreaded --
    including the data attached to its attributes and objects.
    """
    return _search({"term": {"event_uuid": str(event_uuid)}})
