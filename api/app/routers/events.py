import json

from typing import Optional, Annotated

from typing import Union
from uuid import UUID
from app.auth.security import get_current_active_user
from app.db.session import get_db
from app.repositories import events as events_repository
from app.repositories import tags as tags_repository
from app.repositories import attachments as attachments_repository
from app.repositories import objects as objects_repository
from app.schemas import event as event_schemas
from app.schemas import user as user_schemas
from app.schemas import object as object_schemas
from app.schemas import vulnerability as vulnerability_schemas
from app.worker import tasks
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Response,
    Security,
    UploadFile,
    Form,
    Query,
)
from fastapi_pagination import Page
from sqlalchemy.orm import Session
from starlette import status
from fastapi.responses import JSONResponse

router = APIRouter()


async def get_events_parameters(
    info: Optional[str] = None,
    deleted: Optional[bool] = None,
    uuid: Optional[str] = None,
):
    return {"info": info, "deleted": deleted, "uuid": uuid}


@router.get("/events/", response_model=Page[event_schemas.Event])
async def get_events(
    params: dict = Depends(get_events_parameters),
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(get_current_active_user, scopes=["events:read"]),
) -> Page[event_schemas.Event]:
    return events_repository.get_events(
        db, params["info"], params["deleted"], params["uuid"]
    )


@router.get("/events/search")
async def search_events(
    query: str = Query(..., min_length=0),
    searchAttributes: Optional[bool] = Query(False),
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    user: user_schemas.User = Security(get_current_active_user, scopes=["events:read"]),
):

    from_value = (page - 1) * size

    return events_repository.search_events(
        query, searchAttributes, page, from_value, size
    )

@router.get("/events/export")
async def export_events(
    query: str = Query(..., min_length=0),
    searchAttributes: Optional[bool] = Query(False),
    format: Optional[str] = Query("json"),
    user: user_schemas.User = Security(get_current_active_user, scopes=["events:read"]),
):
    return events_repository.export_events(query, searchAttributes)


@router.get("/events/{event_id}", response_model=event_schemas.Event)
def get_event_by_id(
    event_id: Union[int, UUID],
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(get_current_active_user, scopes=["events:read"]),
) -> event_schemas.Event:

    if isinstance(event_id, int):
        db_event = events_repository.get_event_by_id(db, event_id=event_id)
    else:
        db_event = events_repository.get_event_by_uuid(db, event_uuid=event_id)

    if db_event is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Event not found"
        )
    return db_event


@router.post(
    "/events/", response_model=event_schemas.Event, status_code=status.HTTP_201_CREATED
)
def create_event(
    event_create_request: event_schemas.EventCreate,
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["events:create"]
    ),
) -> event_schemas.Event:
    db_event = events_repository.get_user_by_info(db, info=event_create_request.info)
    if db_event:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An event with this info already exists",
        )
    event_create_request.user_id = user.id
    event_create_request.org_id = user.org_id

    db_event = events_repository.create_event(db=db, event=event_create_request)
    tasks.index_event.delay(db_event.uuid, full_reindex=True)

    return db_event


@router.patch("/events/{event_id}", response_model=event_schemas.Event)
def update_event(
    event_id: int,
    event: event_schemas.EventUpdate,
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["events:update"]
    ),
) -> event_schemas.Event:
    return events_repository.update_event(db=db, event_id=event_id, event=event)


@router.delete("/events/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_event(
    event_id: Union[int, UUID],
    force: Optional[bool] = Query(False),
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["events:delete"]
    ),
):
    return events_repository.delete_event(db=db, event_id=event_id, force=force)


@router.post(
    "/events/{event_id}/tag/{tag}",
    status_code=status.HTTP_201_CREATED,
)
def tag_event(
    event_id: int,
    tag: str,
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["events:update"]
    ),
):
    event = events_repository.get_event_by_id(db, event_id=event_id)
    if event is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Event not found"
        )

    tag = tags_repository.get_tag_by_name(db, tag_name=tag)
    if tag is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Tag not found"
        )

    tags_repository.tag_event(db=db, event=event, tag=tag)

    return Response(status_code=status.HTTP_201_CREATED)


@router.delete(
    "/events/{event_id}/tag/{tag}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def untag_event(
    event_id: int,
    tag: str,
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["events:update"]
    ),
):
    event = events_repository.get_event_by_id(db, event_id=event_id)
    if event is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Event not found"
        )

    tag = tags_repository.get_tag_by_name(db, tag_name=tag)
    if tag is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Tag not found"
        )

    tags_repository.untag_event(db=db, event=event, tag=tag)

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/events/{event_id}/upload_attachments/",
    status_code=status.HTTP_200_OK,
)
async def upload_attachments(
    event_id: Union[int, UUID],
    attachments: list[UploadFile],
    attachments_meta: Annotated[str, Form()],
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["events:update"]
    ),
) -> list[object_schemas.Object]:
    if isinstance(event_id, int):
        db_event = events_repository.get_event_by_id(db, event_id=event_id)
    else:
        db_event = events_repository.get_event_by_uuid(db, event_uuid=event_id)

    if db_event is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Event not found"
        )

    if attachments_meta:
        attachments_meta = json.loads(attachments_meta)

    objects = attachments_repository.upload_attachments_to_event(
        db=db,
        event=db_event,
        attachments=attachments,
        attachments_meta=attachments_meta,
    )

    return objects


