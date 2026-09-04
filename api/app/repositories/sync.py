import logging
from hashlib import sha1
from typing import Optional, Union
from uuid import UUID

from datetime import datetime, timezone
from app.models import tag as tag_models
from app.schemas import event as event_schemas
from app.models import user as user_models
from app.repositories import attributes as attributes_repository
from app.repositories import objects as objects_repository
from app.repositories import tags as tags_repository
from app.schemas import server as server_schemas
from opensearchpy import helpers as opensearch_helpers
from pymisp import (
    MISPAttribute,
    MISPEvent,
    MISPNote,
    MISPObject,
    MISPOpinion,
    MISPRelationship,
    MISPTag,
    MISPEventReport,
)
from sqlalchemy.orm import Session
from app.services.opensearch import get_opensearch_client

logger = logging.getLogger(__name__)


def create_pulled_tags(
    db: Session,
    event: event_schemas.Event,
    pulled_tags: list[MISPTag],
    user: user_models.User,
) -> list[tag_models.Tag]:
    tags = []

    for tag in pulled_tags:
        tag = tags_repository.capture_tag(db, tag, user)
        if tag:
            tags.append(tag)

    return tags


def create_pulled_event_tags(
    db: Session,
    event: event_schemas.Event,
    pulled_tags: list[MISPTag],
    user: user_models.User,
) -> None:

    tags = create_pulled_tags(db, event, pulled_tags, user)

    # TODO: bulk insert
    for tag in tags:
        tags_repository.tag_event(db, event, tag)


def create_pulled_event_reports(
    db: Session,
    local_event_uuid: UUID,
    event_reports: list[MISPEventReport],
    user: user_models.User,
) -> None:

    if event_reports is None or len(event_reports) == 0:
        return

    OpenSearchClient = get_opensearch_client()

    for event_report in event_reports:

        event_report_raw = event_report.to_dict()

        event_report_raw["@timestamp"] = datetime.fromtimestamp(
            int(event_report_raw["timestamp"])
        ).isoformat()

        event_report_raw["event_uuid"] = str(local_event_uuid)

        response = OpenSearchClient.index(
            index="misp-event-reports",
            id=event_report.uuid,
            body=event_report_raw,
            refresh=True,
        )

        if response["result"] not in ["created", "updated"]:
            logger.error(
                "Failed to index event report uuid=%s. Response: %s",
                event_report.uuid,
                response,
            )
            raise Exception("Failed to index event report.")


def create_pulled_event_attributes(
    db: Session,
    event_uuid: str,
    attributes: list[MISPAttribute],
    user: user_models.User,
):
    hashes_dict = {}
    for attribute in attributes:
        hash = sha1(
            (str(attribute.value) + attribute.type + attribute.category).encode("utf-8")
        ).hexdigest()
        if hash not in hashes_dict:
            attributes_repository.create_attribute_from_pulled_attribute(
                db, attribute, event_uuid, user
            )
            hashes_dict[hash] = True

    db.commit()


def create_pulled_event_objects(
    db: Session,
    event_uuid: str,
    objects: list[MISPObject],
    user: user_models.User,
):
    for object in objects:
        objects_repository.create_object_from_pulled_object(
            db, object, event_uuid, user
        )

    db.commit()


def update_pulled_event_objects(
    db: Session,
    event_uuid: str,
    objects: list[MISPObject],
    user: user_models.User,
) -> None:
    for object in objects:
        local_object = objects_repository.get_object_by_uuid(db, object.uuid)

        if local_object is None:
            objects_repository.create_object_from_pulled_object(
                db, object, event_uuid, user
            )
        else:
            objects_repository.update_object_from_pulled_object(
                db, local_object, object, event_uuid, user
            )


def update_pulled_event_attributes(
    db: Session,
    event_uuid: str,
    attributes: list[MISPAttribute],
    user: user_models.User,
) -> None:
    for pulled_attribute in attributes:
        local_attribute = attributes_repository.get_attribute_by_uuid(
            db, pulled_attribute.uuid
        )

        if local_attribute is None:
            attributes_repository.create_attribute_from_pulled_attribute(
                db, pulled_attribute, event_uuid, user
            )
        else:
            attributes_repository.update_attribute_from_pulled_attribute(
                db, local_attribute, pulled_attribute, user
            )


ANALYST_DATA_INDEX = "misp-analyst-data"

# Fields carried by every analyst data type, followed by the ones specific to
# each. Anything else MISP sends (Org/Orgc blobs, nested analyst data, server
# side ids) is deliberately dropped rather than indexed.
_ANALYST_DATA_COMMON_FIELDS = (
    "uuid",
    "object_uuid",
    "object_type",
    "authors",
    "created",
    "modified",
    "distribution",
    "sharing_group_id",
)

_ANALYST_DATA_TYPE_FIELDS = {
    "Note": ("note", "language", "note_type_name"),
    "Opinion": ("opinion", "comment"),
    "Relationship": (
        "related_object_uuid",
        "related_object_type",
        "relationship_type",
    ),
}

_INT_FIELDS = {"distribution", "sharing_group_id", "opinion"}


