from typing import Union
import uuid
from app.models import user as user_models
from app.models import notification as notification_models
from app.models import organisation as organisation_models
from app.models import object as object_models
from app.models import event as event_models
from app.models import attribute as attribute_models
from app.repositories import user_settings as user_settings_repository
from sqlalchemy import select, update, text
from sqlalchemy.orm import Session
from fastapi_pagination.ext.sqlalchemy import paginate
from datetime import datetime
from app.services.redis import get_redis_client
import json
import copy

CACHE_TTL = 60

def get_user_notifications(db: Session, user_id: int, params: dict = {}):
    query = select(notification_models.Notification)
    query = query.where(notification_models.Notification.user_id == user_id)

    if params.get("type") is not None:
        query = query.where(notification_models.Notification.type == params["type"])
    if params.get("read") is not None:
        query = query.where(notification_models.Notification.read == params["read"])
    if params.get("filter") is not None and params["filter"] != "":
        filter_value = params["filter"]
        query = query.where(
            notification_models.Notification.type.ilike(f"%{filter_value}%")
        )

    query = query.order_by(notification_models.Notification.created_at.desc())

    return paginate(db, query)


def mark_notification_as_read(
    db: Session, notification_id: Union[int, str], user_id: int
):

    if isinstance(notification_id, str) and notification_id == "all":
        notification_id = "all"

        # update all notifications for the user
        stmt = (
            update(notification_models.Notification)
            .where(notification_models.Notification.user_id == user_id)
            .values(read=True)
        )

        db.execute(stmt)
        db.commit()
    else:
        notification = (
            db.query(notification_models.Notification)
            .filter(
                notification_models.Notification.id == notification_id,
                notification_models.Notification.user_id == user_id,
            )
            .first()
        )

        if not notification:
            return None

        notification.read = True
        db.commit()
        db.refresh(notification)

    return {"status": "success"}


def unfollow_notification(db: Session, notification_id: int, user_id: int):

    notification = (
        db.query(notification_models.Notification)
        .filter(
            notification_models.Notification.id == notification_id,
            notification_models.Notification.user_id == user_id,
        )
        .first()
    )

    if not notification:
        return None

    follow_key = ""
    uuid = ""
    if notification.type.startswith("event"):
        follow_key = "events"
        uuid = notification.payload.get("event_uuid")
    elif notification.type.startswith("organisation"):
        follow_key = "organisations"
        uuid = notification.payload.get("organisation_uuid")
    elif notification.type.startswith("attribute"):
        follow_key = "attributes"
        uuid = notification.payload.get("attribute_uuid")
    elif notification.type.startswith("object"):
        follow_key = "objects"
        uuid = notification.payload.get("object_uuid")
    else:
        return {"status": "error", "message": "Unsupported notification type"}

    invalidate_follow_cache(follow_key, uuid)

    unfollow_notifications(
        db,
        follow_key=follow_key,
        uuid=uuid,
        user_id=user_id,
    )

    # delete the notification
    db.delete(notification)
    db.commit()

    return {"status": "success"}


def get_followers_for(db, follow_key: str, uuid: str):
    """
    Get all users who follow a specific organisation, event, object or attribute.

    Args:
        db: Database session.
        follow_key: 'organisations', 'events', 'objects' or 'attributes'.
        uuid: The UUID of the organisation, event, object or attribute.

    Returns:
        List of user ids.
    """

    cache_key = f"notifications:followers:{follow_key}:{uuid}"
    RedisClient = get_redis_client()
    cached = RedisClient.get(cache_key)
    if cached:
        user_ids = json.loads(cached)
    else:
        stmt = text(
            f"""
            SELECT user_id
            FROM user_settings
            WHERE namespace = 'notifications'
            AND (value -> 'follow' -> :key) @> :uuid_array
            """
        )
        result = db.execute(
            stmt,
            {
                "key": follow_key,
                "uuid_array": json.dumps([str(uuid)]),
            },
        )

        user_ids = [row.user_id for row in result]
        

        RedisClient.setex(cache_key, CACHE_TTL, json.dumps(user_ids))
    
    if not user_ids:
        return []
    
    return user_ids


