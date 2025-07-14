from app.auth.security import get_current_active_user
from app.db.session import get_db
from app.repositories import tags as tags_repository
from app.schemas import tag as tag_schemas
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


@router.get("/tags/", response_model=Page[tag_schemas.Tag])
def get_tags(
    db: Session = Depends(get_db),
    hidden: bool = Query(None),
    filter: str = Query(None),
    user: user_schemas.User = Security(get_current_active_user, scopes=["tags:read"]),
):
    return tags_repository.get_tags(db, hidden=hidden, filter=filter)


@router.get("/tags/{tag_id}", response_model=tag_schemas.Tag)
def get_tag_by_id(
    tag_id: int,
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(get_current_active_user, scopes=["tags:read"]),
):
    db_tag = tags_repository.get_tag_by_id(db, tag_id=tag_id)
    if db_tag is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Tag not found"
        )
    return db_tag


@router.post(
    "/tags/",
    response_model=tag_schemas.Tag,
    status_code=status.HTTP_201_CREATED,
)
def create_tag(
    tag: tag_schemas.TagCreate,
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(get_current_active_user, scopes=["tags:create"]),
):
    return tags_repository.create_tag(db=db, tag=tag)


@router.patch("/tags/{tag_id}", response_model=tag_schemas.Tag)
def update_tag(
    tag_id: int,
    tag: tag_schemas.TagUpdate,
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(get_current_active_user, scopes=["tags:update"]),
):
    return tags_repository.update_tag(db=db, tag_id=tag_id, tag=tag)


@router.delete("/tags/{tag_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_tag(
    tag_id: int,
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(get_current_active_user, scopes=["tags:delete"]),
):
    return tags_repository.delete_tag(db=db, tag_id=tag_id)
