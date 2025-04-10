import os
import asyncio
import logging
from asyncio import Semaphore

import aiohttp
import requests
from app.models import event as event_models
from app.models import feed as feed_models
from app.repositories import attributes as attributes_repository
from app.repositories import events as events_repository
from app.repositories import objects as objects_repository
from app.repositories import organisations as organisations_repository
from app.schemas import feed as feed_schemas
from app.schemas import user as user_schemas
from app.worker import tasks
from fastapi import HTTPException, status
from pymisp import MISPEvent
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

MAX_CONCURRENT_CONNECTIONS = 5
MAX_CONCURRENT_CONNECTIONS_PER_HOST = 5
MAX_CONCURRENT_REQUESTS = 5
USER_AGENT = "misp-lite/" + os.environ.get("APP_VERSION", "")


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


async def fetch_feed_event_by_uuid(feed, event_uuid, session):
    url = f"{feed.url}/{event_uuid}.json"
    async with session.get(url) as response:
        return await response.json()


async def process_feed_event(
    event_uuid: str,
    local_feed_events_uuids: list[str],
    feed: feed_models.Feed,
    user: user_schemas.User,
    session,
    db: Session,
    semaphore: Semaphore,
):
    async with semaphore:
        logging.info(f"Fetching event {feed.url}/{event_uuid}")
        try:
            event_raw = await fetch_feed_event_by_uuid(feed, event_uuid, session)
            event = MISPEvent()
            event.load(event_raw)

        except Exception as e:
            logger.error(f"Failed to fetch event {event_uuid}: {str(e)}")
            return None

        try:
            orgc = organisations_repository.get_or_create_organisation_from_feed(
                db, event.Orgc, user=user
            )

            if event_uuid in local_feed_events_uuids:
                db_event = events_repository.update_event_from_fetched_event(
                    db, event, orgc, feed, user
                )

                # process objects
                db_event = objects_repository.update_objects_from_fetched_event(
                    db, db_event, event, feed, user
                )

                # process attributes
                db_event = attributes_repository.update_attributes_from_fetched_event(
                    db, db_event, event.attributes, feed, user
                )

            else:
                # TODO: process tag_id and tag_collection_id

                # TODO: process feed.sharing_group_id

                # TODO: apply feed rules (disable_correlation, unpublish_event)

                db_event = events_repository.create_event_from_fetched_event(
                    db, event, orgc, feed, user
                )

                # process objects
                db_event = objects_repository.create_objects_from_fetched_event(
                    db, db_event, event.objects, feed, user
                )

                # process attributes
                db_event = attributes_repository.create_attributes_from_fetched_event(
                    db, db_event, event.attributes, None, feed, user
                )

            # update counters
            events_repository.increment_attribute_count(
                db, db_event.id, db_event.attribute_count
            )
            events_repository.increment_object_count(
                db, db_event.id, db_event.object_count
            )
            db.commit()

            tasks.index_event.delay(db_event.uuid)

        except Exception as e:
            logger.error(f"Failed to process event {event_uuid}: {e}")


async def fetch_feeds_async(
    events_uuids: list[str],
    local_feed_events_uuids: list[str],
    feed: feed_models.Feed,
    user: user_schemas.User,
    db: Session,
):
    connector = aiohttp.TCPConnector(
        limit=MAX_CONCURRENT_CONNECTIONS,
        limit_per_host=MAX_CONCURRENT_CONNECTIONS_PER_HOST,
    )
    semaphore = Semaphore(MAX_CONCURRENT_REQUESTS)

    async with aiohttp.ClientSession(connector=connector, headers={"User-Agent": USER_AGENT}) as session:
        tasks = [
            process_feed_event(
                event_uuid, local_feed_events_uuids, feed, user, session, db, semaphore
            )
            for event_uuid in events_uuids
        ]
        await asyncio.gather(*tasks)


def get_feed_manifest(feed: feed_models.Feed):
    return requests.get(f"{feed.url}/manifest.json")


def fetch_feed(db: Session, feed_id: int, user: user_schemas.User):
    db_feed = get_feed_by_id(db, feed_id=feed_id)
    if db_feed is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Feed not found"
        )

    if not db_feed.enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Feed is not enabled"
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

            feed_events_uuids = manifest.keys()

            local_feed_events = (
                db.query(event_models.Event)
                .filter(event_models.Event.uuid.in_(feed_events_uuids))
                .all()
            )
            local_feed_events_uuids = [str(event.uuid) for event in local_feed_events]

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

            asyncio.run(
                fetch_feeds_async(
                    feed_events_uuids,
                    local_feed_events_uuids,
                    db_feed,
                    user,
                    db,
                )
            )

            return {"result": "success", "message": "Feed fetched"}

    return []
