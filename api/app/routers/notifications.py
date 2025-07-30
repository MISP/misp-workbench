from typing import Optional
from app.auth.security import get_current_active_user
from app.db.session import get_db
from app.repositories import notifications as notifications_repository
from app.schemas import user as user_schemas
from app.schemas import notifications as notification_schemas
from fastapi import (
    APIRouter,
    Depends,
    Security,
)
from sqlalchemy.orm import Session
from fastapi_pagination import Page

router = APIRouter()


async def get_notification_parameters(
    read: Optional[bool] = None,
    type: Optional[str] = None,
):
    return {"type": type, "read": read}


@router.get(
    "/notifications",
    response_model=Page[notification_schemas.Notification],
)
async def get_my_notifications(
    db: Session = Depends(get_db),
    params: dict = Depends(get_notification_parameters),
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["notifications:read"]
    ),
) -> Page[notification_schemas.Notification]:
    return notifications_repository.get_user_notifications(db, user_id=user.id, params=params)


@router.patch(
    "/notifications/{notification_id}/read",
    response_model=notification_schemas.Notification,
)
async def mark_notification_as_read(
    notification_id: int,
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["notifications:update"]
    ),
) -> notification_schemas.Notification:
    notification = notifications_repository.mark_notification_as_read(db, notification_id, user.id)
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found or not accessible")
    
    return notification


@router.get(
    "/notifications/followers/organisation/{organisation_uuid}",
    response_model=list[user_schemas.User],
)
async def get_users_following_organisation(
    organisation_uuid: str,
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["notifications:admin    "]
    ),
) -> list[user_schemas.User]:
    return notifications_repository.get_followers_for_organisation(
        db, organisation_uuid=organisation_uuid
    )