def _coerce_int(value):
    """
    MISP sends numeric analyst data fields as strings ("3", "75"). The index
    maps them as integers, so a string would be rejected on write.
    """
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _analyst_data_timestamp(value) -> Optional[str]:
    """
    `created`/`modified` arrive as a datetime from pymisp, or as a MISP
    date string. Both are normalised to ISO 8601 for the date mapping.
    """
    if value is None or value == "":
        return None

    if isinstance(value, datetime):
        return value.isoformat()

    return str(value)


def _build_analyst_data_document(
    analyst_data: Union[MISPNote, MISPOpinion, MISPRelationship],
    analyst_type: str,
    event_uuid: Optional[UUID],
) -> Optional[dict]:
    raw = analyst_data.to_dict()

    if raw.get("uuid") is None:
        logger.warning("skipping %s without a uuid", analyst_type)
        return None

    document = {"analyst_type": analyst_type, "deleted": False}

    fields = _ANALYST_DATA_COMMON_FIELDS + _ANALYST_DATA_TYPE_FIELDS[analyst_type]
    for field in fields:
        value = raw.get(field)

        if field in _INT_FIELDS:
            value = _coerce_int(value)
        elif field in ("created", "modified"):
            value = _analyst_data_timestamp(value)
        elif value is not None:
            value = str(value)

        document[field] = value

    # The organisation blobs are flattened to their uuids: the orgs themselves
    # are captured separately by the event/attribute ingest.
    for key, source in (("org_uuid", "Org"), ("orgc_uuid", "Orgc")):
        org = raw.get(source)
        document[key] = (
            str(org["uuid"]) if isinstance(org, dict) and org.get("uuid") else None
        )

    # Denormalised so all analyst data for an event can be read in one query,
    # including data nested several levels deep whose object_uuid points at
    # another note rather than at the event.
    document["event_uuid"] = str(event_uuid) if event_uuid else None

    document["@timestamp"] = (
        document["modified"]
        or document["created"]
        or datetime.now(timezone.utc).isoformat()
    )

    return document


def _collect_analyst_data(
    parent,
    event_uuid: Optional[UUID],
    documents: list,
    seen: set,
) -> None:
    """
    Walk analyst data attached to `parent`, appending one document per
    note/opinion/relationship found.

    MISP nests analyst data arbitrarily deep -- a note carries notes and
    opinions of its own, each of those the same again. Documents are stored
    flat and keyed by `object_uuid` + `object_type`, so the thread is
    reconstructed on read instead of being nested in the index. `seen` guards
    against a payload that points a note back at an ancestor.
    """
    for analyst_type, attribute in (
        ("Note", "notes"),
        ("Opinion", "opinions"),
        ("Relationship", "relationships"),
    ):
        for analyst_data in getattr(parent, attribute, None) or []:
            uuid_str = str(getattr(analyst_data, "uuid", "") or "")
            if uuid_str in seen:
                logger.warning(
                    "skipping already seen %s uuid=%s, the payload nests it in a cycle",
                    analyst_type,
                    uuid_str,
                )
                continue
            seen.add(uuid_str)

            document = _build_analyst_data_document(
                analyst_data, analyst_type, event_uuid
            )
            if document is not None:
                documents.append(document)

            # Relationships carry analyst data too, so all three recurse.
            _collect_analyst_data(analyst_data, event_uuid, documents, seen)


def create_pulled_analyst_data(
    db: Session,
    event: MISPEvent,
    event_uuid: UUID,
    user: user_models.User,
) -> list[dict]:
    """
    Capture the analyst data (notes, opinions, relationships) carried by a
    pulled or fetched event, its attributes, its objects and their attributes.

    Documents are upserted by uuid, so re-pulling an event refreshes the
    analyst data already stored for it rather than duplicating it.
    """
    documents: list[dict] = []
    seen: set = set()

    _collect_analyst_data(event, event_uuid, documents, seen)

    for attribute in event.attributes or []:
        _collect_analyst_data(attribute, event_uuid, documents, seen)

    for misp_object in event.objects or []:
        _collect_analyst_data(misp_object, event_uuid, documents, seen)

        for attribute in misp_object.attributes or []:
            _collect_analyst_data(attribute, event_uuid, documents, seen)

    for event_report in event.event_reports or []:
        _collect_analyst_data(event_report, event_uuid, documents, seen)

    if not documents:
        return []

    OpenSearchClient = get_opensearch_client()

    actions = [
        {
            "_op_type": "index",
            "_index": ANALYST_DATA_INDEX,
            "_id": document["uuid"],
            **document,
        }
        for document in documents
    ]

    _, errors = opensearch_helpers.bulk(
        OpenSearchClient, actions, refresh=True, raise_on_error=False
    )

    for error in errors:
        info = error.get("index", {})
        logger.error(
            "failed to index analyst data %s: %s",
            info.get("_id"),
            info.get("error"),
        )

    logger.info(
        "captured %d analyst data documents for event %s",
        len(documents) - len(errors),
        event_uuid,
    )

    return documents
