from app.auth.auth import AVAILABLE_SCOPES
from app.auth.security import get_current_active_user
from app.db.session import get_db
from app.repositories import roles as roles_repository
from app.schemas import role as role_schemas
from app.schemas import user as user_schemas
from fastapi import APIRouter, Depends, HTTPException, Security, status
from sqlalchemy.orm import Session

router = APIRouter()


@router.get("/roles/scopes", response_model=dict[str, str])
def get_available_scopes(
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["roles:read"]
    ),
):
    return AVAILABLE_SCOPES


@router.get("/roles/", response_model=list[role_schemas.Role])
def get_roles(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(get_current_active_user, scopes=["roles:read"]),
):
    return roles_repository.get_roles(db, skip=skip, limit=limit)


@router.get("/roles/{role_id}", response_model=role_schemas.Role)
def get_role(
    role_id: int,
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(get_current_active_user, scopes=["roles:read"]),
):
    db_role = roles_repository.get_role_by_id(db, role_id)
    if db_role is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")
    return db_role


@router.patch("/roles/{role_id}", response_model=role_schemas.Role)
def update_role(
    role_id: int,
    role_update: role_schemas.RoleUpdate,
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["roles:update"]
    ),
):
    db_role = roles_repository.update_role(db, role_id, role_update)
    if db_role is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")
    return db_role


@router.delete("/roles/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_role(
    role_id: int,
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["roles:delete"]
    ),
):
    db_role = roles_repository.delete_role(db, role_id)
    if db_role is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")
