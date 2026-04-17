import logging
import os
import smtplib
from email.message import EmailMessage
from datetime import datetime
from uuid import UUID

from app.database import SQLALCHEMY_DATABASE_URL
from app.services.opensearch import get_opensearch_client
from app.services.redis import get_redis_client
from app.settings import get_settings
from app.services.runtime_settings_provider import get_runtime_settings
from app.repositories import events as events_repository
from app.repositories import feeds as feeds_repository
from app.repositories import freetext as freetext_repository
from app.repositories import servers as servers_repository
from app.repositories import objects as objects_repository
from app.repositories import users as users_repository
from app.repositories import correlations as correlations_repository
from app.repositories import attributes as attributes_repository
from app.repositories import notifications as notifications_repository
from app.repositories import galaxies as galaxies_repository
from app.repositories import hunts as hunts_repository
from app.repositories import taxonomies as taxonomies_repository
from app.schemas import attribute as attribute_schemas
from celery import Celery
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

# Celery configuration
celery_app = Celery("misp-workbench")
celery_app.conf.update(
    broker_url=os.environ.get("CELERY_BROKER_URL"),
    result_backend=os.environ.get("CELERY_RESULT_BACKEND"),
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    worker_pool_restarts=True,
    broker_transport_options={"visibility_timeout": 60 * 60 * 24},  # 24 hours,
    acks_late=False,
    worker_prefetch_multiplier=1,
    task_time_limit=None,
    task_soft_time_limit=None,
    beat_scheduler="redbeat.RedBeatScheduler",
    redbeat_redis_url=os.environ.get("CELERY_BROKER_URL"),
)

logger = logging.getLogger(__name__)

engine = create_engine(SQLALCHEMY_DATABASE_URL)


@celery_app.task
def server_pull_by_id(server_id: int, user_id: int, technique: str):
    logger.info("pull server_id=%s job started", server_id)

    with Session(engine) as db:
        user = users_repository.get_user_by_id(db, user_id)
        if user is None:
            raise Exception("User not found")

        servers_repository.pull_server_by_id(db, server_id, user, technique)
        logger.info("pull server_id=%s job finished", server_id)

    return True


@celery_app.task
def pull_event_by_uuid(event_uuid: str, server_id: int, user_id: int):
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

        if db_event:
            notifications_repository.create_event_notifications(
                db, "created", event=db_event
            )

        logger.info(
            "pull event uuid=%s from server id=%s, job finished", event_uuid, server_id
        )

    return True


@celery_app.task
def server_push_by_id(server_id: int, user_id: int, technique: str):
    logger.info("push server_id=%s job started", server_id)

    with Session(engine) as db:
        user = users_repository.get_user_by_id(db, user_id)
        if user is None:
            raise Exception("User not found")

        servers_repository.push_server_by_id(db, server_id, user, technique)
        logger.info("push server_id=%s job finished", server_id)

    return True


@celery_app.task
def push_event_by_uuid(event_uuid: str, server_id: int, user_id: int):
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


@celery_app.task
def handle_created_event(event_uuid: str):
    logger.info("handling created event uuid=%s job started", event_uuid)

    os_event = events_repository.get_event_from_opensearch(UUID(event_uuid))
    if os_event is not None:
        with Session(engine) as db:
            notifications_repository.create_event_notifications(db, "created", event=os_event)

    return True


@celery_app.task
def handle_updated_event(event_uuid: str):
    logger.info("handling updated event uuid=%s job started", event_uuid)

    os_event = events_repository.get_event_from_opensearch(UUID(event_uuid))
    if os_event is not None:
        get_opensearch_client().update(
            index="misp-events",
            id=event_uuid,
            body={"doc": {"timestamp": int(datetime.now().timestamp())}},
            refresh=True,
        )
        with Session(engine) as db:
            notifications_repository.create_event_notifications(db, "updated", event=os_event)

    return True


@celery_app.task
def handle_deleted_event(event_uuid: str):
    logger.info("handling deleted event uuid=%s job started", event_uuid)

    os_event = events_repository.get_event_from_opensearch(UUID(event_uuid))
    if os_event is not None:
        with Session(engine) as db:
            notifications_repository.create_event_notifications(db, "deleted", event=os_event)

    delete_indexed_event(event_uuid)

    return True


