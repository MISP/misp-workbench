from typing import Union
from app.models import user as user_models
from app.models import notification as notification_models
from app.models import organisation as organisation_models
from app.models import event as event_models
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

    if notification.type.startswith("organisation"):
        unfollow_organisation_notifications(
            db,
            organisation_uuid=notification.payload.get("organisation_uuid"),
            user_id=user_id,
        )

    # delete the notification
    db.delete(notification)
    db.commit()

    return {"status": "success"}


def get_followers_for_organisation(db, organisation_uuid: str):
    """
    Get all users who follow the organisation of the given event.
    """

    stmt = text(
        """
        SELECT user_id
        FROM user_settings
        WHERE namespace = 'notifications'
        AND (value -> 'follow' -> 'organisations') @> :org_array
        """
    )
    result = db.execute(stmt, {"org_array": json.dumps([str(organisation_uuid)])})
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

    followers = get_followers_for_organisation(db, organisation_uuid=organisation.uuid)

    if not followers:
        return []

    notifications = []

    for follower in followers:
        user_id = follower.id
        payload = {
            "event_uuid": str(event.uuid),
            "event_name": event.info,
            "organisation_uuid": str(organisation.uuid),
        }

        title = f"new event from {organisation.name}"
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


def unfollow_organisation_notifications(
    db: Session, organisation_uuid: str, user_id: int
):
    """
    Unfollow notifications for a specific organisation.
    """

    user_settings = user_settings_repository.get_user_setting(
        db, user_id, "notifications"
    )
    if not user_settings:
        return {"status": "error", "message": "User settings not found"}

    if organisation_uuid not in user_settings.value.get("follow", {}).get(
        "organisations", []
    ):
        return {
            "status": "error",
            "message": "User is not following this organisation",
        }

    orgs = user_settings.value.get("follow", {}).get("organisations", [])
    updated_orgs = [str(o) for o in orgs if str(o) != organisation_uuid]

    updated_value = copy.deepcopy(user_settings.value)
    updated_value["follow"]["organisations"] = updated_orgs

    user_settings_repository.set_user_setting(
        db, user_id, "notifications", updated_value
    )
