from email.utils import format_datetime, parsedate_to_datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Security, status
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import Response, StreamingResponse
from fastapi_pagination import Page
from sqlalchemy.orm import Session

from app.auth.security import get_current_active_user
from app.db.session import get_db
from app.repositories import exports as exports_repository
from app.schemas import export as export_schemas
from app.schemas import user as user_schemas
from app.services.exports_storage import open_export
from app.worker import tasks

router = APIRouter()

# Content type + filename extension to serve a stored artifact under, by format.
DOWNLOAD_META = {
    "json": ("application/json", "json"),
    "csv": ("text/csv", "csv"),
    "stix": ("application/stix+json", "json"),
    "misp": ("application/json", "json"),
    "ndjson": ("application/x-ndjson", "ndjson"),
    "text": ("text/plain", "txt"),
    "cdb": ("text/plain", "cdb"),
}


def _validators(db_export) -> dict:
    """ETag (the artifact's sha256) and Last-Modified of a stored export."""
    headers = {"Cache-Control": "no-cache"}
    if db_export.checksum:
        headers["ETag"] = f'"{db_export.checksum}"'
    if db_export.finished_at:
        headers["Last-Modified"] = format_datetime(db_export.finished_at, usegmt=True)
    return headers


def _not_modified(request: Request, headers: dict) -> bool:
    if_none_match = request.headers.get("if-none-match")
    if if_none_match:
        tags = {t.strip() for t in if_none_match.split(",")}
        return headers.get("ETag") in tags or "*" in tags
    if_modified_since = request.headers.get("if-modified-since")
    if if_modified_since and "Last-Modified" in headers:
        try:
            return parsedate_to_datetime(headers["Last-Modified"]) <= (
                parsedate_to_datetime(if_modified_since)
            )
        except (TypeError, ValueError):
            return False
    return False


async def _open_artifact(storage_key: str):
    try:
        return await run_in_threadpool(open_export, storage_key)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error fetching export artifact",
        )


def _get_owned_export(db: Session, export_id: int, user_id: int):
    db_export = exports_repository.get_export_by_id(
        db, export_id=export_id, user_id=user_id
    )
    if not db_export:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Export not found"
        )
    return db_export


async def get_export_params(
    filter: Optional[str] = None,
) -> export_schemas.ExportQueryParams:
    return export_schemas.ExportQueryParams(filter=filter)


@router.get("/exports/", response_model=Page[export_schemas.Export])
async def get_exports(
    db: Session = Depends(get_db),
    params: export_schemas.ExportQueryParams = Depends(get_export_params),
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["exports:read"]
    ),
):
    return exports_repository.get_exports(db, user_id=user.id, params=params)


@router.post(
    "/exports/",
    response_model=export_schemas.Export,
    status_code=status.HTTP_201_CREATED,
)
async def create_export(
    export: export_schemas.ExportCreate,
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["exports:create"]
    ),
):
    db_export = exports_repository.create_export(db, export=export, user_id=user.id)
    result = tasks.run_export.delay(db_export.id)
    exports_repository.set_celery_task_id(db, db_export.id, result.id)
    db.refresh(db_export)
    return db_export


@router.post("/exports/{export_id}/run", response_model=export_schemas.Export)
async def run_export_now(
    export_id: int,
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["exports:create"]
    ),
):
    db_export = exports_repository.requeue_export(
        db, export_id=export_id, user_id=user.id
    )
    if db_export is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Export not found"
        )
    result = tasks.run_export.delay(db_export.id)
    exports_repository.set_celery_task_id(db, db_export.id, result.id)
    db.refresh(db_export)
    return db_export


@router.get("/exports/{export_id}", response_model=export_schemas.Export)
async def get_export_by_id(
    export_id: int,
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["exports:read"]
    ),
):
    db_export = exports_repository.get_export_by_id(
        db, export_id=export_id, user_id=user.id
    )
    if not db_export:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Export not found"
        )
    return db_export


@router.patch("/exports/{export_id}/schedule", response_model=export_schemas.Export)
async def update_export_schedule(
    export_id: int,
    payload: export_schemas.ExportScheduleUpdate,
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["exports:create"]
    ),
):
    db_export = exports_repository.update_export_schedule(
        db, export_id=export_id, user_id=user.id, payload=payload
    )
    if db_export is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Export not found"
        )
    return db_export


@router.get("/exports/{export_id}/download")
async def download_export(
    export_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["exports:read"]
    ),
):
    db_export = _get_owned_export(db, export_id, user.id)
    if db_export.status != "completed" or not db_export.storage_key:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Export is not ready for download",
        )

    headers = _validators(db_export)
    if _not_modified(request, headers):
        return Response(status_code=status.HTTP_304_NOT_MODIFIED, headers=headers)

    chunks = await _open_artifact(db_export.storage_key)
    content_type, extension = DOWNLOAD_META.get(
        db_export.format, ("application/octet-stream", "dat")
    )
    filename = f"{db_export.name or f'export-{db_export.id}'}.{extension}"
    headers["Content-Disposition"] = f'attachment; filename="{filename}"'
    return StreamingResponse(chunks, media_type=content_type, headers=headers)


@router.get("/exports/{export_id}/feed")
async def get_export_feed(
    export_id: int,
    request: Request,
    since: Optional[int] = Query(
        None,
        ge=0,
        description=(
            "The X-Feed-Cursor of the last response. Omit for the full feed; "
            "with it, only the deltas written after that cursor."
        ),
    ),
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["exports:read"]
    ),
):
    """Serve an incremental export: the full artifact, or deltas since a cursor.

    Both come from storage, so polling consumers never query OpenSearch; it is
    read once per scheduled run, however many of them there are.
    """
    db_export = _get_owned_export(db, export_id, user.id)
    if not db_export.incremental:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Export is not incremental; use /download",
        )
    if db_export.cursor is None or not db_export.storage_key:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Export has not run yet",
        )

    content_type, _ = DOWNLOAD_META[db_export.format]
    cursor_header = {"X-Feed-Cursor": str(db_export.cursor)}

    if since is None:
        headers = {**_validators(db_export), **cursor_header, "X-Feed-Type": "full"}
        if _not_modified(request, headers):
            return Response(status_code=status.HTTP_304_NOT_MODIFIED, headers=headers)
        chunks = await _open_artifact(db_export.storage_key)
        return StreamingResponse(chunks, media_type=content_type, headers=headers)

    deltas = exports_repository.get_feed_deltas(db, db_export, since)
    if deltas is None:
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail=(
                "since is older than the oldest retained delta; "
                "download the full feed again (omit since)"
            ),
            headers=cursor_header,
        )
    if not deltas:
        return Response(status_code=status.HTTP_304_NOT_MODIFIED, headers=cursor_header)

    # Open every delta before responding, so a missing one is an error status
    # rather than a feed that silently stops short.
    parts = [await _open_artifact(delta.storage_key) for delta in deltas]

    def concatenated():
        try:
            for part in parts:
                yield from part
        finally:
            # Release the handles of parts not reached when a client leaves.
            for part in parts:
                part.close()

    return StreamingResponse(
        concatenated(),
        media_type=content_type,
        headers={
            **cursor_header,
            "X-Feed-Type": "delta",
            "Cache-Control": "no-cache",
        },
    )


@router.delete("/exports/{export_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_export(
    export_id: int,
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["exports:delete"]
    ),
):
    result = exports_repository.delete_export(db, export_id=export_id, user_id=user.id)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Export not found"
        )
