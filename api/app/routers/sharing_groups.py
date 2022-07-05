from app.auth.auth import get_current_active_user
from app.dependencies import get_db
from app.repositories import sharing_groups as sharing_groups_repository
from app.schemas import sharing_groups as sharing_groups_schemas
from app.schemas import user as user_schemas
from fastapi import APIRouter, Depends, HTTPException, Security, status
from sqlalchemy.orm import Session

router = APIRouter()


@router.get(
    "/sharing_groups/", response_model=list[sharing_groups_schemas.SharingGroup]
)
def get_sharing_groups(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["sharing_groups:read"]
    ),
):
    return sharing_groups_repository.get_sharing_groups(db, skip=skip, limit=limit)


@router.get(
    "/sharing_groups/{sharing_group_id}",
    response_model=sharing_groups_schemas.SharingGroup,
)
def get_sharing_group_by_id(
    sharing_group_id: int,
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["sharing_groups:read"]
    ),
):
    db_sharing_group = sharing_groups_repository.get_sharing_group_by_id(
        db, sharing_group_id=sharing_group_id
    )
    if db_sharing_group is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Sharing Group not found"
        )
    return db_sharing_group


@router.post(
    "/sharing_groups/",
    response_model=sharing_groups_schemas.SharingGroup,
    status_code=status.HTTP_201_CREATED,
)
def create_sharing_group(
    sharing_group: sharing_groups_schemas.SharingGroupCreate,
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["sharing_groups:create"]
    ),
):
    return sharing_groups_repository.create_sharing_group(
        db=db, sharing_group=sharing_group
    )


@router.post(
    "/sharing_groups/{sharing_group_id}/servers",
    response_model=sharing_groups_schemas.SharingGroupServer,
    status_code=status.HTTP_201_CREATED,
)
def add_server_to_sharing_group(
    sharing_group_id: int,
    sharing_group_server: sharing_groups_schemas.SharingGroupServerCreate,
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["sharing_groups:update"]
    ),
):
    sharing_group_server.sharing_group_id = sharing_group_id
    return sharing_groups_repository.add_server_sharing_group(
        db=db, sharing_group_server=sharing_group_server
    )


@router.post(
    "/sharing_groups/{sharing_group_id}/organisations",
    response_model=sharing_groups_schemas.SharingGroupOrganisation,
    status_code=status.HTTP_201_CREATED,
)
def add_organisation_to_sharing_group(
    sharing_group_id: int,
    sharing_group_organisation: sharing_groups_schemas.SharingGroupOrganisationCreate,
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["sharing_groups:update"]
    ),
):
    sharing_group_organisation.sharing_group_id = sharing_group_id
    return sharing_groups_repository.add_organisation_to_sharing_group(
        db=db, sharing_group_organisation=sharing_group_organisation
    )


@router.patch(
    "/sharing_groups/{sharing_group_id}",
    response_model=sharing_groups_schemas.SharingGroup,
)
def update_sharing_group(
    sharing_group_id: int,
    sharing_group: sharing_groups_schemas.SharingGroupUpdate,
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["sharing_groups:update"]
    ),
):
    return sharing_groups_repository.update_sharing_group(
        db=db, sharing_group_id=sharing_group_id, sharing_group=sharing_group
    )


@router.delete(
    "/sharing_groups/{sharing_group_id}", status_code=status.HTTP_204_NO_CONTENT
)
def delete_sharing_group(
    sharing_group_id: int,
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["sharing_groups:delete"]
    ),
):
    return sharing_groups_repository.delete_sharing_group(
        db=db, sharing_group_id=sharing_group_id
    )
