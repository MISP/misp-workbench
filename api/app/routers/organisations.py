from app.auth.auth import get_current_active_user
from app.dependencies import get_db
from app.repositories import organisations as organisations_repository
from app.schemas import organisations as organisation_schemas
from app.schemas import user as user_schemas
from fastapi import APIRouter, Depends, HTTPException, Security, status
from sqlalchemy.orm import Session

router = APIRouter()


@router.get("/organisations/", response_model=list[organisation_schemas.Organisation])
def get_organisations(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["organisations:read"]
    ),
):
    return organisations_repository.get_organisations(db, skip=skip, limit=limit)


@router.get(
    "/organisations/{organisation_id}", response_model=organisation_schemas.Organisation
)
def get_organisation_by_id(
    organisation_id: int,
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["organisations:read"]
    ),
):
    db_organisation = organisations_repository.get_organisation_by_id(
        db, organisation_id=organisation_id
    )
    if db_organisation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Organisation not found"
        )
    return db_organisation


@router.post(
    "/organisations/", response_model=organisation_schemas.Organisation, status_code=201
)
def create_organisation(
    organisation: organisation_schemas.OrganisationCreate,
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["organisations:create"]
    ),
):
    return organisations_repository.create_organisation(
        db=db, organisation=organisation
    )
