from ..schemas import role as role_schemas
from ..repositories import roles as roles_repository
from ..dependencies import get_db
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

router = APIRouter()


@router.get("/roles/", response_model=list[role_schemas.Role])
def get_roles(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    roles = roles_repository.get_roles(db, skip=skip, limit=limit)
    return roles
