"""Tech Lab — Reactor Scripts router.

Endpoints are mounted under ``/tech-lab/reactor`` so the Tech Lab umbrella
can host other features (visualizers, sandboxes, etc.) under the same prefix.
"""

from typing import Optional

from app.auth.security import get_current_active_user
from app.db.session import get_db
from app.repositories import reactor as reactor_repository
from app.schemas import reactor as reactor_schemas
from app.schemas import user as user_schemas
from app.services.tech_lab.reactor import runner as reactor_runner
from fastapi import APIRouter, Depends, HTTPException, Security, status
from fastapi_pagination import Page
from sqlalchemy.orm import Session

router = APIRouter()


async def _list_params(
    filter: Optional[str] = None,
) -> reactor_schemas.ReactorQueryParams:
    return reactor_schemas.ReactorQueryParams(filter=filter)


@router.get(
    "/tech-lab/reactor/scripts/",
    response_model=Page[reactor_schemas.ReactorScript],
)
async def list_scripts(
    db: Session = Depends(get_db),
    params: reactor_schemas.ReactorQueryParams = Depends(_list_params),
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["reactor:read"]
    ),
):
    return reactor_repository.get_scripts(db, user_id=user.id, params=params)


@router.post(
    "/tech-lab/reactor/scripts/",
    response_model=reactor_schemas.ReactorScript,
    status_code=status.HTTP_201_CREATED,
)
async def create_script(
    payload: reactor_schemas.ReactorScriptCreate,
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["reactor:create"]
    ),
):
    return reactor_repository.create_script(db, payload, user_id=user.id)


@router.get(
    "/tech-lab/reactor/scripts/{script_id}",
    response_model=reactor_schemas.ReactorScript,
)
async def get_script(
    script_id: int,
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["reactor:read"]
    ),
):
    db_script = reactor_repository.get_script_by_id(db, script_id, user_id=user.id)
    if db_script is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Reactor script not found"
        )
    return db_script


@router.patch(
    "/tech-lab/reactor/scripts/{script_id}",
    response_model=reactor_schemas.ReactorScript,
)
async def update_script(
    script_id: int,
    payload: reactor_schemas.ReactorScriptUpdate,
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["reactor:update"]
    ),
):
    db_script = reactor_repository.update_script(db, script_id, payload, user_id=user.id)
    if db_script is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Reactor script not found"
        )
    return db_script


@router.delete(
    "/tech-lab/reactor/scripts/{script_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_script(
    script_id: int,
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["reactor:delete"]
    ),
):
    result = reactor_repository.delete_script(db, script_id, user_id=user.id)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Reactor script not found"
        )


@router.get("/tech-lab/reactor/scripts/{script_id}/source")
async def get_script_source(
    script_id: int,
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["reactor:read"]
    ),
):
    source = reactor_repository.get_script_source(db, script_id, user_id=user.id)
    if source is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Reactor script not found"
        )
    return {"script_id": script_id, "source": source}


@router.get(
    "/tech-lab/reactor/scripts/{script_id}/runs",
    response_model=Page[reactor_schemas.ReactorRun],
)
async def list_runs(
    script_id: int,
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["reactor:read"]
    ),
):
    page = reactor_repository.get_runs(db, script_id, user_id=user.id)
    if page is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Reactor script not found"
        )
    return page


@router.get(
    "/tech-lab/reactor/runs/{run_id}",
    response_model=reactor_schemas.ReactorRun,
)
async def get_run(
    run_id: int,
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["reactor:read"]
    ),
):
    db_run = reactor_repository.get_run(db, run_id, user_id=user.id)
    if db_run is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Reactor run not found"
        )
    return db_run


@router.get(
    "/tech-lab/reactor/runs/{run_id}/log",
    response_model=reactor_schemas.ReactorRunLog,
)
async def get_run_log(
    run_id: int,
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["reactor:read"]
    ),
):
    log = reactor_repository.get_run_log(db, run_id, user_id=user.id)
    if log is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Reactor run not found"
        )
    return reactor_schemas.ReactorRunLog(run_id=run_id, log=log)


@router.get("/tech-lab/reactor/runs/{run_id}/profile")
async def get_run_profile(
    run_id: int,
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["reactor:read"]
    ),
):
    """Return the flame-chart tree for a profiled run.

    The tree is in d3-flame-graph format: ``{name, value, children}`` where
    ``value`` is wall-clock seconds (inclusive of children). 404 when the
    run isn't found or wasn't profiled.
    """
    tree = reactor_repository.get_run_profile(db, run_id, user_id=user.id)
    if tree is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="No profile for this run"
        )
    return {"run_id": run_id, "tree": tree}


@router.post(
    "/tech-lab/reactor/scripts/{script_id}/test",
    response_model=reactor_schemas.ReactorRun,
)
async def test_run(
    script_id: int,
    payload: reactor_schemas.ReactorTestRequest,
    profile: bool = False,
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["reactor:run"]
    ),
):
    """Run the script synchronously against a user-supplied payload.

    Useful while iterating. Runs in the API process, **not** the sandbox
    worker — admins should keep ``reactor:run`` to trusted users for now.

    Pass ``?profile=true`` to attach cProfile around the handler. The
    top-20 functions by cumulative time are appended to the run log under
    a ``=== profile ===`` section, viewable via ``GET /runs/{id}/log``.
    """
    db_script = reactor_repository.get_script_by_id(db, script_id, user_id=user.id)
    if db_script is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Reactor script not found"
        )
    run = reactor_repository.create_run(
        db,
        db_script,
        triggered_by={
            "resource_type": payload.resource_type or "test",
            "action": payload.action or "manual",
            "payload": payload.payload,
        },
    )
    reactor_runner.run_script(db, run.id, profile=profile)
    db.refresh(run)
    return run
