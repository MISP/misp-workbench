import logging
import os
import smtplib
import uuid
from datetime import datetime

from app.database import SQLALCHEMY_DATABASE_URL
from app.services.opensearch import get_opensearch_client
from app.settings import get_settings
from app.services.runtime_settings_provider import get_runtime_settings
from app.repositories import events as events_repository
from app.repositories import feeds as feeds_repository
from app.repositories import servers as servers_repository
from app.repositories import objects as objects_repository
from app.repositories import users as users_repository
from app.repositories import correlations as correlations_repository
from app.repositories import attributes as attributes_repository
from app.repositories import notifications as notifications_repository
from app.schemas import event as event_schemas
from celery import Celery
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from opensearchpy import helpers as opensearch_helpers
from fastapi import HTTPException, status

# Celery configuration
app = Celery()
app.conf.update(
    broker_url=os.environ.get("CELERY_BROKER_URL"),
    result_backend=os.environ.get("CELERY_RESULT_BACKEND"),
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    worker_pool_restarts=True,
)

logger = logging.getLogger(__name__)

engine = create_engine(SQLALCHEMY_DATABASE_URL)


@app.task
def server_pull_by_id(server_id: int, user_id: int, technique: str):
    logger.info("pull server_id=%s job started", server_id)

    with Session(engine) as db:
        user = users_repository.get_user_by_id(db, user_id)
        if user is None:
            raise Exception("User not found")

        servers_repository.pull_server_by_id(db, server_id, user, technique)
        logger.info("pull server_id=%s job finished", server_id)

    return True


@app.task
def pull_event_by_uuid(event_uuid: uuid.UUID, server_id: int, user_id: int):
    logger.info(
        "pull event uuid=%s from server id=%s, job started", event_uuid, server_id
    )

    with Session(engine) as db:
        user = users_repository.get_user_by_id(db, user_id)
        if user is None:
            raise Exception("User not found")

        server = servers_repository.get_server_by_id(db, server_id)
        if server is None:
            raise Exception("Server not found")

        db_event = servers_repository.pull_event_by_uuid(
            db, event_uuid, server, user, get_settings()
        )
        
        notifications_repository.create_event_notifications(db, "new", event=db_event)
        
        logger.info(
            "pull event uuid=%s from server id=%s, job finished", event_uuid, server_id
        )

    return True


@app.task
def handle_created_event(event_uuid: uuid.UUID):
    logger.info("handling created event uuid=%s job started", event_uuid)

    with Session(engine) as db:
        db_event = events_repository.get_event_by_uuid(db, event_uuid)
        if db_event is None:
            raise Exception("Event with uuid=%s not found", event_uuid)

        notifications_repository.create_event_notifications(db, "new", event=db_event)

    return True

@app.task
def handle_updated_event(event_uuid: uuid.UUID):
    logger.info("handling updated event uuid=%s job started", event_uuid)

    with Session(engine) as db:
        db_event = events_repository.get_event_by_uuid(db, event_uuid)
        if db_event is None:
            raise Exception("Event with uuid=%s not found", event_uuid)

        notifications_repository.create_event_notifications(db, "updated", event=db_event)

    return True

@app.task
def handle_deleted_event(event_uuid: uuid.UUID):
    logger.info("handling deleted event uuid=%s job started", event_uuid)

    with Session(engine) as db:
        db_event = events_repository.get_event_by_uuid(db, event_uuid)
        if db_event is None:
            raise Exception("Event with uuid=%s not found", event_uuid)

        notifications_repository.create_event_notifications(db, "deleted", event=db_event)

    return True

@app.task
def handle_created_attribute(attribute_id: int, object_id: int | None, event_id: int):
    logger.info("handling created attribute id=%s job started", attribute_id)
    with Session(engine) as db:
        if object_id is None:
            events_repository.increment_attribute_count(db, event_id)

    db_attribute = attributes_repository.get_attribute_by_id(db, attribute_id)
    notifications_repository.create_new_attribute_notifications(db, attribute=db_attribute)

    return True


@app.task
def handle_deleted_attribute(attribute_id: int, object_id: int | None, event_id: int):
    logger.info("handling deleted attribute id=%s job started", attribute_id)
    with Session(engine) as db:
        if object_id is None:
            events_repository.decrement_attribute_count(db, event_id)

    return True


@app.task
def handle_created_object(object_id: int, event_id: int):
    logger.info("handling created object id=%s job started", object_id)

    with Session(engine) as db:
        events_repository.increment_object_count(db, event_id)

    db_object = objects_repository.get_object_by_id(db, object_id)
    notifications_repository.create_new_object_notifications(db, object=db_object)

    return True


@app.task
def handle_deleted_object(object_id: int, event_id: int):
    logger.info("handling deleted object id=%s job started", object_id)

    with Session(engine) as db:
        events_repository.decrement_object_count(db, event_id)

    return True


@app.task
def send_email(email: dict):
    logger.info("sending email job started")

    sender = f'<{email["from"]}>'
    receiver = f'<{email["to"]}>'

    message = f"""\
    Subject: {email["subject"]}
    To: {receiver}
    From: {sender}

    {email["body"]}"""

    with smtplib.SMTP(
        os.environ.get("MAIL_SERVER"), os.environ.get("MAIL_PORT")
    ) as server:
        server.login(os.environ.get("MAIL_USERNAME"), os.environ.get("MAIL_PASSWORD"))
        server.sendmail(sender, receiver, message)

    return True


