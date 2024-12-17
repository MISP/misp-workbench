from app.auth.auth import get_current_active_user
from app.dependencies import get_db
from app.repositories import galaxies as galaxies_repository
from app.schemas import galaxy as galaxies_schemas
from app.schemas import user as user_schemas
from fastapi import APIRouter, Depends, HTTPException, Query, Security, status
from fastapi_pagination import Page
from fastapi_pagination.customization import CustomizedPage, UseModelConfig
from sqlalchemy.orm import Session

router = APIRouter()

Page = CustomizedPage[
    Page,
    UseModelConfig(extra="allow"),
]


@router.get("/galaxies/", response_model=Page[galaxies_schemas.Galaxy])
def get_galaxies(
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["galaxies:read"]
    ),
    filter: str = Query(None),
):
    return galaxies_repository.get_galaxies(db, filter=filter)


@router.get("/galaxies/{galaxy_id}", response_model=galaxies_schemas.Galaxy)
def get_galaxy_by_id(
    galaxy_id: int,
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["galaxies:read"]
    ),
) -> galaxies_schemas.Galaxy:
    db_galaxy = galaxies_repository.get_galaxy_by_id(db, galaxy_id=galaxy_id)
    if db_galaxy is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Galaxy not found"
        )
    return db_galaxy


@router.post("/galaxies/update", response_model=list[galaxies_schemas.Galaxy])
def update_galaxies(
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["galaxies:update"]
    ),
):
    return galaxies_repository.update_galaxies(db, user=user)


@router.patch("/galaxies/{galaxy_id}", response_model=galaxies_schemas.Galaxy)
def update_galaxy(
    galaxy_id: int,
    galaxy: galaxies_schemas.GalaxyUpdate,
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["galaxies:update"]
    ),
) -> galaxies_schemas.Galaxy:
    return galaxies_repository.update_galaxy(db=db, galaxy_id=galaxy_id, galaxy=galaxy)
