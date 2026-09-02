from app.auth.security import get_current_active_user
from app.db.session import get_db
from app.repositories import analyst_data as analyst_data_repository
from app.repositories import events as events_repository
from app.schemas import analyst_data as analyst_data_schemas
from app.schemas import user as user_schemas
from fastapi import APIRouter, Depends, HTTPException, Query, Security, status
from sqlalchemy.orm import Session

router = APIRouter()


@router.get(
    "/analyst-data/events/{event_uuid}",
    response_model=analyst_data_schemas.AnalystDataListResponse,
)
def get_event_analyst_data(
    event_uuid: str,
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["analyst_data:read"]
    ),
):
    """
    Analyst data attached directly to an event, threads included.

    Analyst data on the event's attributes and objects is reachable through
    `/analyst-data/objects/{object_uuid}`.
    """
    db_event = events_repository.get_event_by_uuid(db, event_uuid=event_uuid)
    if db_event is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Event not found"
        )

    return analyst_data_repository.get_analyst_data_by_event_uuid(
        event_uuid=str(db_event.uuid)
    )


@router.get(
    "/analyst-data/events/{event_uuid}/all",
    response_model=list[dict],
)
def get_all_event_analyst_data(
    event_uuid: str,
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["analyst_data:read"]
    ),
):
    """
    Every analyst data document captured for an event, flat and unthreaded,
    including the data attached to its attributes and objects.
    """
    db_event = events_repository.get_event_by_uuid(db, event_uuid=event_uuid)
    if db_event is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Event not found"
        )

    return analyst_data_repository.get_all_analyst_data_for_event(
        event_uuid=str(db_event.uuid)
    )


@router.get(
    "/analyst-data/objects/{object_uuid}",
    response_model=analyst_data_schemas.AnalystDataListResponse,
)
def get_object_analyst_data(
    object_uuid: str,
    object_type: str = Query(
        None,
        description=(
            "Restrict to analyst data attached with this MISP object type "
            "(Attribute, Object, EventReport, ...). Omit to match any type "
            "carrying this uuid."
        ),
    ),
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["analyst_data:read"]
    ),
):
    """
    Analyst data attached to an attribute, object, event report or any other
    MISP object type, threads included.
    """
    if (
        object_type is not None
        and object_type not in analyst_data_schemas.ANALYST_DATA_PARENT_TYPES
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported object_type '%s'. Expected one of: %s"
            % (
                object_type,
                ", ".join(sorted(analyst_data_schemas.ANALYST_DATA_PARENT_TYPES)),
            ),
        )

    return analyst_data_repository.get_analyst_data_by_object_uuid(
        object_uuid=object_uuid, object_type=object_type
    )
