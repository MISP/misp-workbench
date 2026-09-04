import datetime
import logging
import uuid as uuid_lib
from typing import Optional
from uuid import UUID

from app.auth.utils import role_has_scope
from app.models import user as user_models
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


def get_analyst_data_counts_for_event(event_uuid: str) -> dict[str, int]:
    """
    How much analyst data hangs off each of an event's objects, keyed by the
    object's uuid -- the event itself, its attributes, its objects.

    Counts the whole subtree, so a note with five replies contributes six. The
    alternative, counting only direct children, would show "1" for a long
    discussion.

    One query for the whole event, so a page can badge every attribute row
    without a request each.
    """
    documents = _search({"term": {"event_uuid": str(event_uuid)}})

    analyst_uuids = {document["uuid"] for document in documents}

    children: dict[str, list[dict]] = {}
    for document in documents:
        children.setdefault(document.get("object_uuid"), []).append(document)

    def subtree(parent_uuid: str, seen: set) -> int:
        total = 0
        for child in children.get(parent_uuid, []):
            if child["uuid"] in seen:
                continue
            seen.add(child["uuid"])
            total += 1 + subtree(child["uuid"], seen)
        return total

    # Only the parents that are not themselves analyst data: a reply is counted
    # inside its own thread's total rather than getting an entry of its own.
    return {
        parent_uuid: subtree(parent_uuid, set())
        for parent_uuid in children
        if parent_uuid and parent_uuid not in analyst_uuids
    }


def get_all_analyst_data_for_event(event_uuid: str) -> list[dict]:
    """
    Every analyst data document captured for an event, flat and unthreaded --
    including the data attached to its attributes and objects.
    """
    return _search({"term": {"event_uuid": str(event_uuid)}})


# ── Writes ────────────────────────────────────────────────────────────────────


def get_analyst_data_by_uuid(analyst_uuid: str) -> Optional[dict]:
    OpenSearchClient = get_opensearch_client()

    try:
        return OpenSearchClient.get(index=ANALYST_DATA_INDEX, id=str(analyst_uuid))[
            "_source"
        ]
    except NotFoundError:
        return None


def _resolve_parent(object_uuid: str, object_type: str) -> tuple[bool, Optional[str]]:
    """
    Check the parent exists and work out which event the analyst data belongs
    to. Returns (parent_exists, event_uuid).

    `event_uuid` is denormalised onto every document so all the analyst data
    for an event can be read in one query, including replies whose own
    object_uuid points at another note rather than at the event.
    """
    # Imported here: events/attributes/objects import this module's siblings,
    # and a module level import would close the cycle.
    from app.repositories import attributes as attributes_repository
    from app.repositories import events as events_repository
    from app.repositories import objects as objects_repository

    if object_type == "Event":
        event = events_repository.get_event_from_opensearch(UUID(object_uuid))
        return event is not None, object_uuid if event else None

    if object_type == "Attribute":
        attribute = attributes_repository.get_attribute_from_opensearch(
            UUID(object_uuid)
        )
        if attribute is None:
            return False, None
        return True, str(attribute.event_uuid) if attribute.event_uuid else None

    if object_type == "Object":
        misp_object = objects_repository.get_object_from_opensearch(UUID(object_uuid))
        if misp_object is None:
            return False, None
        return True, str(misp_object.event_uuid) if misp_object.event_uuid else None

    if object_type in ("Note", "Opinion", "Relationship"):
        # A reply inherits the event of the analyst data it hangs off.
        parent = get_analyst_data_by_uuid(object_uuid)
        if parent is None:
            return False, None
        return True, parent.get("event_uuid")

    if object_type == "EventReport":
        OpenSearchClient = get_opensearch_client()
        try:
            report = OpenSearchClient.get(
                index="misp-event-reports", id=str(object_uuid)
            )["_source"]
        except NotFoundError:
            return False, None
        return True, report.get("event_uuid")

    # A type this instance does not store locally (GalaxyCluster, Organisation,
    # ...). Accept it without an event, so it is still readable by object uuid.
    return True, None


def can_modify(document: dict, user: user_models.User) -> bool:
    """
    Whether `user` may edit or delete this analyst data.

    Analyst data is attributed content -- it carries the author and the
    creating organisation -- so it follows the same ownership rule MISP
    applies: the creating organisation may change it, and nobody else. This
    also means analyst data captured from a remote server or a feed cannot be
    rewritten locally, which is the point.

    Unlike events, attributes and objects, which any holder of the matching
    scope may edit, see [[project-no-row-level-authz]] for the wider picture.
    """
    # Admins bypass, matching tags_repository.capture_tag.
    if role_has_scope(user.role.scopes, "*"):
        return True

    user_org_uuid = str(user.organisation.uuid) if user.organisation else None

    document_org = document.get("orgc_uuid") or document.get("org_uuid")
    if document_org:
        return document_org == user_org_uuid

    # No organisation recorded (older rows, or a sync payload that carried no
    # Org): fall back to authorship rather than letting it be edited by anyone.
    author = document.get("authors")
    return bool(author) and author == user.email


