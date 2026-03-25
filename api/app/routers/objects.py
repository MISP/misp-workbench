from uuid import UUID
from typing import Optional, Union

from app.auth.security import get_current_active_user
from app.db.session import get_db
from app.repositories import events as events_repository
from app.repositories import objects as objects_repository
from app.schemas import object as object_schemas
from app.schemas import user as user_schemas
from app.worker import tasks
from fastapi import APIRouter, Depends, HTTPException, Security, status, Response
from sqlalchemy.orm import Session
from fastapi_pagination import Page, Params

router = APIRouter()


async def get_objects_parameters(
    event_uuid: Optional[str] = None,
    deleted: Optional[bool] = False,
    template_uuid: list[UUID] = None,
):
    return {"event_uuid": event_uuid, "deleted": deleted, "template_uuid": template_uuid}


@router.get("/objects/", response_model=Page[object_schemas.Object])
def get_objects(
    params: dict = Depends(get_objects_parameters),
    page_params: Params = Depends(),
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["objects:read"]
    ),
) -> Page[object_schemas.Object]:
    return objects_repository.get_objects_from_opensearch(
        page_params,
        params["event_uuid"],
        params["deleted"],
        params["template_uuid"],
    )


@router.get("/objects/{object_id}", response_model=object_schemas.Object)
def get_object_by_id(
    object_id: Union[int, UUID],
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["objects:read"]
    ),
):
    os_object = objects_repository.get_object_from_opensearch(object_id)
    if os_object is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Object not found"
        )
    return os_object

@router.post(
    "/objects/",
    response_model=object_schemas.Object,
    status_code=status.HTTP_201_CREATED,
)
def create_object(
    object: object_schemas.ObjectCreate,
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["objects:create"]
    ),
):
    
    if object.event_id:
        event = events_repository.get_event_by_id(db, event_id=object.event_id)
    elif object.event_uuid:
        event = events_repository.get_event_by_uuid(db, event_uuid=object.event_uuid)
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Event UUID is required"
        )

    if event is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Event not found"
        )

    object.event_id = event.id
    object_db = objects_repository.create_object(db=db, object=object)

    return object_db


@router.patch("/objects/{object_id}", response_model=object_schemas.Object)
def update_object(
    object_id: int,
    object: object_schemas.ObjectUpdate,
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["objects:update"]
    ),
):
    return objects_repository.update_object(db=db, object_id=object_id, object=object)


@router.delete("/objects/{object_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_object(
    object_id: Union[int, UUID],
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["objects:delete"]
    ),
):
    objects_repository.delete_object(db=db, object_id=object_id)

    return Response(status_code=status.HTTP_204_NO_CONTENT)
