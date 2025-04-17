from app.auth.auth import get_current_active_user
from app.dependencies import get_db
from app.repositories import reports as report_repository
from app.schemas import user as user_schemas
from fastapi import APIRouter, Depends, HTTPException, Security, status
from sqlalchemy.orm import Session
from app.repositories import events as events_repository

router = APIRouter()


@router.get("/reports/{event_id}")
def get_event_reports_by_event_uuid(
    event_id: int,
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["reports:read"]
    ),
):

    db_event = events_repository.get_event_by_id(db, event_id=event_id)
    if db_event is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Event not found"
        )

    return report_repository.get_event_reports_by_event_uuid(event_uuid=db_event.uuid)
