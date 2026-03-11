import json
from pathlib import Path
import logging

from app.auth.security import get_current_active_user
from app.db.session import get_db
from app.repositories import feeds as feeds_repository
from app.repositories import freetext as freetext_repository
from app.repositories import tasks as tasks_repository
from app.schemas import feed as feed_schemas
from app.schemas import user as user_schemas
from app.worker import tasks
from fastapi import APIRouter, Depends, HTTPException, Security, status
from sqlalchemy.orm import Session

_DEFAULTS_PATH = Path(__file__).parent.parent / "defaults" / "default-feeds.json"

router = APIRouter()


def _to_dict(value) -> dict:
    """Parse a value that may be a dict, a JSON string, or a doubly-encoded JSON string."""
    if not value:
        return {}
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            if isinstance(parsed, dict):
                return parsed
            if isinstance(parsed, str):
                inner = json.loads(parsed)
                if isinstance(inner, dict):
                    return inner
        except (json.JSONDecodeError, ValueError):
            logging.debug("Failed to parse value as JSON or nested JSON in _to_dict; returning empty dict", exc_info=True)
    return {}


@router.get("/feeds/", response_model=list[feed_schemas.Feed])
def get_feeds(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    user: feed_schemas.Feed = Security(get_current_active_user, scopes=["feeds:read"]),
):
    return feeds_repository.get_feeds(db, skip=skip, limit=limit)


@router.get("/feeds/defaults")
def get_default_feeds(
    user: user_schemas.User = Security(get_current_active_user, scopes=["feeds:read"]),
):
    raw = json.loads(_DEFAULTS_PATH.read_text())
    result = []
    for entry in raw:
        feed = entry["Feed"]
        result.append(
            {
                "name": feed["name"],
                "provider": feed["provider"],
                "url": feed["url"],
                "source_format": feed["source_format"],
                "enabled": feed.get("enabled", False),
                "distribution": int(feed.get("distribution", 0)),
                "fixed_event": feed.get("fixed_event", False),
                "delta_merge": feed.get("delta_merge", False),
                "publish": feed.get("publish", False),
                "override_ids": feed.get("override_ids", False),
                "input_source": feed.get("input_source", "network"),
                "delete_local_file": feed.get("delete_local_file", False),
                "lookup_visible": feed.get("lookup_visible", False),
                "rules": _to_dict(feed.get("rules")),
                "settings": _to_dict(feed.get("settings")),
            }
        )
    return result


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


@router.get("/feeds/{feed_id}/explore")
def explore_misp_feed(
    feed_id: int,
    page: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["feeds:read"]
    ),
):
    return feeds_repository.explore_misp_feed(db, feed_id, page=page, limit=limit)


@router.get("/feeds/{feed_id}/explore/{event_uuid}")
def explore_misp_feed_event(
    feed_id: int,
    event_uuid: str,
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["feeds:read"]
    ),
):
    return feeds_repository.explore_misp_feed_event(db, feed_id, event_uuid)


@router.post("/feeds/{feed_id}/explore/{event_uuid}/fetch")
def fetch_single_feed_event(
    feed_id: int,
    event_uuid: str,
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["feeds:fetch"]
    ),
):
    return feeds_repository.fetch_single_feed_event(db, feed_id, event_uuid, user)


@router.post("/feeds/misp/test-connection")
def test_feed_connection(
    feed: feed_schemas.FeedCreate,
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["feeds:test-connection"]
    ),
):
    return feeds_repository.test_misp_feed_connection(feed=feed)


@router.post("/feeds/csv/preview")
def preview_csv_feed(
    settings: dict = None,
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["feeds:preview-csv"]
    ),
):
    return feeds_repository.preview_csv_feed(settings=settings)

@router.post("/feeds/freetext/preview")
def preview_freetext_feed(
    settings: dict = None,
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["feeds:preview-csv"]
    ),
):
    return freetext_repository.preview_freetext_feed(settings=settings)


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
    tasks_repository.delete_scheduled_tasks_for_feed(feed_id)
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
