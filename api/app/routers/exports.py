import io
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Security, status
from fastapi.responses import StreamingResponse
from fastapi_pagination import Page
from sqlalchemy.orm import Session

from app.auth.security import get_current_active_user
from app.db.session import get_db
from app.repositories import exports as exports_repository
from app.schemas import export as export_schemas
from app.schemas import user as user_schemas
from app.services.exports_storage import get_export
from app.worker import tasks

router = APIRouter()

# Content type + filename extension to serve a stored artifact under, by format.
DOWNLOAD_META = {
    "json": ("application/json", "json"),
    "csv": ("text/csv", "csv"),
    "stix": ("application/stix+json", "json"),
}


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


@router.get("/exports/{export_id}/download")
async def download_export(
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
    if db_export.status != "completed" or not db_export.storage_key:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Export is not ready for download",
        )

    try:
        content = get_export(db_export.storage_key)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error fetching export artifact",
        )

    content_type, extension = DOWNLOAD_META.get(
        db_export.format, ("application/octet-stream", "dat")
    )
    filename = f"{db_export.name or f'export-{db_export.id}'}.{extension}"
    return StreamingResponse(
        io.BytesIO(content),
        media_type=content_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
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