@celery_app.task
def handle_created_attribute(attribute_uuid: str, object_uuid, event_uuid: str | None):
    logger.info("handling created attribute uuid=%s job started", attribute_uuid)
    with Session(engine) as db:
        if object_uuid is None and event_uuid:
            events_repository.increment_attribute_count(db, event_uuid)

        os_attr = attributes_repository.get_attribute_from_opensearch(UUID(attribute_uuid))
        if os_attr is not None:
            notifications_repository.create_attribute_notifications(db, "created", attribute=os_attr)

    return True


@celery_app.task
def handle_updated_attribute(attribute_uuid: str, object_uuid, event_uuid: str | None):
    logger.info("handling updated attribute uuid=%s job started", attribute_uuid)
    with Session(engine) as db:
        os_attr = attributes_repository.get_attribute_from_opensearch(UUID(attribute_uuid))
        if os_attr is not None:
            notifications_repository.create_attribute_notifications(db, "updated", attribute=os_attr)

    return True


@celery_app.task
def handle_deleted_attribute(attribute_uuid: str, object_uuid, event_uuid: str | None):
    logger.info("handling deleted attribute uuid=%s job started", attribute_uuid)
    with Session(engine) as db:
        if object_uuid is None and event_uuid:
            events_repository.decrement_attribute_count(db, event_uuid)

        os_attr = attributes_repository.get_attribute_from_opensearch(UUID(attribute_uuid))
        if os_attr is not None:
            notifications_repository.create_attribute_notifications(db, "deleted", attribute=os_attr)

    return True


@celery_app.task
def handle_created_object(object_uuid: str, event_uuid: str | None):
    logger.info("handling created object uuid=%s job started", object_uuid)

    with Session(engine) as db:
        if event_uuid:
            events_repository.increment_object_count(db, event_uuid)

        os_obj = objects_repository.get_object_from_opensearch(UUID(object_uuid))
        if os_obj is not None:
            notifications_repository.create_object_notifications(db, "created", object=os_obj)

    return True


@celery_app.task
def handle_updated_object(object_uuid: str, event_uuid: str | None):
    logger.info("handling updated object uuid=%s job started", object_uuid)

    with Session(engine) as db:
        os_obj = objects_repository.get_object_from_opensearch(UUID(object_uuid))
        if os_obj is not None:
            notifications_repository.create_object_notifications(db, "updated", object=os_obj)

    return True


@celery_app.task
def handle_deleted_object(object_uuid: str, event_uuid: str | None):
    logger.info("handling deleted object uuid=%s job started", object_uuid)

    with Session(engine) as db:
        if event_uuid:
            events_repository.decrement_object_count(db, event_uuid)

        os_obj = objects_repository.get_object_from_opensearch(UUID(object_uuid))
        if os_obj is not None:
            notifications_repository.create_object_notifications(db, "deleted", object=os_obj)

    return True


@celery_app.task
def send_email(email: dict):
    logger.info("sending email job started")

    mail_server = os.environ.get("MAIL_SERVER")
    mail_port = os.environ.get("MAIL_PORT")
    if not mail_server:
        logger.warning("MAIL_SERVER not configured, skipping email send")
        return False

    msg = EmailMessage()
    msg["Subject"] = email["subject"]
    msg["From"] = email["from"]
    msg["To"] = email["to"]
    msg.set_content(email["body"])

    try:
        with smtplib.SMTP(mail_server, mail_port) as server:
            username = os.environ.get("MAIL_USERNAME")
            password = os.environ.get("MAIL_PASSWORD")
            if username and password:
                server.login(username, password)
            server.send_message(msg)
    except (smtplib.SMTPException, OSError) as e:
        logger.error("Failed to send email: %s", e)
        return False

    return True


@celery_app.task
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


@celery_app.task
def fetch_feed_event(event_uuid: str, feed_id: int, user_id: int):
    logger.info("fetch feed event uuid=%s job started", event_uuid)

    with Session(engine) as db:
        user = users_repository.get_user_by_id(db, user_id)
        db_feed = feeds_repository.get_feed_by_id(db, feed_id=feed_id)

        result = feeds_repository.process_feed_event(db, event_uuid, db_feed, user)

    logger.info("fetch feed event uuid=%s job finished", event_uuid)
    return result


