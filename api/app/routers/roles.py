from app.auth.security import get_current_active_user
from app.db.session import get_db
from app.repositories import roles as roles_repository
from app.schemas import role as role_schemas
from app.schemas import user as user_schemas
from fastapi import APIRouter, Depends, Security
from sqlalchemy.orm import Session

router = APIRouter()


@router.get("/roles/", response_model=list[role_schemas.Role])
def get_roles(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(get_current_active_user, scopes=["roles:read"]),
):
    return roles_repository.get_roles(db, skip=skip, limit=limit)
