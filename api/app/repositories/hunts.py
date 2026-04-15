import logging

import json

import re

from app.models import hunt as hunt_models
from app.models import galaxy as galaxy_models
from app.schemas import hunt as hunt_schemas
from app.services.opensearch import get_opensearch_client
from app.services import rulezet
from app.services import vulnerability_lookup
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


def update_hunt(db: Session, hunt_id: int, hunt: hunt_schemas.HuntUpdate, user_id: int):
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


def delete_hunt_history(db: Session, hunt_id: int):
    db.query(hunt_models.HuntRunHistory).filter(
        hunt_models.HuntRunHistory.hunt_id == hunt_id
    ).delete()
    db.commit()
    redis = get_redis_client()
    redis.delete(f"hunt:history:{hunt_id}")
    redis.delete(f"hunt:results:{hunt_id}")


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


def _hit_key(hit: dict, hunt_type: str, index_target: str | None) -> str | None:
    """Return a stable identifier for a hit, used to compare results across runs."""
    if hunt_type == "opensearch":
        if index_target == "correlations":
            src = hit.get("source_attribute_uuid")
            tgt = hit.get("target_attribute_uuid")
            if src is None and tgt is None:
                return None
            return f"{src or ''}|{tgt or ''}"
        return hit.get("uuid")
    if hunt_type == "mitre-attack-pattern":
        return hit.get("uuid")
    if hunt_type == "cpe":
        return hit.get("cve_id")
    if hunt_type == "rulezet":
        return hit.get("detail_url") or hit.get("title")
    return None


def _tag_new_hits(
    hits: list[dict],
    previous_hits: list[dict] | None,
    hunt_type: str,
    index_target: str | None,
) -> None:
    """Mutate hits in place to add an `is_new` flag relative to previous_hits.

    On the first run (previous_hits is None) nothing is flagged as new — otherwise
    every row would be highlighted, which defeats the purpose of the indicator.
    """
    if previous_hits is None:
        for hit in hits:
            hit["is_new"] = False
        return

    previous_keys = {
        key
        for key in (_hit_key(h, hunt_type, index_target) for h in previous_hits)
        if key is not None
    }
    for hit in hits:
        key = _hit_key(hit, hunt_type, index_target)
        hit["is_new"] = key is not None and key not in previous_keys


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
    db.add(
        hunt_models.HuntRunHistory(hunt_id=db_hunt.id, run_at=now, match_count=total)
    )
    db.commit()
    db.refresh(db_hunt)

    redis = get_redis_client()

    # Diff against the previous run's stored results before overwriting them, so
    # the persisted payload carries an `is_new` flag for each hit.
    previous_raw = redis.get(f"hunt:results:{db_hunt.id}")
    previous_hits: list[dict] | None = None
    if previous_raw is not None:
        try:
            previous_hits = json.loads(previous_raw).get("hits", [])
        except (ValueError, TypeError):
            previous_hits = None
    _tag_new_hits(hits, previous_hits, db_hunt.hunt_type, db_hunt.index_target)

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


def _run_cpe_hunt(db: Session, db_hunt: hunt_models.Hunt):
    try:
        cves = vulnerability_lookup.lookup_by_cpe(db_hunt.query)
        if not isinstance(cves, list):
            cves = []
    except Exception as e:
        logger.error("CPE hunt %s failed: %s", db_hunt.id, e)
        cves = []

    total = len(cves)
    _persist_hunt_run(db, db_hunt, total, cves, db_hunt.last_match_count)

    return {
        "hunt": hunt_schemas.Hunt.model_validate(db_hunt),
        "total": total,
        "hits": cves,
    }


MITRE_ATTACK_PATTERN_TAG_PREFIX = "misp-galaxy:mitre-attack-pattern="
MITRE_EXTERNAL_ID_RE = re.compile(r"^T\d{4}(?:\.\d{3})?$", re.IGNORECASE)
UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)


def _resolve_mitre_cluster_value(db: Session, token: str) -> str | None:
    """Return the human-readable MITRE ATT&CK cluster value for a T-code or UUID."""
    query = db.query(galaxy_models.GalaxyCluster.value).filter(
        galaxy_models.GalaxyCluster.type == "mitre-attack-pattern",
    )
    if UUID_RE.match(token):
        row = query.filter(galaxy_models.GalaxyCluster.uuid == token).first()
    else:
        row = (
            query.join(
                galaxy_models.GalaxyElement,
                galaxy_models.GalaxyElement.galaxy_cluster_id
                == galaxy_models.GalaxyCluster.id,
            )
            .filter(
                galaxy_models.GalaxyElement.key == "external_id",
                galaxy_models.GalaxyElement.value == token.upper(),
            )
            .first()
        )
    return row.value if row else None


