from api.app import db
from app.models import user as user_models
from app.models import event as event_models
    from app.schemas import notifications as notification_schemas
from sqlalchemy import text
import json


def get_followers_for_organisation(db, organisation_uuid: str):
    """
    Get all users who follow the organisation of the given event.
    """

    stmt = text("""
        SELECT user_id
        FROM user_settings
        WHERE namespace = 'notifications'
        AND (value -> 'follow' -> 'organisations') @> :org_array
    """)
    result = db.execute(stmt, {"org_array": json.dumps([str(organisation_uuid)])})
    user_ids = [row.user_id for row in result]

    if not user_ids:
        return []
    
    return db.query(user_models.User).filter(user_models.User.id.in_(user_ids)).all()


def create_new_event_notifications(
   event: event_models.Event
):
    # create notifications for organisation followers
    followers = get_followers_for_organisation(
        db, organisation_uuid=event.organisation.uuid
    )

    if not followers:
        return []

    notifications = []

    for follower in followers:
        user_id = follower.id
        payload = {
            "event_uuid": str(event.uuid),
            "event_name": event.name,
            "organisation_uuid": str(event.organisation.uuid),
        }

        title = f"New event in organisation {event.organisation.name}"
        notification = notification_schemas.Notification(
            user_id=user_id,
            type="organisation_event",
            entity_type="organisation",
            entity_uuid=event.organisation.uuid,
            read=False,
            title=title,
            payload=payload,
        )
        notifications.append(notification)

    db.add_all(notifications)
    db.commit()

    return notifications