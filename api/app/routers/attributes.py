from typing import Optional

from typing import Union
from uuid import UUID
from app.auth.security import get_current_active_user
from app.db.session import get_db
from app.repositories import attributes as attributes_repository
from app.repositories import events as events_repository
from app.repositories import tags as tags_repository
from app.schemas import attribute as attribute_schemas
from app.schemas import user as user_schemas
from app.worker import tasks
from fastapi import APIRouter, Depends, HTTPException, Response, Security, status, Query
from fastapi_pagination import Page
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

router = APIRouter()


async def get_attributes_parameters(
    event_uuid: Optional[str] = None,
    deleted: Optional[bool] = None,
    object_id: Optional[int] = None,
    type: Optional[str] = None,
):
    return {
        "event_uuid": event_uuid,
        "deleted": deleted,
        "object_id": object_id,
        "type": type,
    }


@router.get("/attributes/", response_model=Page[attribute_schemas.Attribute])
def get_attributes(
    params: dict = Depends(get_attributes_parameters),
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["attributes:read"]
    ),
) -> Page[attribute_schemas.Attribute]:
    return attributes_repository.get_attributes(
        db, params["event_uuid"], params["deleted"], params["object_id"], params["type"]
    )


@router.get("/attributes/search")
async def search_attributes(
    query: str = Query(..., min_length=0),
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["attributes:read"]
    ),
):

    from_value = (page - 1) * size

    return attributes_repository.search_attributes(query, page, from_value, size)

@router.get("/attributes/export")
async def export_attributes(
    query: str = Query(..., min_length=0),
    format: Optional[str] = Query("json"),
    user: user_schemas.User = Security(get_current_active_user, scopes=["attributes:read"]),
):
    results = attributes_repository.export_attributes(query, format=format)

    if format == "json":
        return JSONResponse(list(results))

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid format specified"
    )

@router.get("/attributes/{attribute_id}", response_model=attribute_schemas.Attribute)
def get_attribute_by_id(
    attribute_id: Union[int, UUID],
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["attributes:read"]
    ),
) -> attribute_schemas.Attribute:

    if isinstance(attribute_id, UUID):
        db_attribute = attributes_repository.get_attribute_by_uuid(
            db, attribute_uuid=attribute_id
        )
    else:
        db_attribute = attributes_repository.get_attribute_by_id(
            db, attribute_id=attribute_id
        )

    if db_attribute is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Attribute not found"
        )
    
    attribute = attribute_schemas.Attribute.from_orm(db_attribute)
    attribute.event_uuid = str(db_attribute.event.uuid)

    return attribute


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
    if attribute.event_id is None:
        if attribute.event_uuid is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Event ID or UUID must be provided",
            )
        event = events_repository.get_event_by_uuid(
            db, event_uuid=str(attribute.event_uuid)
        )
    else:
        event = events_repository.get_event_by_id(db, event_id=attribute.event_id)

    if event is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Event not found"
        )

    attribute.event_id = event.id
    db_attribute = attributes_repository.create_attribute(db=db, attribute=attribute)

    return db_attribute


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
    "/attributes/{attribute_id}/tag/{tag}",
    status_code=status.HTTP_201_CREATED,
)
def tag_attribute(
    attribute_id: int,
    tag: str,
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

    tag = tags_repository.get_tag_by_name(db, tag_name=tag)
    if tag is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Tag not found"
        )

    tags_repository.tag_attribute(db=db, attribute=attribute, tag=tag)

    return Response(status_code=status.HTTP_201_CREATED)


@router.delete(
    "/attributes/{attribute_id}/tag/{tag}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def untag_attribute(
    attribute_id: int,
    tag: str,
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

    tag = tags_repository.get_tag_by_name(db, tag_name=tag)
    if tag is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Tag not found"
        )

    tags_repository.untag_attribute(db=db, attribute=attribute, tag=tag)

    return Response(status_code=status.HTTP_204_NO_CONTENT)
