from fastapi import APIRouter, Depends, Security
from sqlalchemy.orm import Session

from ..auth.auth import get_current_active_user
from ..dependencies import get_db
from ..repositories import roles as roles_repository
from ..schemas import role as role_schemas
from ..schemas import user as user_schemas

router = APIRouter()


@router.get("/roles/", response_model=list[role_schemas.Role])
def get_roles(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(get_current_active_user, scopes=["roles:read"]),
):
    roles = roles_repository.get_roles(db, skip=skip, limit=limit)
    return roles
