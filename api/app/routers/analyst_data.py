from app.auth.security import get_current_active_user
from app.db.session import get_db
from app.repositories import analyst_data as analyst_data_repository
from app.repositories import events as events_repository
from app.schemas import analyst_data as analyst_data_schemas
from app.schemas import user as user_schemas
from app.services.analyst_relationships import get_local_relationship_types
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


@router.get("/analyst-data/events/{event_uuid}/counts")
def get_event_analyst_data_counts(
    event_uuid: str,
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["analyst_data:read"]
    ),
) -> dict[str, int]:
    """
    Analyst data totals for everything belonging to an event, keyed by object
    uuid, so a page can badge every attribute and object in one request.
    """
    db_event = events_repository.get_event_by_uuid(db, event_uuid=event_uuid)
    if db_event is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Event not found"
        )

    return analyst_data_repository.get_analyst_data_counts_for_event(
        event_uuid=str(db_event.uuid)
    )


@router.get("/analyst-data/relationship-types")
def get_relationship_types(
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["analyst_data:read"]
    ),
):
    """
    The MISP relationship vocabulary, for the relationship type picker. A type
    outside this list is still accepted on create.
    """
    return get_local_relationship_types()


# ── Writes ────────────────────────────────────────────────────────────────────


def _create(analyst_type, payload, user):
    created = analyst_data_repository.create_analyst_data(
        analyst_type=analyst_type, payload=payload, user=user
    )

    if created is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No %s found with uuid %s to attach this to"
            % (payload["object_type"], payload["object_uuid"]),
        )

    return created


@router.post("/analyst-data/notes", status_code=status.HTTP_201_CREATED)
def create_note(
    note: analyst_data_schemas.NoteCreate,
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["analyst_data:create"]
    ),
):
    return _create(analyst_data_schemas.AnalystDataType.NOTE, note.model_dump(), user)


@router.post("/analyst-data/opinions", status_code=status.HTTP_201_CREATED)
def create_opinion(
    opinion: analyst_data_schemas.OpinionCreate,
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["analyst_data:create"]
    ),
):
    return _create(
        analyst_data_schemas.AnalystDataType.OPINION, opinion.model_dump(), user
    )


@router.post("/analyst-data/relationships", status_code=status.HTTP_201_CREATED)
def create_relationship(
    relationship: analyst_data_schemas.RelationshipCreate,
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["analyst_data:create"]
    ),
):
    return _create(
        analyst_data_schemas.AnalystDataType.RELATIONSHIP,
        relationship.model_dump(),
        user,
    )


@router.put("/analyst-data/{analyst_uuid}")
def update_analyst_data(
    analyst_uuid: str,
    update: analyst_data_schemas.AnalystDataUpdate,
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["analyst_data:update"]
    ),
):
    # exclude_unset so a partial update does not blank the fields it omits
    payload = update.model_dump(exclude_unset=True)

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields to update",
        )

    try:
        updated = analyst_data_repository.update_analyst_data(
            analyst_uuid=analyst_uuid, payload=payload, user=user
        )
    except ValueError as ex:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ex))
    except PermissionError as ex:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(ex))

    if updated is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Analyst data not found"
        )

    return updated


@router.delete("/analyst-data/{analyst_uuid}")
def delete_analyst_data(
    analyst_uuid: str,
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["analyst_data:delete"]
    ),
):
    """
    Soft delete. Replies nested under this document are deleted with it, except
    any belonging to another organisation.
    """
    try:
        deleted = analyst_data_repository.delete_analyst_data(
            analyst_uuid=analyst_uuid, user=user
        )
    except PermissionError as ex:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(ex))

    if deleted is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Analyst data not found"
        )

    return deleted
