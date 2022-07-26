from app.auth.auth import get_current_active_user
from app.dependencies import get_db
from app.repositories import tags as tags_repository
from app.schemas import tag as tag_schemas
from app.schemas import user as user_schemas
from fastapi import APIRouter, Depends, Security
from sqlalchemy.orm import Session

router = APIRouter()


@router.get("/tags/", response_model=list[tag_schemas.Tag])
def get_tags(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(get_current_active_user, scopes=["tags:read"]),
):
    return tags_repository.get_tags(db, skip=skip, limit=limit)
