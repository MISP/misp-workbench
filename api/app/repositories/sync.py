import logging
from hashlib import sha1
from uuid import UUID

from datetime import datetime
from app.models import event as event_models
from app.models import tag as tag_models
from app.models import user as user_models
from app.models import attribute as attribute_models
from app.models import object as object_models
from app.repositories import attributes as attributes_repository
from app.repositories import objects as objects_repository
from app.repositories import tags as tags_repository
from app.schemas import server as server_schemas
from pymisp import (
    MISPAttribute,
    MISPObject,
    MISPTag,
    MISPEventReport,
)
from sqlalchemy.orm import Session
from app.dependencies import get_opensearch_client

logger = logging.getLogger(__name__)


def create_pulled_tags(
    db: Session,
    event: event_models.Event,
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
    event: event_models.Event,
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
    local_event_id: int,
    attributes: list[attribute_models.Attribute],
    user: user_models.User,
):
    hashes_dict = {}
    for attribute in attributes:
        hash = sha1(
            (str(attribute.value) + attribute.type + attribute.category).encode("utf-8")
        ).hexdigest()
        if hash not in hashes_dict:
            local_attribute = (
                attributes_repository.create_attribute_from_pulled_attribute(
                    db, attribute, local_event_id, user
                )
            )
            hashes_dict[hash] = True
            db.add(local_attribute)

    db.commit()


def create_pulled_event_objects(
    db: Session,
    local_event_id: int,
    objects: list[object_models.Object],
    user: user_models.User,
):
    for object in objects:
        objects_repository.create_object_from_pulled_object(
            db, object, local_event_id, user
        )

    db.commit()


def update_pulled_event_objects(
    db: Session,
    local_event_id: int,
    objects: list[MISPObject],
    server: server_schemas.Server,
    user: user_models.User,
) -> None:
    for object in objects:
        local_object = objects_repository.get_object_by_uuid(db, object.uuid)

        if local_object is None:
            objects_repository.create_object_from_pulled_object(
                db, object, local_event_id, user
            )
        else:
            objects_repository.update_object_from_pulled_object(
                db, local_object, object, local_event_id, user
            )


def update_pulled_event_attributes(
    db: Session,
    local_event_id: int,
    attributes: list[MISPAttribute],
    user: user_models.User,
) -> None:
    for pulled_attribute in attributes:
        local_attribute = attributes_repository.get_attribute_by_uuid(
            db, pulled_attribute.uuid
        )

        if local_attribute is None:
            local_attribute = (
                attributes_repository.create_attribute_from_pulled_attribute(
                    db, pulled_attribute, local_event_id, user
                )
            )
            db.add(local_attribute)
        else:
            attributes_repository.update_attribute_from_pulled_attribute(
                db, local_attribute, pulled_attribute, local_event_id, user
            )
