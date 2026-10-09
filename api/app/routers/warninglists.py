from fastapi import APIRouter, Depends, HTTPException, Security, status
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.orm import Session

from app.auth.security import get_current_active_user
from app.db.session import get_db
from app.repositories import warninglists as warninglists_repository
from app.schemas import task as task_schemas
from app.schemas import user as user_schemas
from app.schemas import warninglist as warninglist_schemas
from app.worker import tasks

router = APIRouter()


@router.get("/warninglists/", response_model=list[warninglist_schemas.Warninglist])
def get_warninglists(
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["warninglists:read"]
    ),
):
    return warninglists_repository.get_warninglists(db)


@router.post(
    "/warninglists/check", response_model=warninglist_schemas.WarninglistCheckResponse
)
async def check_values(
    request: warninglist_schemas.WarninglistCheckRequest,
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["warninglists:read"]
    ),
):
    """Which enabled warninglists each value hits."""
    results = await run_in_threadpool(
        warninglists_repository.check_values, db, request.values, request.type
    )
    return {"hits": {value: hits for value, hits in results.items() if hits}}


@router.post("/warninglists/update", response_model=task_schemas.Task)
def update_warninglists(
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["warninglists:update"]
    ),
):
    """Load new and updated lists from the submodule, then re-flag attributes."""
    task = tasks.load_warninglists.delay()
    return task_schemas.Task(
        task_id=task.id,
        status=task.status,
        message="load_warninglists task has been queued",
    )


@router.patch(
    "/warninglists/{warninglist_id}", response_model=warninglist_schemas.Warninglist
)
def update_warninglist(
    warninglist_id: int,
    payload: warninglist_schemas.WarninglistUpdate,
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["warninglists:update"]
    ),
):
    """Enable or disable a list; attributes are re-flagged in the background."""
    db_list = warninglists_repository.get_warninglist(db, warninglist_id)
    if db_list is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Warninglist not found"
        )
    changed = db_list.enabled != payload.enabled
    db_list = warninglists_repository.set_enabled(db, db_list, payload.enabled)
    if changed:
        tasks.evaluate_all_warninglist_hits.delay()
    return db_list
