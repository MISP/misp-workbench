import logging

import json

from app.models import hunt as hunt_models
from app.schemas import hunt as hunt_schemas
from app.services.opensearch import get_opensearch_client
from app.services import rulezet
from app.repositories import notifications as notifications_repository
from app.services.redis import get_redis_client
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session
from fastapi_pagination.ext.sqlalchemy import paginate
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

INDEX_MAP = {
    "attributes": "misp-attributes",
    "events": "misp-events",
    "correlations": "misp-attribute-correlations",
}


def get_hunts(db: Session, user_id: int, params: hunt_schemas.HuntQueryParams = None):
    query = select(hunt_models.Hunt).where(hunt_models.Hunt.user_id == user_id)
    if params and params.filter:
        query = query.where(hunt_models.Hunt.name.ilike(f"%{params.filter}%"))
    query = query.order_by(hunt_models.Hunt.created_at.desc())
    return paginate(db, query)


def get_hunt_by_id(db: Session, hunt_id: int, user_id: int) -> hunt_models.Hunt:
    return (
        db.query(hunt_models.Hunt)
        .filter(
            hunt_models.Hunt.id == hunt_id,
            hunt_models.Hunt.user_id == user_id,
        )
        .first()
    )


def create_hunt(db: Session, hunt: hunt_schemas.HuntCreate, user_id: int):
    db_hunt = hunt_models.Hunt(
        **hunt.model_dump(),
        user_id=user_id,
        created_at=datetime.now(timezone.utc),
    )
    db.add(db_hunt)
    db.commit()
    db.refresh(db_hunt)
    return db_hunt


def update_hunt(
    db: Session, hunt_id: int, hunt: hunt_schemas.HuntUpdate, user_id: int
):
    db_hunt = get_hunt_by_id(db, hunt_id, user_id)
    if not db_hunt:
        return None
    for key, value in hunt.model_dump(exclude_unset=True).items():
        setattr(db_hunt, key, value)
    db_hunt.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(db_hunt)
    return db_hunt


def get_hunt_results(hunt_id: int):
    data = get_redis_client().get(f"hunt:results:{hunt_id}")
    if data is None:
        return None
    return json.loads(data)


def get_hunt_history(db: Session, hunt_id: int) -> list[dict]:
    redis = get_redis_client()
    history_key = f"hunt:history:{hunt_id}"
    raw = redis.lrange(history_key, 0, -1)
    if raw:
        return [json.loads(entry) for entry in raw]

    # Cache miss — load from DB, populate cache, return
    rows = (
        db.query(hunt_models.HuntRunHistory)
        .filter(hunt_models.HuntRunHistory.hunt_id == hunt_id)
        .order_by(hunt_models.HuntRunHistory.run_at.asc())
        .limit(90)
        .all()
    )
    entries = [
        {"run_at": row.run_at.isoformat(), "match_count": row.match_count}
        for row in rows
    ]
    if entries:
        redis.rpush(history_key, *[json.dumps(e) for e in entries])
        redis.ltrim(history_key, -90, -1)
    return entries


def delete_hunt(db: Session, hunt_id: int, user_id: int):
    db_hunt = get_hunt_by_id(db, hunt_id, user_id)
    if not db_hunt:
        return None
    db.delete(db_hunt)
    db.commit()
    redis = get_redis_client()
    redis.delete(f"hunt:results:{hunt_id}")
    redis.delete(f"hunt:history:{hunt_id}")
    from app.repositories import tasks as tasks_repository
    tasks_repository.delete_scheduled_tasks_for_hunt(hunt_id)
    return {"status": "success"}


def _persist_hunt_run(
    db: Session,
    db_hunt: hunt_models.Hunt,
    total: int,
    hits: list,
    prev_total: int,
):
    now = datetime.now(timezone.utc)
    db_hunt.last_run_at = now
    db_hunt.last_match_count = total
    db_hunt.updated_at = now
    db.add(hunt_models.HuntRunHistory(hunt_id=db_hunt.id, run_at=now, match_count=total))
    db.commit()
    db.refresh(db_hunt)

    redis = get_redis_client()
    redis.set(
        f"hunt:results:{db_hunt.id}",
        json.dumps({"total": total, "hits": hits}),
    )

    history_key = f"hunt:history:{db_hunt.id}"
    entry = json.dumps({"run_at": now.isoformat(), "match_count": total})
    redis.rpush(history_key, entry)
    redis.ltrim(history_key, -90, -1)

    notifications_repository.create_hunt_notification(db, db_hunt, total, prev_total)


def _run_opensearch_hunt(db: Session, db_hunt: hunt_models.Hunt):
    index = INDEX_MAP.get(db_hunt.index_target, "misp-attributes")
    OpenSearchClient = get_opensearch_client()

    body = {
        "size": 100,
        "query": {"query_string": {"query": db_hunt.query}},
    }

    try:
        response = OpenSearchClient.search(index=index, body=body)
    except Exception as e:
        logger.error("Hunt %s execution failed: %s", db_hunt.id, e)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Search engine error: {e}",
        )

    hits = response["hits"]["hits"]
    total = response["hits"]["total"]["value"]
    hit_sources = [h["_source"] for h in hits]

    _persist_hunt_run(db, db_hunt, total, hit_sources, db_hunt.last_match_count)

    return {
        "hunt": hunt_schemas.Hunt.model_validate(db_hunt),
        "total": total,
        "hits": hit_sources,
    }


def _run_rulezet_hunt(db: Session, db_hunt: hunt_models.Hunt):
    try:
        rules = rulezet.lookup(db_hunt.query)
        if not isinstance(rules, list):
            rules = []
    except Exception as e:
        logger.error("Rulezet hunt %s failed: %s", db_hunt.id, e)
        rules = []

    total = len(rules)

    _persist_hunt_run(db, db_hunt, total, rules, db_hunt.last_match_count)

    return {
        "hunt": hunt_schemas.Hunt.model_validate(db_hunt),
        "total": total,
        "hits": rules,
    }


def _run_hunt(db: Session, db_hunt: hunt_models.Hunt):
    if db_hunt.hunt_type == "rulezet":
        return _run_rulezet_hunt(db, db_hunt)
    return _run_opensearch_hunt(db, db_hunt)


def get_active_correlation_hunts(db: Session) -> list[hunt_models.Hunt]:
    """Return all active hunts that target the correlations index."""
    return (
        db.query(hunt_models.Hunt)
        .filter(
            hunt_models.Hunt.status == "active",
            hunt_models.Hunt.index_target == "correlations",
        )
        .all()
    )


def execute_hunt_system(db: Session, hunt_id: int):
    """Execute a hunt without user ownership check — for scheduled/system calls."""
    db_hunt = db.query(hunt_models.Hunt).filter(hunt_models.Hunt.id == hunt_id).first()
    if not db_hunt:
        return None
    return _run_hunt(db, db_hunt)


def execute_hunt(db: Session, hunt_id: int, user_id: int):
    db_hunt = get_hunt_by_id(db, hunt_id, user_id)
    if not db_hunt:
        return None
    return _run_hunt(db, db_hunt)
