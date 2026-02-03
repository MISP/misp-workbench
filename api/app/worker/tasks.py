import logging
import os
import smtplib
import uuid
from datetime import datetime

from app.database import SQLALCHEMY_DATABASE_URL
from app.services.opensearch import get_opensearch_client
from app.services.redis import get_redis_client
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
from app.repositories import galaxies as galaxies_repository
from app.repositories import taxonomies as taxonomies_repository
from app.schemas import event as event_schemas
from celery import Celery
from celery.signals import worker_ready
from app.models import user as user_models
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from opensearchpy import helpers as opensearch_helpers

# Celery configuration
app = Celery()
app.conf.update(
    broker_url=os.environ.get("CELERY_BROKER_URL"),
    result_backend=os.environ.get("CELERY_RESULT_BACKEND"),
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    worker_pool_restarts=True,
    broker_transport_options={"visibility_timeout": 60 * 60 * 10},  # 10 hours,
    acks_late=False,
    worker_prefetch_multiplier=1,
    task_time_limit=None,
    task_soft_time_limit=None,
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

        notifications_repository.create_event_notifications(
            db, "created", event=db_event
        )

        logger.info(
            "pull event uuid=%s from server id=%s, job finished", event_uuid, server_id
        )

    return True


@app.task
def server_push_by_id(server_id: int, user_id: int, technique: str):
    logger.info("push server_id=%s job started", server_id)

    with Session(engine) as db:
        user = users_repository.get_user_by_id(db, user_id)
        if user is None:
            raise Exception("User not found")

        servers_repository.push_server_by_id(db, server_id, user, technique)
        logger.info("push server_id=%s job finished", server_id)

    return True


@app.task
def push_event_by_uuid(event_uuid: uuid.UUID, server_id: int, user_id: int):
    logger.info(
        "push event uuid=%s to server id=%s, job started", event_uuid, server_id
    )

    with Session(engine) as db:
        user = users_repository.get_user_by_id(db, user_id)
        if user is None:
            raise Exception("User not found")

        server = servers_repository.get_server_by_id(db, server_id)
        if server is None:
            raise Exception("Server not found")

        servers_repository.push_event_by_uuid(
            db, event_uuid, server, user, get_settings()
        )

        logger.info(
            "push event uuid=%s to server id=%s, job finished", event_uuid, server_id
        )

    return True


@app.task
def handle_created_event(event_uuid: uuid.UUID):
    logger.info("handling created event uuid=%s job started", event_uuid)

    with Session(engine) as db:
        db_event = events_repository.get_event_by_uuid(db, event_uuid)
        if db_event is None:
            raise Exception("Event with uuid=%s not found", event_uuid)

        notifications_repository.create_event_notifications(
            db, "created", event=db_event
        )

    return True


@app.task
def handle_updated_event(event_uuid: uuid.UUID):
    logger.info("handling updated event uuid=%s job started", event_uuid)

    with Session(engine) as db:
        db_event = events_repository.get_event_by_uuid(db, event_uuid)

        if db_event is None:
            raise Exception("Event with uuid=%s not found", event_uuid)

        db_event.timestamp = datetime.now().timestamp()
        db.commit()
        db.refresh(db_event)

        notifications_repository.create_event_notifications(
            db, "updated", event=db_event
        )

        index_event.delay(db_event.uuid, full_reindex=False)

    return True


@app.task
def handle_deleted_event(event_uuid: uuid.UUID):
    logger.info("handling deleted event uuid=%s job started", event_uuid)

    with Session(engine) as db:
        db_event = events_repository.get_event_by_uuid(db, event_uuid)
        if db_event is None:
            raise Exception("Event with uuid=%s not found", event_uuid)

        notifications_repository.create_event_notifications(
            db, "deleted", event=db_event
        )

        delete_indexed_event.delay(event_uuid)

    return True


@app.task
def handle_created_attribute(attribute_id: int, object_id: int | None, event_id: int):
    logger.info("handling created attribute id=%s job started", attribute_id)
    with Session(engine) as db:
        if object_id is None:
            events_repository.increment_attribute_count(db, event_id)

        db_attribute = attributes_repository.get_attribute_by_id(db, attribute_id)
        notifications_repository.create_attribute_notifications(
            db, "created", attribute=db_attribute
        )

        index_attribute.delay(db_attribute.uuid)

    return True


@app.task
def handle_updated_attribute(attribute_id: int, object_id: int | None, event_id: int):
    logger.info("handling updated attribute id=%s job started", attribute_id)
    with Session(engine) as db:
        db_attribute = attributes_repository.get_attribute_by_id(db, attribute_id)
        notifications_repository.create_attribute_notifications(
            db, "updated", attribute=db_attribute
        )

        index_attribute.delay(db_attribute.uuid)

    return True


@app.task
def handle_deleted_attribute(attribute_id: int, object_id: int | None, event_id: int):
    logger.info("handling deleted attribute id=%s job started", attribute_id)
    with Session(engine) as db:
        db_attribute = attributes_repository.get_attribute_by_id(db, attribute_id)
        if object_id is None:
            events_repository.decrement_attribute_count(db, event_id)

        notifications_repository.create_attribute_notifications(
            db, "deleted", attribute=db_attribute
        )

        delete_indexed_attribute.delay(db_attribute.uuid)

    return True


@app.task
def handle_created_object(object_id: int, event_id: int):
    logger.info("handling created object id=%s job started", object_id)

    with Session(engine) as db:
        events_repository.increment_object_count(db, event_id)

        db_object = objects_repository.get_object_by_id(db, object_id)
        notifications_repository.create_object_notifications(
            db, "created", object=db_object
        )

        index_object.delay(db_object.uuid)

    return True


@app.task
def handle_updated_object(object_id: int, event_id: int):
    logger.info("handling updated object id=%s job started", object_id)

    with Session(engine) as db:
        db_object = objects_repository.get_object_by_id(db, object_id)
        notifications_repository.create_object_notifications(
            db, "updated", object=db_object
        )

        index_object.delay(db_object.uuid)

    return True


@app.task
def handle_deleted_object(object_id: int, event_id: int):
    logger.info("handling deleted object id=%s job started", object_id)

    with Session(engine) as db:
        events_repository.decrement_object_count(db, event_id)

        db_object = objects_repository.get_object_by_id(db, object_id)
        notifications_repository.create_object_notifications(
            db, "deleted", object=db_object
        )

        delete_indexed_object.delay(db_object.uuid)

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
def index_event(event_uuid: uuid.UUID, full_reindex: bool = False):
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

    if not full_reindex:
        return True

    # delete existing indexed attributes and objects
    query = {"query": {"bool": {"must": [{"term": {"event_uuid": str(event.uuid)}}]}}}

    response = OpenSearchClient.delete_by_query(
        index="misp-attributes", body=query, refresh=True
    )
    logger.info(
        "deleted %s previously indexed attributes for event uuid=%s",
        response["deleted"],
        event_uuid,
    )

    response = OpenSearchClient.delete_by_query(
        index="misp-objects", body=query, refresh=True
    )
    logger.info(
        "deleted %s previously indexed objects for event uuid=%s",
        response["deleted"],
        event_uuid,
    )

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
            OpenSearchClient, object_attributes_docs, refresh=True
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
        RedisClient = get_redis_client()
    except Exception:
        RedisClient = None

    # TODO: Make lock key and TTL configurable, check if this is still required when there are multiple workers
    lock_key = "generate_correlations_lock"
    lock_ttl_seconds = 60 * 60 * 1  # 1 hour - safe default for long runs

    # Try to acquire the lock. If we can't acquire it, another run is active
    # or finished very recently, so skip to avoid duplicates.
    if RedisClient is not None:
        try:
            got_lock = RedisClient.set(lock_key, "1", nx=True, ex=lock_ttl_seconds)
        except Exception:
            got_lock = False
    else:
        got_lock = False

    if not got_lock:
        logger.info("generate_correlations skipped: lock present (another run active)")
        return True

    try:
        try:
            correlations_repository.delete_correlations()
            correlations_repository.run_correlations(runtimeSettings)
        except Exception as e:
            logger.error("Failed to generate correlations: %s", str(e))
            return False

        logger.info("generate correlations job finished")
        return True
    finally:
        # Release the lock. If Redis isn't available this is a noop.
        try:
            if RedisClient is not None:
                RedisClient.delete(lock_key)
        except Exception:
            pass

@app.task
def handle_created_sighting(
    value: str, organisation: str, sighting_type: str, timestamp: float = None
):
    logger.info("handling created sighting value=%s job started", value)

    attributes = events_repository.search_events(
        page=0,
        from_value=0,
        size=1000,
        query="value: %s" % value,
        searchAttributes=True,
    )

    if attributes["total"] > 1000:
        logger.warning(
            "Too many attributes found for value=%s, only the first 1000 will be processed.",
            value,
        )

    sighting = {
        "value": value,
        "type": sighting_type,
        "observer": {"organisation": organisation},
        "timestamp": timestamp or datetime.datetime.now().timestamp(),
    }

    with Session(engine) as db:
        for attribute in attributes["results"]:
            notifications_repository.create_sighting_notifications(
                db, "created", attribute=attribute, sighting=sighting
            )


@app.task
def handle_created_correlation(
    source_attribute_uuid: str,
    source_event_uuid: str,
    target_event_uuid: str,
    target_attribute_uuid: str,
    target_attribute_type: str,
    target_attribute_value: str,
):
    logger.info("handling created correlation id=%s job started", source_attribute_uuid)

    with Session(engine) as db:
        correlation = {
            "source_attribute_uuid": source_attribute_uuid,
            "source_event_uuid": source_event_uuid,
            "target_event_uuid": target_event_uuid,
            "target_attribute_uuid": target_attribute_uuid,
            "target_attribute_type": target_attribute_type,
            "target_attribute_value": target_attribute_value,
        }

        notifications_repository.create_correlation_notifications(
            db, "created", correlation=correlation
        )

    return True


@app.task
def handle_published_event(event_uuid: uuid.UUID):
    logger.info("handling published event uuid=%s job started", event_uuid)

    with Session(engine) as db:
        db_event = events_repository.get_event_by_uuid(db, event_uuid)
        if db_event is None:
            raise Exception("Event with uuid=%s not found", event_uuid)

        notifications_repository.create_event_notifications(
            db, "published", event=db_event
        )

        logger.info("handling published event uuid=%s job finished", event_uuid)

    return True


@app.task
def handle_unpublished_event(event_uuid: uuid.UUID):
    logger.info("handling unpublished event uuid=%s job started", event_uuid)

    with Session(engine) as db:
        db_event = events_repository.get_event_by_uuid(db, event_uuid)
        if db_event is None:
            raise Exception("Event with uuid=%s not found", event_uuid)

        notifications_repository.create_event_notifications(
            db, "unpublished", event=db_event
        )

        logger.info("handling unpublished event uuid=%s job finished", event_uuid)

    return True


@app.task
def handle_toggled_event_correlation(event_uuid: uuid.UUID, disable_correlation: bool):
    logger.info("handling toggled event correlation uuid=%s job started", event_uuid)

    with Session(engine) as db:
        db_event = events_repository.get_event_by_uuid(db, event_uuid)
        if db_event is None:
            raise Exception("Event with uuid=%s not found", event_uuid)

        if disable_correlation:
            correlations_repository.delete_event_correlations(event_uuid)
        else:
            with Session(engine) as db:
                runtimeSettings = get_runtime_settings(db)

                correlations_repository.correlate_event(
                    runtimeSettings, str(event_uuid)
                )

        logger.info(
            "handling toggled event correlation uuid=%s job finished", event_uuid
        )

    return True


@app.task
def delete_indexed_event(event_uuid: uuid.UUID):
    logger.info("deleting indexed event uuid=%s job started", event_uuid)

    OpenSearchClient = get_opensearch_client()

    response = OpenSearchClient.delete(
        index="misp-events", id=event_uuid, refresh=True, ignore=[404]
    )

    if response.get("result") == "not_found":
        logger.info("event uuid=%s not found in index, nothing to delete", event_uuid)
    else:
        logger.info("deleted indexed event uuid=%s", event_uuid)

    # delete indexed attributes
    query = {"query": {"bool": {"must": [{"term": {"event_uuid": str(event_uuid)}}]}}}

    response = OpenSearchClient.delete_by_query(
        index="misp-attributes", body=query, refresh=True
    )
    logger.info(
        "deleted %s indexed attributes for event uuid=%s",
        response["deleted"],
        event_uuid,
    )

    # delete indexed objects
    response = OpenSearchClient.delete_by_query(
        index="misp-objects", body=query, refresh=True
    )
    logger.info(
        "deleted %s indexed objects for event uuid=%s",
        response["deleted"],
        event_uuid,
    )

    logger.info("deleting indexed event uuid=%s job finished", event_uuid)

    return True


@app.task
def index_attribute(attribute_uuid: uuid.UUID):
    logger.info("indexing attribute uuid=%s job started", attribute_uuid)

    with Session(engine) as db:
        db_attribute = attributes_repository.get_attribute_by_uuid(db, attribute_uuid)
        if db_attribute is None:
            raise Exception("Attribute with uuid=%s not found", attribute_uuid)

    attribute = event_schemas.Attribute.model_validate(db_attribute)

    OpenSearchClient = get_opensearch_client()

    attribute_raw = attribute.model_dump()

    # convert timestamp to datetime so it can be indexed
    attribute_raw["@timestamp"] = datetime.fromtimestamp(
        attribute_raw["timestamp"]
    ).isoformat()
    attribute_raw["data"] = ""  # do not index file contents

    response = OpenSearchClient.index(
        index="misp-attributes",
        id=attribute.uuid,
        body=attribute_raw,
        refresh=True,
    )

    if response["result"] not in ["created", "updated"]:
        logger.error(
            "Failed to index attribute uuid=%s. Response: %s",
            attribute_uuid,
            response,
        )
        raise Exception("Failed to index attribute.")

    logger.info("indexed attribute uuid=%s job finished", attribute_uuid)

    return True


@app.task
def delete_indexed_attribute(attribute_uuid: uuid.UUID):
    logger.info("deleting indexed attribute uuid=%s job started", attribute_uuid)

    OpenSearchClient = get_opensearch_client()

    response = OpenSearchClient.delete(
        index="misp-attributes", id=attribute_uuid, refresh=True, ignore=[404]
    )

    if response.get("result") == "not_found":
        logger.info(
            "attribute uuid=%s not found in index, nothing to delete", attribute_uuid
        )
    else:
        logger.info("deleted indexed attribute uuid=%s", attribute_uuid)

    logger.info("deleting indexed attribute uuid=%s job finished", attribute_uuid)

    return True


@app.task(name="load_galaxies")
def load_galaxies(user_id: int):
    """Load galaxies from the bundled misp-galaxy submodule into the database.

    If `user_id` is not provided the first user in the database will be used as
    the creator for created tags and objects.
    """
    logger.info("load_galaxies job started")

    with Session(engine) as db:
        if user_id is not None:
            user = users_repository.get_user_by_id(db, user_id)

        if user is None:
            logger.error("No user found to run load_galaxies; aborting")
            return False

        try:
            galaxies = galaxies_repository.update_galaxies(db, user)
            logger.info(
                "load_galaxies finished: %s galaxies created/updated", len(galaxies)
            )
            return True
        except Exception as e:
            logger.exception("Error loading galaxies: %s", e)
            return False

@app.task(name="load_taxonomies")
def load_taxonomies():
    logger.info("load_taxonomies job started")

    with Session(engine) as db:
        try:
            taxonomies = taxonomies_repository.update_taxonomies(db)
            logger.info(
                "load_taxonomies finished: %s taxonomies created/updated",
                len(taxonomies),
            )
            return True
        except Exception as e:
            logger.exception("Error loading taxonomies: %s", e)
            return False

@app.task
def index_object(object_uuid: uuid.UUID):
    logger.info("indexing object uuid=%s job started", object_uuid)

    with Session(engine) as db:
        db_object = objects_repository.get_object_by_uuid(db, object_uuid)
        if db_object is None:
            raise Exception("Object with uuid=%s not found", object_uuid)

    object = event_schemas.Object.model_validate(db_object)

    OpenSearchClient = get_opensearch_client()

    object_raw = object.model_dump()

    # convert timestamp to datetime so it can be indexed
    object_raw["@timestamp"] = datetime.fromtimestamp(
        object_raw["timestamp"]
    ).isoformat()
    object_raw["event_uuid"] = str(db_object.event.uuid)

    response = OpenSearchClient.index(
        index="misp-objects",
        id=object.uuid,
        body=object_raw,
        refresh=True,
    )

    if response["result"] not in ["created", "updated"]:
        logger.error(
            "Failed to index object uuid=%s. Response: %s", object_uuid, response
        )
        raise Exception("Failed to index object.")

    logger.info("indexed object uuid=%s job finished", object_uuid)

    return True


@app.task
def delete_indexed_object(object_uuid: uuid.UUID):
    logger.info("deleting indexed object uuid=%s job started", object_uuid)

    OpenSearchClient = get_opensearch_client()

    response = OpenSearchClient.delete(
        index="misp-objects", id=object_uuid, refresh=True, ignore=[404]
    )

    if response.get("result") == "not_found":
        logger.info("object uuid=%s not found in index, nothing to delete", object_uuid)
    else:
        logger.info("deleted indexed object uuid=%s", object_uuid)

    logger.info("deleting indexed object uuid=%s job finished", object_uuid)

    return True