def build_event_notification(
    user_id: int, type: str, event, organisation
) -> notification_models.Notification:
    return notification_models.Notification(
        user_id=user_id,
        type=type,
        entity_type="event",
        entity_uuid=event.uuid,
        read=False,
        payload={
            "event_uuid": str(event.uuid),
            "event_name": event.info,
            "organisation_uuid": str(organisation.uuid),
            "organisation_name": organisation.name,
        },
        created_at=datetime.now(),
    )


def create_event_notifications(db: Session, type: str, event: event_models.Event):
    """Create notifications for users following the organisation or event."""

    # Get event organisation
    organisation = (
        db.query(organisation_models.Organisation)
        .filter(organisation_models.Organisation.id == event.orgc_id)
        .first()
    )

    if not organisation:
        return []

    notifications = []

    # Followers of the organisation
    org_followers = get_followers_for(db, "organisations", organisation.uuid)
    notifications += [
        build_event_notification(
            follower,
            f"organisation.event.{type}",
            event=event,
            organisation=organisation,
        )
        for follower in org_followers
    ]

    # Followers of the specific event
    event_followers = get_followers_for(db, "events", event.uuid)
    notifications += [
        build_event_notification(
            follower, f"event.{type}", event=event, organisation=organisation
        )
        for follower in event_followers
    ]

    if notifications:
        db.add_all(notifications)
        db.commit()

    return notifications


def unfollow_notifications(db: Session, follow_key: str, uuid: str, user_id: int):
    """
    Unfollow notifications for a specific organisation or event.
    """

    user_settings = user_settings_repository.get_user_setting(
        db, user_id, "notifications"
    )
    if not user_settings:
        return {"status": "error", "message": "User settings not found"}

    followed_items = user_settings.value.get("follow", {}).get(follow_key, [])

    if uuid not in followed_items:
        return {
            "status": "error",
            "message": f"User is not following this {follow_key[:-1]}",
        }

    updated_items = [str(i) for i in followed_items if str(i) != uuid]

    updated_value = copy.deepcopy(user_settings.value)
    updated_value.setdefault("follow", {})[follow_key] = updated_items

    user_settings_repository.set_user_setting(
        db, user_id, "notifications", updated_value
    )

    return {"status": "success"}


def build_attribute_notification(
    user_id: int, type: str, attribute, event, object=None
) -> notification_models.Notification:

    payload = {
        "event_uuid": str(event.uuid),
        "event_title": event.info,
        "attribute_value": attribute.value[:10],
        "attribute_type": attribute.type,
    }

    if object:
        payload["object_uuid"] = str(object.uuid)
        payload["object_name"] = object.name

    return notification_models.Notification(
        user_id=user_id,
        type=type,
        entity_type="attribute",
        entity_uuid=attribute.uuid,
        read=False,
        payload=payload,
        created_at=datetime.now(),
    )


def create_attribute_notifications(
    db: Session, type: str, attribute: attribute_models.Attribute
):
    """Create notifications for users following event of the attribute."""

    # get event
    event = (
        db.query(event_models.Event)
        .filter(event_models.Event.id == attribute.event_id)
        .first()
    )

    if not event:
        return []

    notifications = []

    # Followers of the specific attribute
    attr_followers = get_followers_for(db, "attributes", attribute.uuid)
    notifications += [
        build_attribute_notification(
            follower,
            f"attribute.{type}",
            attribute=attribute,
            event=event,
        )
        for follower in attr_followers
    ]

    # If the attribute is linked to an object, we can also notify followers of that object
    if attribute.object_id:
        object = (
            db.query(object_models.Object)
            .filter(object_models.Object.id == attribute.object_id)
            .first()
        )
        if object:
            notifications = build_attribute_notification(
                db,
                f"object.attribute.{type}",
                attribute=attribute,
                event=event,
                object=object,
            )
            return notifications

    # Followers of the event
    event_followers = get_followers_for(db, "events", event.uuid)
    notifications += [
        build_attribute_notification(
            follower, f"event.attribute.{type}", attribute=attribute, event=event
        )
        for follower in event_followers
    ]

    if notifications:
        db.add_all(notifications)
        db.commit()

    return notifications


