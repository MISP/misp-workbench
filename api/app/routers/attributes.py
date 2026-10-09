from typing import Optional
from uuid import UUID
from app.auth.security import get_current_active_user
from app.db.session import get_db
from app.repositories import attributes as attributes_repository
from app.repositories import events as events_repository
from app.repositories import stream_exports as stream_exports_repository
from app.repositories import tags as tags_repository
from app.schemas import attribute as attribute_schemas
from app.schemas import user as user_schemas
from app.services.runtime_settings import RuntimeSettings
from app.services.runtime_settings_provider import get_runtime_settings
from app.worker import tasks
from fastapi import APIRouter, Depends, HTTPException, Request, Response, Security, status, Query
from fastapi.concurrency import run_in_threadpool
from fastapi_pagination import Page, Params
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
    include_deleted: bool = Query(False),
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["attributes:read"]
    ),
):

    from_value = (page - 1) * size

    return attributes_repository.search_attributes(
        query, page, from_value, size, sort_by, sort_order,
        include_deleted=include_deleted,
    )

@router.get("/attributes/histogram")
async def get_attributes_histogram(
    query: str = Query(..., min_length=0),
    interval: Optional[str] = Query("1d", pattern="^(1d|1w|1M)$"),
    include_deleted: bool = Query(False),
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["attributes:read"]
    ),
):
    return attributes_repository.search_attributes_histogram(query, interval, include_deleted=include_deleted)


@router.get("/attributes/export")
async def export_attributes(
    request: Request,
    query: str = Query("", min_length=0),
    format: Optional[str] = Query("json"),
    since: Optional[str] = Query(
        None,
        description=(
            "Only attributes written since this time (epoch seconds, ISO date or "
            "relative age like 7d), soft-deleted ones included as tombstones. "
            "Use the X-Export-Timestamp header of the previous export."
        ),
    ),
    include_deleted: bool = Query(False),
    enforce_warninglist: Optional[bool] = Query(
        None,
        description=(
            "Leave out attributes on an enabled warninglist (full exports only). "
            "Defaults to the warninglists.enforce_on_outputs runtime setting."
        ),
    ),
    runtime_settings: RuntimeSettings = Depends(get_runtime_settings),
    user: user_schemas.User = Security(get_current_active_user, scopes=["attributes:read"]),
):
    if enforce_warninglist is None:
        enforce_warninglist = bool(
            await run_in_threadpool(
                runtime_settings.get_value, "warninglists.enforce_on_outputs", True
            )
        )
    try:
        export = await run_in_threadpool(
            stream_exports_repository.prepare_attribute_export,
            query,
            format,
            since,
            include_deleted,
            enforce_warninglist,
        )
    except stream_exports_repository.RestSearchError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error))

    max_concurrent = await run_in_threadpool(
        runtime_settings.get_value, "exports.max_concurrent_per_user", 3
    )
    return await stream_exports_repository.to_response(
        export, request, user_id=user.id, max_concurrent=max_concurrent
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
    try:
        created = attributes_repository.create_attribute(db=db, attribute=attribute)
    except attributes_repository.AttributeNotIndexedError as error:
        # A servo dropped it. 201 would be a lie -- the attribute is not
        # searchable and nothing downstream ran for it.
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)
        )
    events_repository.mark_event_modified(event.uuid)
    return created


@router.patch("/attributes/{attribute_uuid}", response_model=attribute_schemas.Attribute)
def update_attribute(
    attribute_uuid: UUID,
    attribute: attribute_schemas.AttributeUpdate,
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["attributes:update"]
    ),
) -> attribute_schemas.Attribute:
    updated = attributes_repository.update_attribute(
        db=db, attribute_uuid=attribute_uuid, attribute=attribute
    )
    events_repository.mark_event_modified(updated.event_uuid)
    return updated


@router.delete("/attributes/{attribute_uuid}", status_code=status.HTTP_204_NO_CONTENT)
def delete_attribute(
    attribute_uuid: UUID,
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["attributes:delete"]
    ),
):
    attribute = attributes_repository.get_attribute_from_opensearch(attribute_uuid)
    attributes_repository.delete_attribute(db=db, attribute_uuid=attribute_uuid)
    events_repository.mark_event_modified(attribute.event_uuid)

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
    events_repository.mark_event_modified(attribute.event_uuid)

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
    events_repository.mark_event_modified(attribute.event_uuid)

    return Response(status_code=status.HTTP_204_NO_CONTENT)