@celery_app.task
def fetch_csv_feed(feed_id: int, user_id: int):
    logger.info("fetch csv feed id=%s job started", feed_id)

    index = 0
    rows_parsed = 0
    attributes_created = 0
    failed_rows = 0

    with Session(engine) as db:
        user = users_repository.get_user_by_id(db, user_id)
        db_feed = feeds_repository.get_feed_by_id(db, feed_id=feed_id)

        db_event = feeds_repository.get_or_create_feed_event(db, db_feed, user)

        lines = feeds_repository.fetch_csv_content_from_network(db_feed.url, extra_headers=db_feed.headers)
        rows = feeds_repository.parse_csv_feed_lines(db_feed.settings, lines)

        for row in rows:
            if db_feed.settings["csvConfig"]["header"] and index == 0:
                continue  # skip the first line if header is present

            try:
                rows_parsed += 1
                attribute = feeds_repository.process_csv_feed_row(row, db_feed.settings)

                db_attribute = attribute_schemas.AttributeCreate(
                    event_uuid=db_event.uuid,
                    type=attribute["type"],
                    value=attribute["value"],
                    category=attribute.get("category", "External analysis"),
                )

                if "distribution" in attribute:
                    db_attribute.distribution = attribute["distribution"]

                if "comment" in attribute:
                    db_attribute.comment = attribute["comment"]

                if "to_ids" in attribute:
                    db_attribute.to_ids = attribute["to_ids"]

                attributes_repository.create_attribute(db, db_attribute)
                attributes_created += 1

            except Exception as e:
                failed_rows += 1
                logger.error("Error processing CSV feed row: %s", e)

            index += 1

    logger.info("fetch csv feed id=%s job finished", feed_id)

    return {
        "result": "success",
        "message": "CSV feed=%s processed, %s rows parsed, %s attributes created, %s rows failed."
        % (db_feed.name, rows_parsed, attributes_created, failed_rows),
    }


@celery_app.task
def fetch_freetext_feed(feed_id: int, user_id: int):
    logger.info("fetch freetext feed id=%s job started", feed_id)

    rows_parsed = 0
    attributes_created = 0
    failed_rows = 0

    with Session(engine) as db:
        user = users_repository.get_user_by_id(db, user_id)
        db_feed = feeds_repository.get_feed_by_id(db, feed_id=feed_id)

        db_event = feeds_repository.get_or_create_feed_event(db, db_feed, user)

        lines = feeds_repository.fetch_csv_content_from_network(
            db_feed.url, extra_headers=db_feed.headers
        )

        freetext_config = (db_feed.settings or {}).get("freetextConfig", {})
        type_detection = freetext_config.get("type_detection", "automatic")
        fixed_type = freetext_config.get("fixed_type")

        for line in lines:
            value = line.strip()
            if not value:
                continue

            try:
                rows_parsed += 1

                if type_detection == "fixed" and fixed_type:
                    attr_type = fixed_type
                else:
                    attr_type = freetext_repository.detect_type(value)

                db_attribute = attribute_schemas.AttributeCreate(
                    event_uuid=db_event.uuid,
                    type=attr_type,
                    value=value,
                    category="External analysis",
                )
                attributes_repository.create_attribute(db, db_attribute)
                attributes_created += 1

            except Exception as e:
                failed_rows += 1
                logger.error("Error processing freetext feed line: %s", e)

    logger.info("fetch freetext feed id=%s job finished", feed_id)

    return {
        "result": "success",
        "message": "Freetext feed=%s processed, %s rows parsed, %s attributes created, %s rows failed."
        % (db_feed.name, rows_parsed, attributes_created, failed_rows),
    }


