"""Organisations' own warninglists (see ``app.repositories.local_warninglists``).

Each organisation sees and manages its own lists only; admins see them all.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Security, status
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import StreamingResponse
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth.security import get_current_active_user
from app.db.session import get_db
from app.repositories import local_warninglists as lists_repository
from app.schemas import local_warninglist as schemas
from app.schemas import user as user_schemas
from app.services import audit

router = APIRouter()

READ = ["warninglists:read"]
MANAGE = ["warninglists:read", "local_warninglists:manage"]


def _get(db: Session, user, list_id: int):
    try:
        return lists_repository.get_list(db, user, list_id)
    except lists_repository.NotVisible:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Warninglist not found")


def _audit(db, request, user, action: str, db_list, **metadata) -> None:
    audit.record(
        db,
        action=f"local_warninglist.{action}",
        resource_type="warninglist",
        resource_id=db_list.id,
        actor_user_id=user.id,
        request=request,
        metadata={"name": db_list.name, "org_id": db_list.org_id, **metadata},
    )
    db.commit()


def _invalid(error: Exception) -> HTTPException:
    return HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(error))


@router.get("/local-warninglists", response_model=list[schemas.LocalWarninglist])
def list_lists(
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(get_current_active_user, scopes=READ),
):
    """Your organisation's lists (every organisation's, for admins)."""
    return lists_repository.visible(db, user)


@router.post(
    "/local-warninglists",
    response_model=schemas.LocalWarninglist,
    status_code=status.HTTP_201_CREATED,
)
def create_list(
    payload: schemas.LocalWarninglistCreate,
    request: Request,
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(get_current_active_user, scopes=MANAGE),
):
    org_id = user.org_id
    if payload.org_id is not None and payload.org_id != user.org_id:
        if not lists_repository.sees_all(user):
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                "Only admins keep lists for another organisation",
            )
        org_id = payload.org_id
    try:
        db_list = lists_repository.create_list(
            db, org_id, payload.name, payload.description, payload.source_url
        )
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT, f"Your organisation has a list {payload.name!r}"
        )
    except lists_repository.InvalidEntry as error:
        raise _invalid(error)
    _audit(db, request, user, "created", db_list)
    return db_list


@router.get("/local-warninglists/{list_id}", response_model=schemas.LocalWarninglist)
def get_list(
    list_id: int,
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(get_current_active_user, scopes=READ),
):
    return _get(db, user, list_id)


@router.patch("/local-warninglists/{list_id}", response_model=schemas.LocalWarninglist)
def update_list(
    list_id: int,
    payload: schemas.LocalWarninglistUpdate,
    request: Request,
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(get_current_active_user, scopes=MANAGE),
):
    db_list = _get(db, user, list_id)
    patch = payload.model_dump(exclude_unset=True)
    try:
        db_list = lists_repository.update_list(db, db_list, patch)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT, f"Your organisation has a list {payload.name!r}"
        )
    except lists_repository.InvalidEntry as error:
        raise _invalid(error)
    _audit(db, request, user, "updated", db_list, changed=sorted(patch))
    return db_list


@router.delete("/local-warninglists/{list_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_list(
    list_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(get_current_active_user, scopes=MANAGE),
):
    from app.repositories import detection_profiles

    db_list = _get(db, user, list_id)
    used_by = [
        p.name
        for p in detection_profiles.get_profiles(db)
        if list_id in ((p.rules or {}).get("exclude_lists") or [])
    ]
    if used_by:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Attached to the profiles {', '.join(map(repr, used_by))}; "
            "detach it first",
        )
    _audit(db, request, user, "deleted", db_list)
    lists_repository.delete_list(db, db_list)


@router.get("/local-warninglists/{list_id}/entries", response_model=schemas.EntryPage)
def list_entries(
    list_id: int,
    q: Optional[str] = Query(None, description="Part of the entry"),
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(get_current_active_user, scopes=READ),
):
    return lists_repository.entries(db, _get(db, user, list_id), q, page, size)


@router.post(
    "/local-warninglists/{list_id}/entries", response_model=schemas.EntriesChanged
)
def add_entries(
    list_id: int,
    payload: schemas.EntriesRequest,
    request: Request,
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(get_current_active_user, scopes=MANAGE),
):
    """Add entries (or update the comment and expiry of ones there).
    Attributes are flagged again in the background."""
    db_list = _get(db, user, list_id)
    try:
        changed = lists_repository.add_entries(
            db, db_list, [e.model_dump() for e in payload.entries], user.id
        )
    except lists_repository.InvalidEntry as error:
        db.rollback()
        raise _invalid(error)
    _audit(db, request, user, "entries_added", db_list, **changed)
    return changed


@router.post(
    "/local-warninglists/{list_id}/entries/delete",
    response_model=schemas.EntriesChanged,
)
def delete_entries(
    list_id: int,
    payload: schemas.EntryIds,
    request: Request,
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(get_current_active_user, scopes=MANAGE),
):
    db_list = _get(db, user, list_id)
    removed = lists_repository.delete_entries(db, db_list, payload.ids)
    _audit(db, request, user, "entries_removed", db_list, removed=removed)
    return {"removed": removed}


@router.post(
    "/local-warninglists/{list_id}/import", response_model=schemas.EntriesChanged
)
def import_entries(
    list_id: int,
    payload: schemas.ImportRequest,
    request: Request,
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(get_current_active_user, scopes=MANAGE),
):
    """A plain list, one entry per line (``entry  # comment``)."""
    db_list = _get(db, user, list_id)
    try:
        changed = lists_repository.add_entries(
            db,
            db_list,
            lists_repository.parse_lines(payload.text),
            user.id,
            origin="import",
            replace=payload.replace,
        )
    except lists_repository.InvalidEntry as error:
        db.rollback()
        raise _invalid(error)
    _audit(db, request, user, "imported", db_list, **changed)
    return changed


@router.get("/local-warninglists/{list_id}/export")
def export_entries(
    list_id: int,
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(get_current_active_user, scopes=READ),
):
    """The list as plain text, one entry per line: what import reads."""
    db_list = _get(db, user, list_id)
    return StreamingResponse(
        lists_repository.export_lines(db, db_list),
        media_type="text/plain",
        headers={
            "Content-Disposition": f'attachment; filename="warninglist-{db_list.id}.txt"'
        },
    )


@router.post(
    "/local-warninglists/{list_id}/sync", response_model=schemas.LocalWarninglist
)
async def sync_list(
    list_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(get_current_active_user, scopes=MANAGE),
):
    """Sync the entries from the list's source URL now."""
    db_list = _get(db, user, list_id)
    if not db_list.source_url:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "The list has no source URL")
    await run_in_threadpool(lists_repository.sync, db, db_list)
    _audit(db, request, user, "synced", db_list, error=db_list.sync_error)
    return db_list


@router.post("/local-warninglists/hits", response_model=schemas.HitsResponse)
def hits(
    payload: schemas.HitsRequest,
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(get_current_active_user, scopes=READ),
):
    """Which of your organisation's lists each indicator is on (others'
    lists are never told)."""
    found = lists_repository.lists_of(
        payload.indicators, lists_repository.visible_ids(db, user)
    )
    return {"hits": {i: ids for i, ids in found.items() if ids}}


@router.post("/local-warninglists/explain", response_model=schemas.ExplainResponse)
async def explain(
    payload: schemas.ExplainRequest,
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(get_current_active_user, scopes=READ),
):
    """Which entries of your organisation's lists each value matches."""
    matches = await run_in_threadpool(
        lists_repository.explain, db, user, payload.values, payload.type
    )
    return {"matches": matches}
