"""CRUD + trigger dispatch for reactor scripts (Tech Lab)."""

import hashlib
import logging
import uuid
from datetime import datetime, timezone

from app.models import reactor as reactor_models
from app.schemas import reactor as reactor_schemas
from app.services.tech_lab.reactor import storage as reactor_storage
from app.services.tech_lab.reactor import triggers as reactor_triggers
from app.services.tech_lab.reactor.runner import read_log
from fastapi_pagination.ext.sqlalchemy import paginate
from sqlalchemy import select
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────────
# CRUD
# ──────────────────────────────────────────────────────────────────────────


def get_scripts(db: Session, user_id: int, params=None):
    query = select(reactor_models.ReactorScript).where(
        reactor_models.ReactorScript.user_id == user_id
    )
    if params and getattr(params, "filter", None):
        query = query.where(
            reactor_models.ReactorScript.name.ilike(f"%{params.filter}%")
        )
    query = query.order_by(reactor_models.ReactorScript.created_at.desc())
    return paginate(db, query)


def get_script_by_id(
    db: Session, script_id: int, user_id: int
) -> reactor_models.ReactorScript | None:
    return (
        db.query(reactor_models.ReactorScript)
        .filter(
            reactor_models.ReactorScript.id == script_id,
            reactor_models.ReactorScript.user_id == user_id,
        )
        .first()
    )


def create_script(
    db: Session, script: reactor_schemas.ReactorScriptCreate, user_id: int
) -> reactor_models.ReactorScript:
    source_uri, sha = _store_source(script.source)
    db_script = reactor_models.ReactorScript(
        user_id=user_id,
        name=script.name,
        description=script.description,
        language="python",
        source_uri=source_uri,
        source_sha256=sha,
        entrypoint=script.entrypoint,
        triggers=[t.model_dump() for t in script.triggers],
        status=script.status,
        timeout_seconds=script.timeout_seconds,
        max_writes=script.max_writes,
        created_at=datetime.now(timezone.utc),
    )
    db.add(db_script)
    db.commit()
    db.refresh(db_script)
    return db_script


def update_script(
    db: Session,
    script_id: int,
    update: reactor_schemas.ReactorScriptUpdate,
    user_id: int,
) -> reactor_models.ReactorScript | None:
    db_script = get_script_by_id(db, script_id, user_id)
    if db_script is None:
        return None

    data = update.model_dump(exclude_unset=True)
    if "source" in data and data["source"] is not None:
        new_uri, new_sha = _store_source(data.pop("source"))
        db_script.source_uri = new_uri
        db_script.source_sha256 = new_sha
    elif "source" in data:
        data.pop("source")

    if "triggers" in data and data["triggers"] is not None:
        data["triggers"] = [
            t.model_dump() if hasattr(t, "model_dump") else t for t in data["triggers"]
        ]

    for key, value in data.items():
        setattr(db_script, key, value)
    db_script.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(db_script)
    return db_script


def delete_script(db: Session, script_id: int, user_id: int):
    db_script = get_script_by_id(db, script_id, user_id)
    if db_script is None:
        return None
    _delete_source(db_script.source_uri)
    db.delete(db_script)
    db.commit()
    return {"status": "success"}


def get_script_source(db: Session, script_id: int, user_id: int) -> str | None:
    db_script = get_script_by_id(db, script_id, user_id)
    if db_script is None:
        return None
    return _read_source(db_script.source_uri)


# ──────────────────────────────────────────────────────────────────────────
# Runs
# ──────────────────────────────────────────────────────────────────────────


def get_runs(db: Session, script_id: int, user_id: int):
    db_script = get_script_by_id(db, script_id, user_id)
    if db_script is None:
        return None
    query = (
        select(reactor_models.ReactorRun)
        .where(reactor_models.ReactorRun.script_id == script_id)
        .order_by(reactor_models.ReactorRun.created_at.desc())
    )
    return paginate(db, query)


def get_run(db: Session, run_id: int, user_id: int) -> reactor_models.ReactorRun | None:
    run = (
        db.query(reactor_models.ReactorRun)
        .filter(reactor_models.ReactorRun.id == run_id)
        .first()
    )
    if run is None:
        return None
    db_script = get_script_by_id(db, run.script_id, user_id)
    if db_script is None:
        return None
    return run


def get_run_log(db: Session, run_id: int, user_id: int) -> str | None:
    run = get_run(db, run_id, user_id)
    if run is None:
        return None
    return read_log(run.log_uri or "")


def create_run(
    db: Session,
    script: reactor_models.ReactorScript,
    triggered_by: dict,
) -> reactor_models.ReactorRun:
    now = datetime.now(timezone.utc)
    run = reactor_models.ReactorRun(
        script_id=script.id,
        triggered_by=triggered_by,
        status="queued",
        created_at=now,
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    return run


# ──────────────────────────────────────────────────────────────────────────
# Trigger dispatch
# ──────────────────────────────────────────────────────────────────────────


def dispatch_triggered_scripts(
    db: Session,
    resource_type: str,
    action: str,
    payload: dict,
) -> list[int]:
    """Find scripts subscribed to (resource_type, action), enqueue runs.

    Returns the list of created run ids (mostly for tests).
    """
    candidates = reactor_triggers.list_active_scripts_for(db, resource_type, action)
    matching = [
        s
        for s in candidates
        if reactor_triggers.matches_filters(s.triggers or [], resource_type, action, payload)
    ]
    if not matching:
        return []

    # Local import to avoid circular import (worker.tasks imports this module).
    from app.worker import tasks as worker_tasks

    run_ids: list[int] = []
    for script in matching:
        run = create_run(
            db,
            script,
            triggered_by={
                "resource_type": resource_type,
                "action": action,
                "payload": payload,
            },
        )
        async_result = worker_tasks.run_reactor_script.apply_async(
            args=[run.id], queue="reactor_sandbox"
        )
        run.celery_task_id = getattr(async_result, "id", None)
        db.commit()
        run_ids.append(run.id)
    return run_ids


# ──────────────────────────────────────────────────────────────────────────
# Source storage
# ──────────────────────────────────────────────────────────────────────────


def _store_source(source: str) -> tuple[str, str]:
    sha = hashlib.sha256(source.encode("utf-8")).hexdigest()
    key = f"reactor/scripts/{uuid.uuid4()}.py"
    reactor_storage.write_object(key, source.encode("utf-8"))
    return key, sha


def _read_source(source_uri: str) -> str:
    return reactor_storage.read_object(source_uri).decode("utf-8")


def _delete_source(source_uri: str) -> None:
    reactor_storage.delete_object(source_uri)
