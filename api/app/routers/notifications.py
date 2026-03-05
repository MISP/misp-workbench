from typing import Optional, Union
from app.auth.security import get_current_active_user
from app.db.session import get_db
from app.repositories import notifications as notifications_repository
from app.schemas import user as user_schemas
from app.schemas import notifications as notification_schemas
from fastapi import APIRouter, Depends, Security, HTTPException, status
from sqlalchemy.orm import Session
from fastapi_pagination import Page

router = APIRouter()


async def get_notification_parameters(
    read: Optional[bool] = None,
    type: Optional[str] = None,
    filter: Optional[str] = None,
):
    return {"type": type, "read": read, "filter": filter}


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
    return notifications_repository.get_user_notifications(
        db, user_id=user.id, params=params
    )


@router.patch(
    "/notifications/{notification_id}/read",
    response_model=notification_schemas.StatusResponse,
    status_code=status.HTTP_200_OK,
)
async def mark_notification_as_read(
    notification_id: Union[int, str],
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["notifications:update"]
    ),
) -> notification_schemas.StatusResponse:
    result = notifications_repository.mark_notification_as_read(
        db, notification_id, user.id
    )
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found"
        )
    return result


@router.patch(
    "/notifications/{notification_id}/unfollow",
    response_model=notification_schemas.StatusResponse,
    status_code=status.HTTP_200_OK,
)
async def unfollow_notification(
    notification_id: int,
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["notifications:update"]
    ),
) -> notification_schemas.StatusResponse:
    result = notifications_repository.unfollow_notification(db, notification_id, user.id)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found"
        )
    return result


@router.delete(
    "/notifications/all",
    response_model=notification_schemas.StatusResponse,
    status_code=status.HTTP_200_OK,
)
async def delete_all_notifications(
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["notifications:update"]
    ),
) -> notification_schemas.StatusResponse:
    return notifications_repository.delete_all_notifications(db, user.id)


@router.delete(
    "/notifications/{notification_id}",
    response_model=notification_schemas.StatusResponse,
    status_code=status.HTTP_200_OK,
)
async def delete_notification(
    notification_id: int,
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["notifications:update"]
    ),
) -> notification_schemas.StatusResponse:
    result = notifications_repository.delete_notification(db, notification_id, user.id)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found"
        )
    return result
