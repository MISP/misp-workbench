from typing import Optional

from app.auth.auth import get_current_active_user
from app.dependencies import get_db
from app.repositories import attributes as attributes_repository
from app.repositories import events as events_repository
from app.repositories import tags as tags_repository
from app.schemas import attribute as attribute_schemas
from app.schemas import user as user_schemas
from app.worker import tasks
from fastapi import APIRouter, Depends, HTTPException, Response, Security, status
from fastapi_pagination import Page
from sqlalchemy.orm import Session

router = APIRouter()


async def get_attributes_parameters(
    event_id: Optional[int] = None, deleted: Optional[bool] = None
):
    return {"event_id": event_id, "deleted": deleted}


@router.get("/attributes/", response_model=Page[attribute_schemas.Attribute])
def get_attributes(
    params: dict = Depends(get_attributes_parameters),
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["attributes:read"]
    ),
) -> Page[attribute_schemas.Attribute]:
    return attributes_repository.get_attributes(
        db, params["event_id"], params["deleted"]
    )


@router.get("/attributes/{attribute_id}", response_model=attribute_schemas.Attribute)
def get_attribute_by_id(
    attribute_id: int,
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["attributes:read"]
    ),
) -> attribute_schemas.Attribute:
    db_attribute = attributes_repository.get_attribute_by_id(
        db, attribute_id=attribute_id
    )
    if db_attribute is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Attribute not found"
        )
    return db_attribute


@router.post(
    "/attributes/",
    response_model=attribute_schemas.Attribute,
    status_code=status.HTTP_201_CREATED,
)
def create_attribute(
    attribute: attribute_schemas.AttributeCreate,
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["attributes:create"]
    ),
) -> attribute_schemas.Attribute:
    event = events_repository.get_event_by_id(
        db, event_id=attribute.event_id
    )  # TODO: only check if exists and get uuid
    if event is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Event not found"
        )

    tasks.index_event.delay(event.uuid)

    return attributes_repository.create_attribute(db=db, attribute=attribute)


@router.patch("/attributes/{attribute_id}", response_model=attribute_schemas.Attribute)
def update_attribute(
    attribute_id: int,
    attribute: attribute_schemas.AttributeUpdate,
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["attributes:update"]
    ),
) -> attribute_schemas.Attribute:
    attribute_db = attributes_repository.get_attribute_by_id(
        db, attribute_id=attribute_id
    )

    attribute_db = attributes_repository.update_attribute(
        db=db, attribute_id=attribute_id, attribute=attribute
    )
    event = events_repository.get_event_by_id(db, event_id=attribute_db.event_id)
    tasks.index_event.delay(event.uuid)

    return attribute_db


@router.delete("/attributes/{attribute_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_attribute(
    attribute_id: int,
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["attributes:delete"]
    ),
):
    attributes_repository.delete_attribute(db=db, attribute_id=attribute_id)

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/attributes/{attribute_id}/tag/{tag_id}",
    status_code=status.HTTP_201_CREATED,
)
def tag_attribute(
    attribute_id: int,
    tag_id: int,
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["attributes:update"]
    ),
):
    attribute = attributes_repository.get_attribute_by_id(db, attribute_id=attribute_id)
    if attribute is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Attribute not found"
        )

    tag = tags_repository.get_tag_by_id(db, tag_id=tag_id)
    if tag is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Tag not found"
        )

    tags_repository.tag_attribute(db=db, attribute=attribute, tag=tag)

    return Response(status_code=status.HTTP_201_CREATED)
