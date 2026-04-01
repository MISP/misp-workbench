from typing import Optional, List

from app.auth.security import get_current_active_user
from app.db.session import get_db
from app.repositories import hunts as hunts_repository
from app.schemas import hunt as hunt_schemas
from app.schemas import user as user_schemas
from fastapi import APIRouter, Depends, HTTPException, Security, status
from sqlalchemy.orm import Session
from fastapi_pagination import Page

router = APIRouter()


async def get_hunt_params(filter: Optional[str] = None) -> hunt_schemas.HuntQueryParams:
    return hunt_schemas.HuntQueryParams(filter=filter)


@router.get("/hunts/", response_model=Page[hunt_schemas.Hunt])
async def get_hunts(
    db: Session = Depends(get_db),
    params: hunt_schemas.HuntQueryParams = Depends(get_hunt_params),
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["hunts:read"]
    ),
):
    return hunts_repository.get_hunts(db, user_id=user.id, params=params)


@router.post(
    "/hunts/",
    response_model=hunt_schemas.Hunt,
    status_code=status.HTTP_201_CREATED,
)
async def create_hunt(
    hunt: hunt_schemas.HuntCreate,
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["hunts:create"]
    ),
):
    return hunts_repository.create_hunt(db, hunt=hunt, user_id=user.id)


@router.get("/hunts/{hunt_id}", response_model=hunt_schemas.Hunt)
async def get_hunt(
    hunt_id: int,
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["hunts:read"]
    ),
):
    db_hunt = hunts_repository.get_hunt_by_id(db, hunt_id=hunt_id, user_id=user.id)
    if not db_hunt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Hunt not found"
        )
    return db_hunt


@router.patch("/hunts/{hunt_id}", response_model=hunt_schemas.Hunt)
async def update_hunt(
    hunt_id: int,
    hunt: hunt_schemas.HuntUpdate,
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["hunts:update"]
    ),
):
    db_hunt = hunts_repository.update_hunt(
        db, hunt_id=hunt_id, hunt=hunt, user_id=user.id
    )
    if not db_hunt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Hunt not found"
        )
    return db_hunt


@router.delete("/hunts/{hunt_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_hunt(
    hunt_id: int,
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["hunts:delete"]
    ),
):
    result = hunts_repository.delete_hunt(db, hunt_id=hunt_id, user_id=user.id)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Hunt not found"
        )


@router.get("/hunts/{hunt_id}/results", response_model=hunt_schemas.HuntResults)
async def get_hunt_results(
    hunt_id: int,
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["hunts:read"]
    ),
) -> hunt_schemas.HuntResults:
    db_hunt = hunts_repository.get_hunt_by_id(db, hunt_id=hunt_id, user_id=user.id)
    if not db_hunt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Hunt not found"
        )
    results = hunts_repository.get_hunt_results(hunt_id)
    if results is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="No results available yet"
        )
    return results


@router.get("/hunts/{hunt_id}/history", response_model=List[hunt_schemas.HuntRunHistoryEntry])
async def get_hunt_history(
    hunt_id: int,
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["hunts:read"]
    ),
):
    db_hunt = hunts_repository.get_hunt_by_id(db, hunt_id=hunt_id, user_id=user.id)
    if not db_hunt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Hunt not found"
        )
    return hunts_repository.get_hunt_history(db, hunt_id)


@router.delete("/hunts/{hunt_id}/history", status_code=status.HTTP_204_NO_CONTENT)
async def delete_hunt_history(
    hunt_id: int,
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["hunts:delete"]
    ),
):
    db_hunt = hunts_repository.get_hunt_by_id(db, hunt_id=hunt_id, user_id=user.id)
    if not db_hunt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Hunt not found"
        )
    hunts_repository.delete_hunt_history(db, hunt_id)


@router.post("/hunts/{hunt_id}/run", response_model=hunt_schemas.HuntRunResult)
async def run_hunt(
    hunt_id: int,
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["hunts:run"]
    ),
) -> hunt_schemas.HuntRunResult:
    result = hunts_repository.execute_hunt(db, hunt_id=hunt_id, user_id=user.id)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Hunt not found"
        )
    return result