@celery_app.task
def fetch_json_feed(feed_id: int, user_id: int):
    logger.info("fetch json feed id=%s job started", feed_id)

    items_processed = 0
    attributes_created = 0
    failed_items = 0

    with Session(engine) as db:
        user = users_repository.get_user_by_id(db, user_id)
        db_feed = feeds_repository.get_feed_by_id(db, feed_id=feed_id)

        db_event = feeds_repository.get_or_create_feed_event(db, db_feed, user)

        content = feeds_repository.fetch_json_content_from_network(
            db_feed.url, extra_headers=db_feed.headers
        )
        json_cfg = (db_feed.settings or {}).get("jsonConfig") or {}
        items = feeds_repository.parse_json_feed_items(content, json_cfg)

        for item in items:
            try:
                items_processed += 1
                attribute = feeds_repository.process_json_item_to_attribute(
                    item, db_feed.settings
                )

                if attribute.get("error") or not attribute.get("type") or not attribute.get("value"):
                    failed_items += 1
                    continue

                db_attribute = attribute_schemas.AttributeCreate(
                    event_uuid=db_event.uuid,
                    type=attribute["type"],
                    value=attribute["value"],
                    category=attribute.get("category", "External analysis"),
                )

                if "comment" in attribute:
                    db_attribute.comment = attribute["comment"]

                if "to_ids" in attribute:
                    db_attribute.to_ids = attribute["to_ids"]

                attributes_repository.create_attribute(db, db_attribute)
                attributes_created += 1

            except Exception as e:
                failed_items += 1
                logger.error("Error processing JSON feed item: %s", e)

    logger.info("fetch json feed id=%s job finished", feed_id)

    return {
        "result": "success",
        "message": "JSON feed=%s processed, %s items, %s attributes created, %s failed."
        % (db_feed.name, items_processed, attributes_created, failed_items),
    }


@celery_app.task
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
        run_correlation_hunts.delay()
        return True
    finally:
        # Release the lock. If Redis isn't available this is a noop.
        try:
            if RedisClient is not None:
                RedisClient.delete(lock_key)
        except Exception:
            pass


@celery_app.task
def enforce_retention():
    logger.info("enforce_retention job started")
    with Session(engine) as db:
        runtime_settings = get_runtime_settings(db)

    retention = runtime_settings.get("retention") or {}
    if not retention.get("enabled"):
        logger.info("enforce_retention skipped: retention disabled")
        return True

    period_days = retention.get("period_days", 365)
    exempt_tags = retention.get("exempt_tags", ["retention:exempt"])
    cutoff = int(datetime.now().timestamp()) - period_days * 86400
    client = get_opensearch_client()

    must_not = (
        [{"match_phrase": {"tags.name": tag}} for tag in exempt_tags]
        if exempt_tags
        else []
    )

    # Collect all event UUIDs eligible for retention
    event_uuids = []
    search_after = None
    while True:
        body = {
            "query": {
                "bool": {
                    "must": [
                        {"range": {"timestamp": {"lt": cutoff}}},
                        {"term": {"deleted": False}},
                    ],
                    "must_not": must_not,
                }
            },
            "_source": ["uuid"],
            "size": 500,
            "sort": [{"uuid.keyword": "asc"}],
        }
        if search_after:
            body["search_after"] = search_after
        response = client.search(index="misp-events", body=body)
        hits = response["hits"]["hits"]
        if not hits:
            break
        event_uuids.extend(hit["_source"]["uuid"] for hit in hits)
        if len(hits) < 500:
            break
        search_after = hits[-1]["sort"]

    if not event_uuids:
        logger.info("enforce_retention finished: no events to purge")
        return True

    logger.info("enforce_retention: purging %s events", len(event_uuids))

    for event_uuid in event_uuids:
        logger.info("enforce_retention: purging event uuid=%s", event_uuid)

        # Collect attribute UUIDs for sighting cleanup
        attr_resp = client.search(
            index="misp-attributes",
            body={
                "query": {"term": {"event_uuid": event_uuid}},
                "_source": ["uuid"],
                "size": 10000,
            },
        )
        attr_uuids = [h["_source"]["uuid"] for h in attr_resp["hits"]["hits"]]

        # Delete sightings for these attributes
        if attr_uuids:
            client.delete_by_query(
                index="misp-sightings",
                body={"query": {"terms": {"attribute_uuid.keyword": attr_uuids}}},
                refresh=False,
                ignore=[404],
            )

        # Delete correlations
        correlations_repository.delete_event_correlations(event_uuid)

        # Delete event, attributes, and objects
        delete_indexed_event(event_uuid)

    logger.info("enforce_retention finished: %s events purged", len(event_uuids))
    return True


