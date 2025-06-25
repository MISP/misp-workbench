from app.auth.auth import get_current_active_user
from app.dependencies import get_db
from app.repositories import reports as report_repository
from app.schemas import user as user_schemas
from fastapi import APIRouter, Depends, HTTPException, Security, status
from sqlalchemy.orm import Session
from app.repositories import events as events_repository

router = APIRouter()


@router.get("/reports/{event_uuid}")
def get_event_reports_by_event_uuid(
    event_uuid: str,
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["reports:read"]
    ),
):

    db_event = events_repository.get_event_by_uuid(db, event_uuid=event_uuid)
    if db_event is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Event not found"
        )

    return report_repository.get_event_reports_by_event_uuid(event_uuid=db_event.uuid)


@router.post("/reports/{event_uuid}")
def create_event_report(
    event_uuid: str,
    report: dict,
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["reports:create"]
    ),
):

    db_event = events_repository.get_event_by_uuid(db, event_uuid=event_uuid)
    if db_event is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Event not found"
        )

    return report_repository.create_event_report(event=db_event, report=report)


@router.put("/reports/{report_uuid}")
def update_event_report(
    report_uuid: str,
    report: dict,
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["reports:update"]
    ),
):
    return report_repository.update_event_report(report_uuid=report_uuid, report=report)


@router.delete("/reports/{report_uuid}")
def delete_event_report(
    report_uuid: str,
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["reports:delete"]
    ),
):
    return report_repository.delete_event_report(report_uuid=report_uuid)
