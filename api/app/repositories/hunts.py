import logging

from app.models import hunt as hunt_models
from app.schemas import hunt as hunt_schemas
from app.services.opensearch import get_opensearch_client
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session
from fastapi_pagination.ext.sqlalchemy import paginate
from datetime import datetime

logger = logging.getLogger(__name__)

INDEX_MAP = {
    "attributes": "misp-attributes",
    "events": "misp-events",
}


def get_hunts(db: Session, user_id: int, params: dict = {}):
    query = select(hunt_models.Hunt).where(hunt_models.Hunt.user_id == user_id)
    if params.get("filter"):
        query = query.where(hunt_models.Hunt.name.ilike(f"%{params['filter']}%"))
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
        created_at=datetime.now(),
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
    db_hunt.updated_at = datetime.now()
    db.commit()
    db.refresh(db_hunt)
    return db_hunt


def delete_hunt(db: Session, hunt_id: int, user_id: int):
    db_hunt = get_hunt_by_id(db, hunt_id, user_id)
    if not db_hunt:
        return None
    db.delete(db_hunt)
    db.commit()
    return {"status": "success"}


def execute_hunt(db: Session, hunt_id: int, user_id: int):
    db_hunt = get_hunt_by_id(db, hunt_id, user_id)
    if not db_hunt:
        return None

    index = INDEX_MAP.get(db_hunt.index_target, "misp-attributes")
    OpenSearchClient = get_opensearch_client()

    body = {
        "size": 100,
        "query": {
            "query_string": {
                "query": db_hunt.query,
            }
        },
    }

    try:
        response = OpenSearchClient.search(index=index, body=body)
    except Exception as e:
        logger.error("Hunt %s execution failed: %s", hunt_id, e)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Search engine error: {e}",
        )

    hits = response["hits"]["hits"]
    total = response["hits"]["total"]["value"]

    db_hunt.last_run_at = datetime.now()
    db_hunt.last_match_count = total
    db_hunt.updated_at = datetime.now()
    db.commit()
    db.refresh(db_hunt)

    return {
        "hunt": hunt_schemas.Hunt.model_validate(db_hunt),
        "total": total,
        "hits": [h["_source"] for h in hits],
    }
