import logging
from datetime import datetime, timezone
from uuid import uuid4

from fastapi_pagination.ext.sqlalchemy import paginate
from opensearchpy import helpers as opensearch_helpers
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import export as export_models
from app.schemas import export as export_schemas
from app.services.exports import converters
from app.services.exports_storage import \
    delete_export as delete_export_artifact
from app.services.exports_storage import store_export
from app.services.opensearch import get_opensearch_client

logger = logging.getLogger(__name__)

# The redbeat task that a recurring export schedule fires.
EXPORT_TASK_NAME = "app.worker.tasks.run_export"


def _build_interval(schedule: dict):
    """Translate a stored schedule dict into a celery beat schedule."""
    from celery.schedules import crontab
    from celery.schedules import schedule as celery_schedule

    if schedule.get("type") == "crontab":
        return crontab(
            minute=schedule.get("minute", "*"),
            hour=schedule.get("hour", "*"),
            day_of_week=schedule.get("day_of_week", "*"),
            day_of_month=schedule.get("day_of_month", "*"),
            month_of_year=schedule.get("month_of_year", "*"),
        )
    return celery_schedule(int(schedule.get("every")))


def _register_export_schedule(db_export: export_models.Export) -> str:
    """Create or replace the redbeat entry for a recurring export.

    Reuses the row's existing ``scheduled_task_name`` so updates replace the
    same entry. Returns the entry name to persist on the row.
    """
    from redbeat import RedBeatSchedulerEntry

    from app.worker.tasks import celery_app

    name = db_export.scheduled_task_name or str(uuid4())
    entry = RedBeatSchedulerEntry(
        name,
        EXPORT_TASK_NAME,
        _build_interval(db_export.schedule),
        args=[db_export.id],
        kwargs={},
        app=celery_app,
        enabled=db_export.schedule_enabled,
    )
    entry.save()
    return name


def _unregister_export_schedule(name: str) -> None:
    """Best-effort removal of an export's redbeat entry."""
    if not name:
        return
    from redbeat import RedBeatSchedulerEntry

    from app.worker.tasks import celery_app

    try:
        RedBeatSchedulerEntry.from_key(f"redbeat:{name}", app=celery_app).delete()
    except Exception as e:
        logger.warning("Failed to remove export schedule %s: %s", name, e)

INDEX_MAP = {
    "attributes": "misp-attributes",
    "events": "misp-events",
}

# Safety cap so a broad query can't exhaust worker memory.
MAX_EXPORT_RECORDS = 100_000


def get_exports(
    db: Session, user_id: int, params: export_schemas.ExportQueryParams = None
):
    query = select(export_models.Export).where(export_models.Export.user_id == user_id)
    if params and params.filter:
        query = query.where(export_models.Export.name.ilike(f"%{params.filter}%"))
    query = query.order_by(export_models.Export.created_at.desc())
    return paginate(db, query)


def get_export_by_id(db: Session, export_id: int, user_id: int) -> export_models.Export:
    return (
        db.query(export_models.Export)
        .filter(
            export_models.Export.id == export_id,
            export_models.Export.user_id == user_id,
        )
        .first()
    )


def create_export(
    db: Session, export: export_schemas.ExportCreate, user_id: int
) -> export_models.Export:
    db_export = export_models.Export(
        **export.model_dump(),
        user_id=user_id,
        status="queued",
        created_at=datetime.now(timezone.utc),
    )
    db.add(db_export)
    db.commit()
    db.refresh(db_export)

    if db_export.schedule:
        db_export.scheduled_task_name = _register_export_schedule(db_export)
        db.commit()
        db.refresh(db_export)

    return db_export


