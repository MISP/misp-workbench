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
    "/organisations/",
    response_model=organisation_schemas.Organisation,
    status_code=status.HTTP_201_CREATED,
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


@router.patch(
    "/organisations/{organisation_id}", response_model=organisation_schemas.Organisation
)
def update_organisation(
    organisation_id: int,
    organisation: organisation_schemas.OrganisationUpdate,
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["organisations:update"]
    ),
):
    return organisations_repository.update_organisation(
        db=db, organisation_id=organisation_id, organisation=organisation
    )


@router.delete(
    "/organisations/{organisation_id}", status_code=status.HTTP_204_NO_CONTENT
)
def delete_organisation(
    organisation_id: int,
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["organisations:delete"]
    ),
):
    return organisations_repository.delete_organisation(
        db=db, organisation_id=organisation_id
    )