@app.task
def index_event(event_uuid: uuid.UUID):
    logger.info("index event uuid=%s job started", event_uuid)

    with Session(engine) as db:
        db_event = events_repository.get_event_by_uuid(db, event_uuid)
        if db_event is None:
            raise Exception("Event with uuid=%s not found", event_uuid)

    event = event_schemas.Event.model_validate(db_event)

    OpenSearchClient = get_opensearch_client()

    event_raw = event.model_dump()
    attributes = event_raw.pop("attributes")
    objects = event_raw.pop("objects")

    # convert timestamp to datetime so it can be indexed
    event_raw["@timestamp"] = datetime.fromtimestamp(event_raw["timestamp"]).isoformat()

    if event_raw["publish_timestamp"]:
        event_raw["@publish_timestamp"] = datetime.fromtimestamp(
            event_raw["publish_timestamp"]
        ).isoformat()

    response = OpenSearchClient.index(
        index="misp-events", id=event.uuid, body=event_raw, refresh=True
    )

    if response["result"] not in ["created", "updated"]:
        logger.error(
            "Failed to index event uuid=%s. Response: %s", event_uuid, response
        )
        raise Exception("Failed to index event.")

    logger.info("indexed event uuid=%s", event_uuid)

    # index attributes
    attributes_docs = []
    for attribute in attributes:
        attribute["@timestamp"] = datetime.fromtimestamp(
            attribute["timestamp"]
        ).isoformat()
        attribute["event_uuid"] = event.uuid
        attribute["data"] = ""  # do not index file contents

        attributes_docs.append(
            {
                "_id": attribute["uuid"],
                "_index": "misp-attributes",
                "_source": attribute,
            }
        )

    success, failed = opensearch_helpers.bulk(
        OpenSearchClient, attributes_docs, refresh=True
    )
    if failed:
        logger.error("Failed to index attributes. Failed: %s", failed)
        raise Exception("Failed to index attributes.")
    logger.info(
        "indexed attributes of event uuid=%s, indexed %s attributes",
        event_uuid,
        len(attributes_docs),
    )

    # index objects
    objects_docs = []
    for object in objects:
        object["@timestamp"] = datetime.fromtimestamp(object["timestamp"]).isoformat()

        object_attributes = object.pop("attributes")

        object_attributes_docs = []
        for attribute in object_attributes:
            attribute["@timestamp"] = datetime.fromtimestamp(
                attribute["timestamp"]
            ).isoformat()
            attribute["event_uuid"] = event.uuid
            attribute["object_uuid"] = object["uuid"]
            attribute["data"] = ""  # do not index file contents
            object_attributes_docs.append(
                {
                    "_id": attribute["uuid"],
                    "_index": "misp-attributes",
                    "_source": attribute,
                }
            )

        success, failed = opensearch_helpers.bulk(
            OpenSearchClient, attributes_docs, refresh=True
        )
        if failed:
            logger.error("Failed to index object attributes. Failed: %s", failed)
            raise Exception("Failed to index object attributes.")
        logger.info(
            "indexed attributes of event uuid=%s, object uuid=%s, indexed %s attributes",
            event_uuid,
            object["uuid"],
            len(object_attributes_docs),
        )

        for reference in object["object_references"]:
            reference["@timestamp"] = datetime.fromtimestamp(
                reference["timestamp"]
            ).isoformat()

        object["event_uuid"] = event.uuid

        objects_docs.append(
            {
                "_id": object["uuid"],
                "_index": "misp-objects",
                "_source": object,
            }
        )

    success, failed = opensearch_helpers.bulk(
        OpenSearchClient, objects_docs, refresh=True
    )
    if failed:
        logger.error("Failed to index objects. Failed: %s", failed)
        raise Exception("Failed to index objects.")
    logger.info(
        "indexed objects of event uuid=%s, indexed %s objects",
        event_uuid,
        len(objects_docs),
    )

    logger.info("index event uuid=%s job finished", event_uuid)

    return True


@app.task
def fetch_feed_async(feed_id: int, user_id: int):
    logger.info("fetch feed id=%s job started", feed_id)

    with Session(engine) as db:
        user = users_repository.get_user_by_id(db, user_id)
        feeds_repository.fetch_feed(db, feed_id, user)

    logger.info("fetch feed id=%s job finished", feed_id)

    return True


@app.task
def fetch_feed(feed_id: int, user_id: int):
    logger.info("fetch feed id=%s job started", feed_id)

    with Session(engine) as db:
        user = users_repository.get_user_by_id(db, user_id)

        feeds_repository.fetch_feed(db, feed_id, user)

        logger.info("fetch feed id=%s all event fetch tasks enqueued.", feed_id)

        return {
            "result": "success",
            "message": "All feed id=%s events to fetch enqueued." % feed_id,
        }


@app.task
def fetch_feed_event(event_uuid: uuid.UUID, feed_id: int, user_id: int):
    logger.info("fetch feed event uuid=%s job started", event_uuid)

    with Session(engine) as db:
        user = users_repository.get_user_by_id(db, user_id)
        db_feed = feeds_repository.get_feed_by_id(db, feed_id=feed_id)

        result = feeds_repository.process_feed_event(db, event_uuid, db_feed, user)

    logger.info("fetch feed event uuid=%s job finished", event_uuid)
    return result


@app.task
def generate_correlations():
    logger.info("generate correlations job started")

    with Session(engine) as db:
        runtimeSettings = get_runtime_settings(db)

    try:
        correlations_repository.delete_correlations()
        correlations_repository.run_correlations(runtimeSettings)
    except Exception as e:
        logger.error("Failed to generate correlations: %s", str(e))
        return False

    logger.info("generate correlations job finished")

    return True