def _assert_can_modify(document: dict, user: user_models.User) -> None:
    if not can_modify(document, user):
        raise PermissionError(
            "Analyst data %s belongs to another organisation" % document.get("uuid")
        )


def create_analyst_data(
    analyst_type: analyst_data_schemas.AnalystDataType,
    payload: dict,
    user: user_models.User,
) -> Optional[dict]:
    """
    Create one note, opinion or relationship.

    Returns None when the parent does not exist, so the caller can turn that
    into a 404 rather than leaving analyst data pointing at nothing.
    """
    object_uuid = payload["object_uuid"]
    object_type = payload["object_type"]

    parent_exists, event_uuid = _resolve_parent(object_uuid, object_type)
    if not parent_exists:
        return None

    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    analyst_uuid = str(uuid_lib.uuid4())

    document = {
        "uuid": analyst_uuid,
        "analyst_type": analyst_type.value,
        "object_uuid": object_uuid,
        "object_type": object_type,
        "event_uuid": event_uuid,
        "authors": user.email,
        "org_uuid": str(user.organisation.uuid) if user.organisation else None,
        "orgc_uuid": str(user.organisation.uuid) if user.organisation else None,
        "created": now,
        "modified": now,
        "@timestamp": now,
        "deleted": False,
        "distribution": payload.get("distribution"),
        "sharing_group_id": payload.get("sharing_group_id"),
    }

    for field in analyst_data_schemas.EDITABLE_FIELDS[analyst_type]:
        document[field] = payload.get(field)

    OpenSearchClient = get_opensearch_client()
    response = OpenSearchClient.index(
        index=ANALYST_DATA_INDEX, id=analyst_uuid, body=document, refresh=True
    )

    if response["result"] != "created":
        logger.error(
            "failed to create %s on %s %s: %s",
            analyst_type.value,
            object_type,
            object_uuid,
            response,
        )

    return document


def update_analyst_data(
    analyst_uuid: str, payload: dict, user: user_models.User
) -> Optional[dict]:
    """
    Apply a partial update. Returns None when the document does not exist, and
    raises ValueError when a field does not belong to its type.
    """
    document = get_analyst_data_by_uuid(analyst_uuid)
    if document is None or document.get("deleted"):
        return None

    _assert_can_modify(document, user)

    analyst_type = analyst_data_schemas.AnalystDataType(document["analyst_type"])
    allowed = (
        analyst_data_schemas.EDITABLE_FIELDS[analyst_type]
        | analyst_data_schemas.COMMON_EDITABLE_FIELDS
    )

    unexpected = set(payload) - allowed
    if unexpected:
        raise ValueError(
            "%s cannot be set on a %s: %s"
            % (", ".join(sorted(unexpected)), analyst_type.value, analyst_uuid)
        )

    document.update(payload)
    document["modified"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    document["@timestamp"] = document["modified"]

    OpenSearchClient = get_opensearch_client()
    OpenSearchClient.index(
        index=ANALYST_DATA_INDEX, id=str(analyst_uuid), body=document, refresh=True
    )

    return document


def delete_analyst_data(analyst_uuid: str, user: user_models.User) -> Optional[dict]:
    """
    Soft delete, matching how event reports are removed: the document stays so
    a later sync of the same uuid does not resurrect it as new.

    Replies are deleted with their parent -- leaving them would strand a thread
    under a note that no longer reads -- but only the replies this caller owns.
    Another organisation's reply on a shared thread is left alone rather than
    destroyed as collateral, so it survives even though it is no longer
    reachable from the thread it hung off.
    """
    document = get_analyst_data_by_uuid(analyst_uuid)
    if document is None:
        return None

    _assert_can_modify(document, user)

    OpenSearchClient = get_opensearch_client()
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()

    deletable = [document]
    retained = 0
    for descendant in _descendants(str(analyst_uuid)):
        if can_modify(descendant, user):
            deletable.append(descendant)
        else:
            retained += 1

    for target in deletable:
        target["deleted"] = True
        target["modified"] = now
        OpenSearchClient.index(
            index=ANALYST_DATA_INDEX,
            id=target["uuid"],
            body=target,
            refresh=True,
        )

    if retained:
        logger.info(
            "deleted %d analyst data documents under %s, kept %d owned by "
            "another organisation",
            len(deletable),
            analyst_uuid,
            retained,
        )

    return document


def _descendants(parent_uuid: str) -> list[dict]:
    """Every analyst data document nested under `parent_uuid`, at any depth."""
    collected: dict[str, dict] = {}
    frontier = [parent_uuid]

    while frontier:
        children = _search({"terms": {"object_uuid": frontier}})
        frontier = []
        for child in children:
            if child["uuid"] not in collected:
                collected[child["uuid"]] = child
                frontier.append(child["uuid"])

    return list(collected.values())
