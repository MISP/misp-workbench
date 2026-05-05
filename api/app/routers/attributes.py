from typing import Optional
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
from fastapi_pagination import Page, Params
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

router = APIRouter()


async def get_attributes_parameters(
    event_uuid: Optional[str] = None,
    deleted: Optional[bool] = None,
    object_uuid: Optional[UUID] = None,
    type: Optional[str] = None,
):
    return {
        "event_uuid": event_uuid,
        "deleted": deleted,
        "object_uuid": object_uuid,
        "type": type,
    }


@router.get("/attributes/", response_model=Page[attribute_schemas.Attribute])
def get_attributes(
    params: dict = Depends(get_attributes_parameters),
    page_params: Params = Depends(),
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["attributes:read"]
    ),
) -> Page[attribute_schemas.Attribute]:
    return attributes_repository.get_attributes_from_opensearch(
        page_params,
        params["event_uuid"],
        params["deleted"],
        params["object_uuid"],
        params["type"],
    )


@router.get("/attributes/search")
async def search_attributes(
    query: str = Query(..., min_length=0),
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    sort_by: Optional[str] = Query("@timestamp", pattern="^(_score|@timestamp)$"),
    sort_order: Optional[str] = Query("desc", pattern="^(asc|desc)$"),
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["attributes:read"]
    ),
):

    from_value = (page - 1) * size

    return attributes_repository.search_attributes(query, page, from_value, size, sort_by, sort_order)

@router.get("/attributes/histogram")
async def get_attributes_histogram(
    query: str = Query(..., min_length=0),
    interval: Optional[str] = Query("1d", pattern="^(1d|1w|1M)$"),
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["attributes:read"]
    ),
):
    return attributes_repository.search_attributes_histogram(query, interval)


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

@router.get("/attributes/{attribute_uuid}", response_model=attribute_schemas.Attribute)
def get_attribute_by_uuid(
    attribute_uuid: UUID,
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["attributes:read"]
    ),
) -> attribute_schemas.Attribute:
    os_attribute = attributes_repository.get_attribute_from_opensearch(attribute_uuid)
    if os_attribute is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Attribute not found"
        )
    return os_attribute


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
    if attribute.event_uuid is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Event UUID must be provided",
        )

    event = events_repository.get_event_from_opensearch(attribute.event_uuid)

    if event is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Event not found"
        )

    attribute.event_uuid = event.uuid
    return attributes_repository.create_attribute(db=db, attribute=attribute)


@router.patch("/attributes/{attribute_uuid}", response_model=attribute_schemas.Attribute)
def update_attribute(
    attribute_uuid: UUID,
    attribute: attribute_schemas.AttributeUpdate,
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["attributes:update"]
    ),
) -> attribute_schemas.Attribute:
    return attributes_repository.update_attribute(
        db=db, attribute_uuid=attribute_uuid, attribute=attribute
    )


@router.delete("/attributes/{attribute_uuid}", status_code=status.HTTP_204_NO_CONTENT)
def delete_attribute(
    attribute_uuid: UUID,
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["attributes:delete"]
    ),
):
    attributes_repository.delete_attribute(db=db, attribute_uuid=attribute_uuid)

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/attributes/{attribute_uuid}/tag/{tag}",
    status_code=status.HTTP_201_CREATED,
)
def tag_attribute(
    attribute_uuid: UUID,
    tag: str,
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["attributes:update"]
    ),
):
    attribute = attributes_repository.get_attribute_from_opensearch(attribute_uuid)
    if attribute is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Attribute not found"
        )

    tag = tags_repository.get_or_create_tag_by_name(db, tag_name=tag)

    tags_repository.tag_attribute(db=db, attribute=attribute, tag=tag)

    return Response(status_code=status.HTTP_201_CREATED)


@router.delete(
    "/attributes/{attribute_uuid}/tag/{tag}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def untag_attribute(
    attribute_uuid: UUID,
    tag: str,
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["attributes:update"]
    ),
):
    attribute = attributes_repository.get_attribute_from_opensearch(attribute_uuid)
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
