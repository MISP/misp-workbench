import logging
import os
import smtplib
import uuid
from datetime import datetime

from app.database import SessionLocal
from app.dependencies import get_opensearch_client
from app.repositories import events as events_repository
from app.repositories import feeds as feeds_repository
from app.repositories import servers as servers_repository
from app.repositories import users as users_repository
from app.schemas import event as event_schemas
from app.settings import get_settings
from celery import Celery

# Celery configuration
app = Celery()
app.conf.update(
    broker_url=os.environ.get("CELERY_BROKER_URL"),
    result_backend=os.environ.get("CELERY_RESULT_BACKEND"),
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
)

logger = logging.getLogger(__name__)

db = SessionLocal()


@app.task
def server_pull_by_id(server_id: int, user_id: int, technique: str):
    logger.info("pull server_id=%s job started", server_id)

    user = users_repository.get_user_by_id(db, user_id)
    if user is None:
        raise Exception("User not found")

    servers_repository.pull_server_by_id(db, get_settings(), server_id, user, technique)
    logger.info("pull server_id=%s job finished", server_id)

    return True


@app.task
def handle_created_attribute(attribute_id: int, event_id: int):
    logger.info("handling created attribute id=%s job started", attribute_id)

    events_repository.increment_attribute_count(db, event_id)

    return True


@app.task
def handle_deleted_attribute(attribute_id: int, event_id: int):
    logger.info("handling deleted attribute id=%s job started", attribute_id)

    events_repository.decrement_attribute_count(db, event_id)

    return True


@app.task
def handle_created_object(object_id: int, event_id: int):
    logger.info("handling created object id=%s job started", object_id)

    events_repository.increment_object_count(db, event_id)

    return True


@app.task
def handle_deleted_object(object_id: int, event_id: int):
    logger.info("handling deleted object id=%s job started", object_id)

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

    db_event = events_repository.get_event_by_uuid(db, event_uuid)
    if db_event is None:
        raise Exception("Event with uuid=%s not found", event_uuid)

    event = event_schemas.Event.model_validate(db_event)

    OpenSearchClient = get_opensearch_client()

    event_json = event.model_dump()

    # convert timestamp to datetime so it can be indexed
    event_json["@timestamp"] = datetime.fromtimestamp(
        event_json["timestamp"]
    ).isoformat()

    if event_json["publish_timestamp"]:
        event_json["@publish_timestamp"] = datetime.fromtimestamp(
            event_json["publish_timestamp"]
        ).isoformat()

    for attribute in event_json["attributes"]:
        attribute["@timestamp"] = datetime.fromtimestamp(
            attribute["timestamp"]
        ).isoformat()

    for object in event_json["objects"]:
        object["@timestamp"] = datetime.fromtimestamp(object["timestamp"]).isoformat()

        for attribute in object["attributes"]:
            attribute["@timestamp"] = datetime.fromtimestamp(
                attribute["timestamp"]
            ).isoformat()

    response = OpenSearchClient.index(
        index="misp-events", id=event.uuid, body=event_json, refresh=True
    )

    if response["result"] not in ["created", "updated"]:
        logger.error(
            "Failed to index event uuid=%s. Response: %s", event_uuid, response
        )
        raise Exception("Failed to index event.")

    logger.info("index event uuid=%s job finished", event_uuid)

    return True


@app.task
def fetch_feed(feed_id: int, user_id: int):
    logger.info("fetch feed id=%s job started", feed_id)

    user = users_repository.get_user_by_id(db, user_id)

    feeds_repository.fetch_feed(db, feed_id, user)

    logger.info("fetch feed id=%s job finished", feed_id)

    return True
