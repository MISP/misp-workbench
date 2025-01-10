from app.auth.auth import get_current_active_user
from app.dependencies import get_db
from app.repositories import taxonomies as taxonomies_repository
from app.schemas import taxonomy as taxonomies_schemas
from app.schemas import user as user_schemas
from fastapi import APIRouter, Depends, HTTPException, Query, Security, status
from fastapi_pagination import Page
from fastapi_pagination.customization import (
    CustomizedPage,
    UseModelConfig,
    UseParamsFields,
)
from sqlalchemy.orm import Session

router = APIRouter()

Page = CustomizedPage[
    Page,
    UseModelConfig(extra="allow"),
    UseParamsFields(size=Query(le=1000, default=20)),
]


@router.get("/taxonomies/", response_model=Page[taxonomies_schemas.Taxonomy])
def get_taxonomies(
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["taxonomies:read"]
    ),
    enabled: bool = Query(None),
    filter: str = Query(None),
):
    return taxonomies_repository.get_taxonomies(db, enabled=enabled, filter=filter)


@router.get("/taxonomies/{taxonomy_id}", response_model=taxonomies_schemas.Taxonomy)
def get_taxonomy_by_id(
    taxonomy_id: int,
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["taxonomies:read"]
    ),
) -> taxonomies_schemas.Taxonomy:
    db_taxonomy = taxonomies_repository.get_taxonomy_by_id(db, taxonomy_id=taxonomy_id)
    if db_taxonomy is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Taxonomy not found"
        )
    return db_taxonomy


@router.post("/taxonomies/update", response_model=list[taxonomies_schemas.Taxonomy])
def update_taxonomies(
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["taxonomies:update"]
    ),
):
    return taxonomies_repository.update_taxonomies(db)


@router.patch("/taxonomies/{taxonomy_id}", response_model=taxonomies_schemas.Taxonomy)
def update_taxonomy(
    taxonomy_id: int,
    taxonomy: taxonomies_schemas.TaxonomyUpdate,
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["taxonomies:update"]
    ),
) -> taxonomies_schemas.Taxonomy:
    return taxonomies_repository.update_taxonomy(
        db=db, taxonomy_id=taxonomy_id, taxonomy=taxonomy
    )
