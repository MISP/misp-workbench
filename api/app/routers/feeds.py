from app.auth.auth import get_current_active_user
from app.dependencies import get_db
from app.repositories import feeds as feeds_repository
from app.schemas import feed as feed_schemas
from app.schemas import user as user_schemas
from fastapi import APIRouter, Depends, Security, status
from sqlalchemy.orm import Session

router = APIRouter()


@router.get("/feeds/", response_model=list[feed_schemas.Feed])
def get_users(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    user: feed_schemas.Feed = Security(get_current_active_user, scopes=["feeds:read"]),
):
    return feeds_repository.get_feeds(db, skip=skip, limit=limit)


@router.post(
    "/feeds/",
    response_model=feed_schemas.Feed,
    status_code=status.HTTP_201_CREATED,
)
def create_server(
    feed: feed_schemas.FeedCreate,
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["feeds:create"]
    ),
):
    return feeds_repository.create_feed(db=db, feed=feed)