@router.get(
    "/events/{event_uuid}/attachments", response_model=Page[object_schemas.Object]
)
def get_event_attachments(
    event_uuid: str,
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(get_current_active_user, scopes=["events:read"]),
) -> Page[object_schemas.Object]:
    db_event = events_repository.get_event_by_uuid(db, event_uuid=event_uuid)
    if db_event is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Event not found"
        )

    return objects_repository.get_objects(
        db,
        event_uuid=db_event.uuid,
        deleted=False,
        template_uuid=[
            "688c46fb-5edb-40a3-8273-1af7923e2215"  # TODO: get the object template from the json file
        ],
    )


@router.post(
    "/events/force-index",
    status_code=status.HTTP_201_CREATED,
)
async def force_index(
    event_uuid: Optional[UUID] = Query(None, alias="uuid"),
    event_id: Optional[int] = Query(None, alias="id"),
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["events:update"]
    ),
):

    if event_uuid:
        tasks.index_event.delay(event_uuid, full_reindex=True)
        return JSONResponse(
            content={"message": f"Indexing started for event {event_uuid}."},
            status_code=status.HTTP_202_ACCEPTED,
        )

    if event_id:
        db_event = events_repository.get_event_by_id(db, event_id=event_id)
        if db_event is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Event not found"
            )
        tasks.index_event.delay(db_event.uuid, full_reindex=True)
        return JSONResponse(
            content={"message": f"Indexing started for event {db_event.uuid}."},
            status_code=status.HTTP_202_ACCEPTED,
        )

    uuids = events_repository.get_event_uuids(db)
    for uuid in uuids:
        tasks.index_event.delay(uuid[0], full_reindex=True)

    return JSONResponse(
        content={"message": "Indexing started for all events."},
        status_code=status.HTTP_202_ACCEPTED,
    )


@router.post("/events/{event_uuid}/publish")
def publish(
    event_uuid: UUID,
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["events:publish"]
    ),
):
    db_event = events_repository.get_event_by_uuid(db, event_uuid=event_uuid)
    if db_event is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Event not found"
        )

    events_repository.publish_event(db, db_event)

    return JSONResponse(
        content={"message": f"Event {event_uuid} has been published."},
        status_code=status.HTTP_200_OK,
    )


@router.post("/events/{event_uuid}/unpublish")
def unpublish(
    event_uuid: UUID,
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["events:publish"]
    ),
):
    db_event = events_repository.get_event_by_uuid(db, event_uuid=event_uuid)
    if db_event is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Event not found"
        )

    events_repository.unpublish_event(db, db_event)

    return JSONResponse(
        content={"message": f"Event {event_uuid} has been unpublished."},
        status_code=status.HTTP_200_OK,
    )


@router.post("/events/{event_uuid}/toggle-correlation")
def toggle_correlation(
    event_uuid: UUID,
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["events:update"]
    ),
):
    db_event = events_repository.get_event_by_uuid(db, event_uuid=event_uuid)
    if db_event is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Event not found"
        )

    events_repository.toggle_event_correlation(db, db_event)

    return JSONResponse(
        content={
            "message": f"Event {event_uuid} disable_correlation has been toggled."
        },
        status_code=status.HTTP_200_OK,
    )


@router.post("/events/{event_uuid}/import")
def import_data(
    event_uuid: UUID,
    db: Session = Depends(get_db),
    data: dict = {},
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["events:import"]
    ),
):
    db_event = events_repository.get_event_by_uuid(db, event_uuid=event_uuid)
    if db_event is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Event not found"
        )

    try:
        result = events_repository.import_data(db, event=db_event, data=data)
        return JSONResponse(
            content=result,
            status_code=status.HTTP_202_ACCEPTED,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred during import: {str(e)}",
        )


@router.get(
    "/events/{event_uuid}/vulnerabilities", response_model=list[vulnerability_schemas.Vulnerability]
)
def get_event_vulnerabilities(
    event_uuid: str,
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(get_current_active_user, scopes=["events:read"]),
) -> list[vulnerability_schemas.Vulnerability]:
    db_event = events_repository.get_event_by_uuid(db, event_uuid=event_uuid)
    if db_event is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Event not found"
        )

    return events_repository.get_event_vulnerabilities(
        db,
        event_uuid=db_event.uuid,
    )