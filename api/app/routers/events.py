import json

from typing import Optional, Annotated

from app.auth.auth import get_current_active_user
from app.dependencies import get_db
from app.repositories import events as events_repository
from app.repositories import tags as tags_repository
from app.repositories import attachments as attachments_repository
from app.schemas import event as event_schemas
from app.schemas import user as user_schemas
from app.schemas import object as object_schemas
from app.worker import tasks
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Response,
    Security,
    UploadFile,
    Form,
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


@router.get("/events/{event_id}", response_model=event_schemas.Event)
def get_event_by_id(
    event_id: int,
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(get_current_active_user, scopes=["events:read"]),
) -> event_schemas.Event:
    db_event = events_repository.get_event_by_id(db, event_id=event_id)
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
    tasks.index_event.delay(db_event.uuid)

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
    event_id: int,
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["events:delete"]
    ),
):
    return events_repository.delete_event(db=db, event_id=event_id)


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
async def upload_attachment(
    event_id: int,
    attachments: list[UploadFile],
    attachments_meta: Annotated[str, Form()],
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["events:update"]
    ),
) -> list[object_schemas.Object]:
    event = events_repository.get_event_by_id(db, event_id=event_id)
    if event is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Event not found"
        )

    if attachments_meta:
        attachments_meta = json.loads(attachments_meta)

    return attachments_repository.upload_attachments_to_event(
        db=db, event=event, attachments=attachments, attachments_meta=attachments_meta
    )