def build_object_notification(
    user_id: int, type: str, object, event
) -> notification_models.Notification:
    return notification_models.Notification(
        user_id=user_id,
        type=type,
        entity_type="object",
        entity_uuid=object.uuid,
        read=False,
        payload={
            "event_uuid": str(event.uuid),
            "event_title": event.info,
            "object_name": object.name,
        },
        created_at=datetime.now(),
    )


def create_object_notifications(db: Session, type: str, object: object_models.Object):
    """Create notifications for users following event of the object."""

    # get event
    event = (
        db.query(event_models.Event)
        .filter(event_models.Event.id == object.event_id)
        .first()
    )

    if not event:
        return []

    notifications = []

    # Followers of the event
    event_followers = get_followers_for(db, "events", event.uuid)
    notifications += [
        build_object_notification(
            follower, f"event.object.{type}", object=object, event=event
        )
        for follower in event_followers
    ]

    # Followers of the specific object
    obj_followers = get_followers_for(db, "objects", object.uuid)
    notifications += [
        build_object_notification(
            follower,
            f"object.{type}",
            object=object,
            event=event,
        )
        for follower in obj_followers
    ]

    if notifications:
        db.add_all(notifications)
        db.commit()

    return notifications


def create_sighting_notifications(
    db: Session, type: str, attribute: dict, sighting: dict
):
    """Create sighting notifications for users following an attribute."""
    if not attribute or not sighting:
        return []

    # Get followers of the attribute
    attribute_followers = get_followers_for(
        db, "attributes", attribute["_source"]["uuid"]
    )

    notifications = []
    for follower in attribute_followers:
        notification = notification_models.Notification(
            user_id=follower,
            type=f"attribute.sighting.{type}",
            entity_type="attribute",
            entity_uuid=attribute["_source"]["uuid"],
            read=False,
            payload={
                "sighting_value": sighting["value"],
                "sighting_type": sighting.get("type", "positive"),
                "organisation": sighting["observer"]["organisation"],
                "timestamp": sighting.get("timestamp", datetime.now().timestamp()),
                "attribute_type": attribute["_source"]["type"],
                "attribute_uuid": attribute["_source"]["uuid"],
            },
            created_at=datetime.now(),
        )
        notifications.append(notification)

    if notifications:
        db.add_all(notifications)
        db.commit()

    return notifications


def create_correlation_notifications(db: Session, type: str, correlation: dict):
    """Create correlation notifications for users following an attribute."""
    if not correlation:
        return []

    # Get followers of the attribute
    attribute_followers = get_followers_for(
        db, "attributes", correlation["source_attribute_uuid"]
    )

    notifications = []
    for follower in attribute_followers:
        notification = notification_models.Notification(
            user_id=follower,
            type=f"attribute.correlation.{type}",
            entity_type="attribute",
            entity_uuid=correlation["source_attribute_uuid"],
            read=False,
            payload={
                "source_event_uuid": correlation["source_event_uuid"],
                "target_event_uuid": correlation["target_event_uuid"],
                "target_attribute_uuid": correlation["target_attribute_uuid"],
                "target_attribute_type": correlation["target_attribute_type"],
                "target_attribute_value": correlation["target_attribute_value"],
            },
            created_at=datetime.now(),
        )
        notifications.append(notification)

    if notifications:
        db.add_all(notifications)
        db.commit()

    return notifications

def invalidate_follow_cache(entity_type: str, entity_uuid: str):
    RedisClient = get_redis_client()
    RedisClient.delete(f"notifications:followers:{entity_type}:{entity_uuid}")