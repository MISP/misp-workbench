from app.models import user as user_models
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
