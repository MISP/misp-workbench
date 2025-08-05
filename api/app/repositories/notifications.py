from typing import Union
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
import json
import copy


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
            notification_models.Notification.title.ilike(f"%{filter_value}%")
            | notification_models.Notification.type.ilike(f"%{filter_value}%")
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
    else:
        return {"status": "error", "message": "Unsupported notification type"}

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
    Get all users who follow a specific organisation or event.

    Args:
        db: Database session.
        follow_key: 'organisations' or 'events'.
        uuid: The UUID of the organisation or event.

    Returns:
        List of User objects.
    """
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
    if not user_ids:
        return []

    return db.query(user_models.User).filter(user_models.User.id.in_(user_ids)).all()


def create_new_event_notifications(db: Session, event: event_models.Event):
    """Create notifications for users following the organisation of the event."""

    # get event organisation
    organisation = (
        db.query(organisation_models.Organisation)
        .filter(organisation_models.Organisation.id == event.orgc_id)
        .first()
    )

    if not organisation:
        return []

    followers = get_followers_for(db, "organisations", organisation.uuid)

    if not followers:
        return []

    notifications = []

    for follower in followers:
        user_id = follower.id
        payload = {
            "event_uuid": str(event.uuid),
            "event_name": event.info,
            "organisation_uuid": str(organisation.uuid),
            "organisation_name": organisation.name,
        }

        title = f"new event"
        notification = notification_models.Notification(
            user_id=user_id,
            type="organisation.event.new",
            entity_type="event",
            entity_uuid=event.uuid,
            read=False,
            title=title,
            payload=payload,
            created_at=datetime.now(),
        )
        notifications.append(notification)

    db.add_all(notifications)
    db.commit()

    return notifications


def unfollow_notifications(db: Session, follow_key: str, uuid: str, user_id: int):
    """
    Unfollow notifications for a specific organisation or event.

    Args:
        db: SQLAlchemy session
        follow_key: 'organisations' or 'events'
        uuid: UUID of the organisation or event
        user_id: ID of the user
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


def create_new_attribute_notifications(
    db: Session, attribute: attribute_models.Attribute
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

    followers = get_followers_for(db, "events", event.uuid)

    if not followers:
        return []

    notifications = []

    for follower in followers:
        user_id = follower.id
        payload = {
            "event_uuid": str(event.uuid),
            "event_title": event.info,
            "attribute_value": attribute.value[:10],
            "attribute_type": attribute.type,
            "organisation_uuid": str(event.orgc_id),
        }

        title = f"new attribute"
        notification = notification_models.Notification(
            user_id=user_id,
            type="event.attribute.new",
            entity_type="attribute",
            entity_uuid=attribute.uuid,
            read=False,
            title=title,
            payload=payload,
            created_at=datetime.now(),
        )
        notifications.append(notification)

    db.add_all(notifications)
    db.commit()

    return notifications

def create_new_object_notifications(
    db: Session, object: object_models.Object
):
    """Create notifications for users following event of the object."""

    # get event
    event = (
        db.query(event_models.Event)
        .filter(event_models.Event.id == object.event_id)
        .first()
    )

    if not event:
        return []

    followers = get_followers_for(db, "events", event.uuid)

    if not followers:
        return []

    notifications = []

    for follower in followers:
        user_id = follower.id
        payload = {
            "event_uuid": str(event.uuid),
            "event_title": event.info,
            "object_template": object.name,
            "organisation_uuid": str(event.orgc_id),
        }

        title = f"new object"
        notification = notification_models.Notification(
            user_id=user_id,
            type="event.object.new",
            entity_type="object",
            entity_uuid=object.uuid,
            read=False,
            title=title,
            payload=payload,
            created_at=datetime.now(),
        )
        notifications.append(notification)

    db.add_all(notifications)
    db.commit()

    return notifications