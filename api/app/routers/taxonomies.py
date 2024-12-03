from app.auth.auth import get_current_active_user
from app.dependencies import get_db
from app.repositories import taxonomies as taxonomies_repository
from app.schemas import taxonomy as taxonomies_schemas
from app.schemas import user as user_schemas
from fastapi import APIRouter, Depends, Security
from sqlalchemy.orm import Session

router = APIRouter()


@router.get("/taxonomies/", response_model=list[taxonomies_schemas.Taxonomy])
def get_taxonomies(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["taxonomies:read"]
    ),
):
    return taxonomies_repository.get_taxonomies(db, skip=skip, limit=limit)


@router.post("/taxonomies/update", response_model=list[taxonomies_schemas.Taxonomy])
def update_taxonomies(
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["taxonomies:update"]
    ),
):
    return taxonomies_repository.update_taxonomies(db)
