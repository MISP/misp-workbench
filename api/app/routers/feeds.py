from app.auth.security import get_current_active_user
from app.db.session import get_db
from app.repositories import feeds as feeds_repository
from app.schemas import feed as feed_schemas
from app.schemas import user as user_schemas
from app.worker import tasks
from fastapi import APIRouter, Depends, HTTPException, Security, status
from sqlalchemy.orm import Session

router = APIRouter()


@router.get("/feeds/", response_model=list[feed_schemas.Feed])
def get_feeds(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    user: feed_schemas.Feed = Security(get_current_active_user, scopes=["feeds:read"]),
):
    return feeds_repository.get_feeds(db, skip=skip, limit=limit)


@router.get("/feeds/{feed_id}", response_model=feed_schemas.Feed)
def get_feed_by_id(
    feed_id: int,
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(get_current_active_user, scopes=["feeds:read"]),
):
    db_feed = feeds_repository.get_feed_by_id(db, feed_id=feed_id)
    if db_feed is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Feed not found"
        )
    return db_feed


@router.post(
    "/feeds/",
    response_model=feed_schemas.Feed,
    status_code=status.HTTP_201_CREATED,
)
def create_feed(
    feed: feed_schemas.FeedCreate,
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["feeds:create"]
    ),
):
    return feeds_repository.create_feed(db=db, feed=feed)

@router.post("/feeds/test-connection")
def test_feed_connection(
    feed: feed_schemas.FeedCreate,
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(get_current_active_user, scopes=["feeds:test-connection"]),
):
    return feeds_repository.test_feed_connection(db=db, feed=feed)

@router.get("/feeds/csv/preview")
def preview_csv_feed(
    url: str,
    mode: str = "network",
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(get_current_active_user, scopes=["feeds:preview-csv"]),
):
    return feeds_repository.preview_csv_feed(db=db, url=url, mode=mode)

@router.patch("/feeds/{feed_id}", response_model=feed_schemas.Feed)
def update_feed(
    feed_id: int,
    feed: feed_schemas.FeedUpdate,
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["feeds:update"]
    ),
) -> feed_schemas.Feed:
    return feeds_repository.update_feed(db=db, feed_id=feed_id, feed=feed)


@router.delete("/feeds/{feed_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_feed(
    feed_id: int,
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["feeds:delete"]
    ),
):
    return feeds_repository.delete_feed(db=db, feed_id=feed_id)


@router.post("/feeds/{feed_id}/fetch")
def fetch_feed(
    feed_id: int,
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(get_current_active_user, scopes=["feeds:fetch"]),
):
    db_feed = feeds_repository.get_feed_by_id(db, feed_id=feed_id)
    if db_feed is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Feed not found"
        )

    result = tasks.fetch_feed.delay(feed_id, user.id)
    return {"task": {"id": result.id, "name": "fetch_feed", "status": result.status}}