@celery_app.task
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
        "timestamp": timestamp or datetime.now().timestamp(),
    }

    with Session(engine) as db:
        for attribute in attributes["results"]:
            notifications_repository.create_sighting_notifications(
                db, "created", attribute=attribute, sighting=sighting
            )


@celery_app.task
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


@celery_app.task
def handle_published_event(event_uuid: str):
    logger.info("handling published event uuid=%s job started", event_uuid)

    os_event = events_repository.get_event_from_opensearch(UUID(event_uuid))
    if os_event is not None:
        with Session(engine) as db:
            notifications_repository.create_event_notifications(db, "published", event=os_event)

    logger.info("handling published event uuid=%s job finished", event_uuid)
    return True


@celery_app.task
def handle_unpublished_event(event_uuid: str):
    logger.info("handling unpublished event uuid=%s job started", event_uuid)

    os_event = events_repository.get_event_from_opensearch(UUID(event_uuid))
    if os_event is not None:
        with Session(engine) as db:
            notifications_repository.create_event_notifications(db, "unpublished", event=os_event)

    logger.info("handling unpublished event uuid=%s job finished", event_uuid)
    return True


@celery_app.task
def handle_toggled_event_correlation(event_uuid: str, disable_correlation: bool):
    logger.info("handling toggled event correlation uuid=%s job started", event_uuid)

    os_event = events_repository.get_event_from_opensearch(UUID(event_uuid))
    if os_event is None:
        logger.warning("handle_toggled_event_correlation: event %s not found", event_uuid)
        return True

    if disable_correlation:
        correlations_repository.delete_event_correlations(event_uuid)
    else:
        with Session(engine) as db:
            runtimeSettings = get_runtime_settings(db)
        correlations_repository.correlate_event(runtimeSettings, str(event_uuid))
        run_correlation_hunts.delay()

    logger.info("handling toggled event correlation uuid=%s job finished", event_uuid)
    return True


@celery_app.task
def delete_indexed_event(event_uuid: str):
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
        index="misp-attributes", body=query, refresh=True, ignore=[404]
    )
    logger.info(
        "deleted %s indexed attributes for event uuid=%s",
        response.get("deleted", 0),
        event_uuid,
    )

    # delete indexed objects
    response = OpenSearchClient.delete_by_query(
        index="misp-objects", body=query, refresh=True, ignore=[404]
    )
    logger.info(
        "deleted %s indexed objects for event uuid=%s",
        response.get("deleted", 0),
        event_uuid,
    )

    logger.info("deleting indexed event uuid=%s job finished", event_uuid)

    return True


@celery_app.task
def delete_indexed_attribute(attribute_uuid: str):
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


@celery_app.task()
def load_galaxies(user_id: int):
    """Load galaxies from the bundled misp-galaxy submodule into the database.

    If `user_id` is not provided the first user in the database will be used as
    the creator for created tags and objects.
    """
    logger.info("load_galaxies job started")

    with Session(engine) as db:
        user = None
        if user_id is not None:
            user = users_repository.get_user_by_id(db, user_id)
        if user is None:
            first = users_repository.get_users(db, skip=0, limit=1)
            user = first[0] if first else None

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


@celery_app.task()
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


@celery_app.task
def delete_indexed_object(object_uuid: str):
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


@celery_app.task
def run_hunt(hunt_id: int, **kwargs):
    logger.info("run hunt id=%s job started", hunt_id)

    with Session(engine) as db:
        result = hunts_repository.execute_hunt_system(db, hunt_id=hunt_id)
        total = result["total"] if result else 0
        logger.info("run hunt id=%s finished, %s matches", hunt_id, total)

    return True


@celery_app.task
def run_correlation_hunts():
    """Re-run all active correlation hunts. Called after correlations are regenerated."""
    logger.info("run_correlation_hunts job started")
    with Session(engine) as db:
        hunts = hunts_repository.get_active_correlation_hunts(db)
        for hunt in hunts:
            run_hunt.delay(hunt.id)
    logger.info("run_correlation_hunts job finished, %s hunts queued", len(hunts))
    return True