def _normalize_mitre_attack_query(
    db: Session, query: str
) -> tuple[list[str], list[str]]:
    """Parse user input into a list of MITRE ATT&CK pattern tag names.

    Accepts MITRE technique codes (T1391, T1391.001), cluster UUIDs, or full tag
    names — comma or newline separated. Returns (tag_names, unresolved_tokens).
    Resolved tokens are rendered as ``misp-galaxy:mitre-attack-pattern="<value>"``
    to match the tag form produced by ``enable_galaxy_tags``.
    """
    if not query:
        return [], []
    tokens = [
        token.strip()
        for token in query.replace("\n", ",").split(",")
        if token.strip()
    ]
    tag_names: list[str] = []
    unresolved: list[str] = []
    seen: set[str] = set()
    for token in tokens:
        tag: str | None
        if token.startswith(MITRE_ATTACK_PATTERN_TAG_PREFIX):
            tag = token
        elif UUID_RE.match(token) or MITRE_EXTERNAL_ID_RE.match(token):
            cluster_value = _resolve_mitre_cluster_value(db, token)
            if cluster_value is None:
                unresolved.append(token)
                continue
            tag = f'{MITRE_ATTACK_PATTERN_TAG_PREFIX}"{cluster_value}"'
        else:
            unresolved.append(token)
            continue
        if tag not in seen:
            seen.add(tag)
            tag_names.append(tag)
    return tag_names, unresolved


MITRE_ALLOWED_INDEX_TARGETS = ("events", "attributes", "attributes_and_events")

INDEX_TO_DOC_KIND = {
    "misp-attributes": "attribute",
    "misp-events": "event",
}


def _run_mitre_attack_hunt(db: Session, db_hunt: hunt_models.Hunt):
    tag_names, unresolved = _normalize_mitre_attack_query(db, db_hunt.query)
    if unresolved:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Unknown MITRE ATT&CK technique(s): "
                f"{', '.join(unresolved)}. Use a technique code "
                "(e.g. T1391) matching an enabled mitre-attack-pattern "
                "galaxy cluster."
            ),
        )
    index_target = (
        db_hunt.index_target
        if db_hunt.index_target in MITRE_ALLOWED_INDEX_TARGETS
        else "events"
    )
    if index_target == "attributes_and_events":
        index = f"{INDEX_MAP['attributes']},{INDEX_MAP['events']}"
    else:
        index = INDEX_MAP[index_target]

    if not tag_names:
        _persist_hunt_run(db, db_hunt, 0, [], db_hunt.last_match_count)
        return {
            "hunt": hunt_schemas.Hunt.model_validate(db_hunt),
            "total": 0,
            "hits": [],
        }

    OpenSearchClient = get_opensearch_client()
    body = {
        "size": 100,
        "query": {
            "bool": {
                "should": [
                    {"match_phrase": {"tags.name": tag}} for tag in tag_names
                ],
                "minimum_should_match": 1,
            }
        },
    }

    try:
        response = OpenSearchClient.search(index=index, body=body)
    except Exception as e:
        logger.error("MITRE hunt %s execution failed: %s", db_hunt.id, e)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Search engine error: {e}",
        )

    hits = response["hits"]["hits"]
    total = response["hits"]["total"]["value"]
    hit_sources = []
    for h in hits:
        source = dict(h["_source"])
        kind = INDEX_TO_DOC_KIND.get(h.get("_index"))
        if kind:
            source["_doc_kind"] = kind
        hit_sources.append(source)

    _persist_hunt_run(db, db_hunt, total, hit_sources, db_hunt.last_match_count)

    return {
        "hunt": hunt_schemas.Hunt.model_validate(db_hunt),
        "total": total,
        "hits": hit_sources,
    }


def _run_hunt(db: Session, db_hunt: hunt_models.Hunt):
    if db_hunt.hunt_type == "rulezet":
        return _run_rulezet_hunt(db, db_hunt)
    if db_hunt.hunt_type == "cpe":
        return _run_cpe_hunt(db, db_hunt)
    if db_hunt.hunt_type == "mitre-attack-pattern":
        return _run_mitre_attack_hunt(db, db_hunt)
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
