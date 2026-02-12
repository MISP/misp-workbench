import os
import logging

import requests
from app.models import feed as feed_models
from app.repositories import sync as sync_repository
from app.repositories import events as events_repository
from app.repositories import organisations as organisations_repository
from app.schemas import feed as feed_schemas
from app.schemas import user as user_schemas
from app.worker import tasks
from fastapi import HTTPException, status
from pymisp import MISPEvent
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

USER_AGENT = "misp-workbench/" + os.environ.get("APP_VERSION", "")


def get_feeds(db: Session, skip: int = 0, limit: int = 100):
    return db.query(feed_models.Feed).offset(skip).limit(limit).all()


def get_feed_by_id(db: Session, feed_id: int) -> feed_models.Feed:
    return db.query(feed_models.Feed).filter(feed_models.Feed.id == feed_id).first()


def create_feed(db: Session, feed: feed_schemas.FeedCreate):
    db_feed = feed_models.Feed(
        name=feed.name,
        provider=feed.provider,
        url=feed.url,
        rules=feed.rules,
        enabled=feed.enabled,
        distribution=feed.distribution,
        sharing_group_id=feed.sharing_group_id,
        tag_id=feed.tag_id,
        default=feed.default,
        source_format=feed.source_format,
        fixed_event=feed.fixed_event,
        delta_merge=feed.delta_merge,
        event_id=feed.event_id,
        publish=feed.publish,
        override_ids=feed.override_ids,
        settings=feed.settings,
        input_source=feed.input_source,
        delete_local_file=feed.delete_local_file,
        lookup_visible=feed.lookup_visible,
        headers=feed.headers,
        caching_enabled=feed.caching_enabled,
        force_to_ids=feed.force_to_ids,
        orgc_id=feed.orgc_id,
        tag_collection_id=feed.tag_collection_id,
        cached_elements=feed.cached_elements,
        coverage_by_other_feeds=feed.coverage_by_other_feeds,
    )

    db.add(db_feed)
    db.commit()
    db.refresh(db_feed)

    return db_feed


def update_feed(
    db: Session,
    feed_id: int,
    feed: feed_schemas.FeedUpdate,
) -> feed_models.Feed:
    db_feed = get_feed_by_id(db, feed_id=feed_id)

    if db_feed is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Feed not found"
        )

    feed_patch = feed.model_dump(exclude_unset=True)
    for key, value in feed_patch.items():
        setattr(db_feed, key, value)

    db.add(db_feed)
    db.commit()
    db.refresh(db_feed)

    return db_feed


def delete_feed(db: Session, feed_id: int) -> None:
    db_feed = get_feed_by_id(db, feed_id=feed_id)

    if db_feed is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Feed not found"
        )

    db.delete(db_feed)
    db.commit()


def fetch_feed_event_by_uuid(feed, event_uuid):
    url = f"{feed.url}/{event_uuid}.json"
    response = requests.get(url, headers={"User-Agent": USER_AGENT})
    if response.status_code == 200:
        return response.json()
    else:
        raise HTTPException(
            status_code=response.status_code,
            detail=f"Failed to fetch event {event_uuid}: {response.text}",
        )


def process_feed_event(
    db: Session,
    event_uuid: str,
    feed: feed_models.Feed,
    user: user_schemas.User,
):
    logging.info(f"Fetching event {feed.url}/{event_uuid}")
    event_raw = fetch_feed_event_by_uuid(feed, event_uuid)
    event = MISPEvent()
    event.load(event_raw)

    orgc = organisations_repository.get_or_create_organisation_from_feed(
        db, event.Orgc, user=user
    )

    local_event = events_repository.get_event_by_uuid(db, event_uuid)

    # TODO: process tag_id and tag_collection_id
    # TODO: process feed.sharing_group_id
    # TODO: apply feed rules (disable_correlation, unpublish_event)

    if local_event is None:

        local_event = events_repository.create_event_from_fetched_event(
            db, event, orgc, feed, user
        )

        sync_repository.create_pulled_event_tags(db, local_event, event.tags, user)

        sync_repository.create_pulled_event_reports(
            db, local_event.uuid, event.event_reports, user
        )

        # process objects
        sync_repository.create_pulled_event_objects(
            db, local_event.id, event.objects, user
        )

        # process attributes
        sync_repository.create_pulled_event_attributes(
            db, local_event.id, event.attributes, user
        )
    else:

        local_event = events_repository.update_event_from_fetched_event(
            db, event, orgc, feed, user
        )

        sync_repository.create_pulled_event_tags(db, local_event, event.tags, user)

        sync_repository.create_pulled_event_reports(
            db, local_event.uuid, event.event_reports, user
        )

        # process objects
        sync_repository.update_pulled_event_objects(
            db, local_event.id, event.objects, user
        )

        # process attributes
        sync_repository.update_pulled_event_attributes(
            db, local_event.id, event.attributes, user
        )

    local_event.attribute_count = len(local_event.attributes)
    local_event.object_count = len(local_event.objects)
    db.add(local_event)

    db.commit()

    tasks.index_event.delay(local_event.uuid, full_reindex=True)

    return {"result": "success", "message": "Event processed"}