def update_export_schedule(
    db: Session,
    export_id: int,
    user_id: int,
    payload: export_schemas.ExportScheduleUpdate,
) -> export_models.Export:
    """Set, change, pause/resume, or clear an export's recurring schedule."""
    db_export = get_export_by_id(db, export_id, user_id)
    if db_export is None:
        return None

    # schedule explicitly set to null -> unschedule.
    if "schedule" in payload.model_fields_set and payload.schedule is None:
        _unregister_export_schedule(db_export.scheduled_task_name)
        db_export.schedule = None
        db_export.scheduled_task_name = None
        db_export.schedule_enabled = False
        db.commit()
        db.refresh(db_export)
        return db_export

    if payload.schedule is not None:
        db_export.schedule = payload.schedule.model_dump()
    if payload.schedule_enabled is not None:
        db_export.schedule_enabled = payload.schedule_enabled

    if db_export.schedule:
        db_export.scheduled_task_name = _register_export_schedule(db_export)

    db.commit()
    db.refresh(db_export)
    return db_export


def set_celery_task_id(db: Session, export_id: int, task_id: str) -> None:
    db_export = (
        db.query(export_models.Export)
        .filter(export_models.Export.id == export_id)
        .first()
    )
    if db_export is not None:
        db_export.celery_task_id = task_id
        db.commit()


def delete_export(db: Session, export_id: int, user_id: int):
    db_export = get_export_by_id(db, export_id, user_id)
    if not db_export:
        return None
    if db_export.scheduled_task_name:
        _unregister_export_schedule(db_export.scheduled_task_name)
    if db_export.storage_key:
        delete_export_artifact(db_export.storage_key)
    db.delete(db_export)
    db.commit()
    return {"status": "success"}


def _fetch_hits(index: str, query: str) -> list[dict]:
    """Scan all documents matching the query_string, capped at MAX_EXPORT_RECORDS."""
    client = get_opensearch_client()
    body = {"query": {"query_string": {"query": query}}}
    hits: list[dict] = []
    for doc in opensearch_helpers.scan(
        client=client,
        index=index,
        query=body,
        scroll="2m",
        size=500,
    ):
        source = doc.get("_source")
        if source is None:
            continue
        # Skip soft-deleted documents — they shouldn't appear in exports.
        if source.get("deleted"):
            continue
        hits.append(source)
        if len(hits) >= MAX_EXPORT_RECORDS:
            logger.warning(
                "Export hit the %s record cap; results truncated.",
                MAX_EXPORT_RECORDS,
            )
            break
    return hits


def run_export(db: Session, export_id: int) -> None:
    """Execute an export job: query OpenSearch, convert, store the artifact.

    Updates the row's status as it progresses. Any failure is recorded on the
    row rather than raised, so the job is observable via the API.
    """
    db_export = (
        db.query(export_models.Export)
        .filter(export_models.Export.id == export_id)
        .first()
    )
    if db_export is None:
        logger.error("run_export: export %s not found", export_id)
        return

    db_export.status = "running"
    db_export.started_at = datetime.now(timezone.utc)
    db_export.error = None
    db.commit()

    try:
        index = INDEX_MAP.get(db_export.index_target, "misp-attributes")
        hits = _fetch_hits(index, db_export.query)

        content, extension, _content_type = converters.convert(
            db_export.format, hits, db_export.index_target
        )

        storage_key = f"export-{db_export.id}.{extension}"
        stored_key = store_export(storage_key, content)

        db_export.storage_key = stored_key
        db_export.file_size = len(content)
        db_export.record_count = len(hits)
        db_export.status = "completed"
        db_export.finished_at = datetime.now(timezone.utc)
        db_export.last_run_at = db_export.finished_at
        db.commit()
        logger.info(
            "Export %s completed: %s records, %s bytes",
            export_id,
            len(hits),
            len(content),
        )
    except Exception as e:
        logger.exception("Export %s failed", export_id)
        db.rollback()
        db_export = (
            db.query(export_models.Export)
            .filter(export_models.Export.id == export_id)
            .first()
        )
        if db_export is not None:
            db_export.status = "failed"
            db_export.error = str(e)
            db_export.finished_at = datetime.now(timezone.utc)
            db.commit()