def get_feed_manifest(feed: feed_models.Feed):
    return requests.get(f"{feed.url}/manifest.json")


def fetch_feed(db: Session, feed_id: int, user: user_schemas.User):
    logger.info("fetch feed id=%s job started", feed_id)

    db_feed = get_feed_by_id(db, feed_id=feed_id)

    if db_feed is None:
        raise Exception("Feed not found")

    if not db_feed.enabled:
        raise Exception("Feed is not enabled")

    if db_feed is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Feed not found"
        )

    logger.info(f"Fetching feed {db_feed.id} {db_feed.name}")

    if db_feed.source_format == "misp":
        # TODO: check feed etag in redis cache
        req = get_feed_manifest(db_feed)

        if req.status_code == 200:
            manifest = req.json()

            # TODO: cache etag value in redis
            # etag = req.headers.get("etag")
            # logger.info(f"Fetching feed UUID {db_feed.uuid} ETag: {etag}")


            # filter feed events to fetch based on rules
            manifest = filter_feed_by_rules(db_feed.rules, manifest)

            feed_events_uuids = manifest.keys()

            local_feed_events = events_repository.get_events_by_uuids(
                db, feed_events_uuids
            )

            # filter out events that are already in the database and have the same or older timestamp
            skip_events = [
                str(event.uuid)
                for event in local_feed_events
                if event.timestamp >= manifest[str(event.uuid)]["timestamp"]
            ]

            feed_events_uuids = [
                uuid for uuid in feed_events_uuids if uuid not in skip_events
            ]

            # TODO: check if event is blocked by blocklist or feed rules (tags, orgs)

            # fetch events in parallel http requests

            if not feed_events_uuids:
                return {"result": "success", "message": "No new events to fetch"}

            for event_uuid in feed_events_uuids:
                tasks.fetch_feed_event.delay(event_uuid, db_feed.id, user.id)

    logger.info("fetch feed id=%s all event fetch tasks enqueued.", feed_id)
    return {
        "result": "success",
        "message": "All feed id=%s events to fetch enqueued." % feed_id,
    }

def filter_feed_by_rules(rules: dict, manifest: dict):
    # apply feed rules to filter manifest events
    if not rules or rules == {}:
        return manifest
    
    filtered_manifest = {}
    
    if "event_uuid" in rules:
        event_uuids_rule = rules["event_uuid"] if isinstance(rules["event_uuid"], list) else [rules["event_uuid"]]

    for uuid, event in manifest.items():
        # filter by event id
        if "event_uuid" in rules:
            if uuid not in event_uuids_rule:
                continue

        if "timestamp" in rules:
            try:
                timestamp_rule = int(rules["timestamp"])
            except ValueError:
                # Convert human-readable time formats (e.g., 30d, 1y) to a timestamp
                timestamp_rule = parse_human_readable_time(rules["timestamp"])

            if event["timestamp"] <= timestamp_rule:
                continue

        if "tags" in rules:
            event_tags = event.get("Tag", [])
            required_tags = rules["tags"] if isinstance(rules["tags"], list) else [rules["tags"]]
            if not any(
                tag in [
                    (t.get("name", "") if isinstance(t, dict) else getattr(t, "name", ""))
                    for t in event_tags
                ]
                for tag in required_tags
            ):
                continue

        if "orgs" in rules:
            event_org = event.get("Orgc", {}).get("name", "")
            required_orgs = rules["orgs"] if isinstance(rules["orgs"], list) else [rules["orgs"]]
            if event_org not in required_orgs:
                continue

        filtered_manifest[uuid] = event

    return filtered_manifest

def test_feed_connection(db: Session, feed: feed_schemas.FeedCreate):
    if feed.source_format == "misp":
        try:
            response = get_feed_manifest(feed)
            if response.status_code == 200:
                manifest = response.json()
                
                total_events = len(manifest)

                # apply feed rules to filter manifest events
                filtered_manifest = filter_feed_by_rules(feed.rules, manifest)
                total_filtered_events = len(filtered_manifest)

                return {"result": "success", "message": "Connection successful", "total_events": total_events, "total_filtered_events": total_filtered_events}
            else:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Failed to connect to feed: {response.text}",
                )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to connect to feed: {str(e)}",
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported feed source format: {feed.source_format}",
        )
    
def parse_human_readable_time(time_str):
    unit = time_str[-1]
    value = int(time_str[:-1])
    now = datetime.now()
    if unit == "d":
        return int((now - timedelta(days=value)).timestamp())
    elif unit == "h":
        return int((now - timedelta(hours=value)).timestamp())
    elif unit == "y":
        return int((now - timedelta(days=value * 365)).timestamp())
    else:
        raise ValueError(f"Unsupported time format: {time_str}")