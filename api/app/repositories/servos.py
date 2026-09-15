"""CRUD for Tech Lab transformation servos + the cluster pipeline inventory."""

import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi_pagination.ext.sqlalchemy import paginate
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models import servo as servo_models
from app.schemas import servo as servo_schemas
from app.services.tech_lab.servos import chain

logger = logging.getLogger(__name__)


def get_servos(db: Session, params: Optional[servo_schemas.ServoQueryParams] = None):
    query = select(servo_models.Servo).order_by(
        servo_models.Servo.position, servo_models.Servo.id
    )
    if params is not None and params.filter:
        needle = f"%{params.filter}%"
        query = query.where(
            or_(
                servo_models.Servo.name.ilike(needle),
                servo_models.Servo.slug.ilike(needle),
                servo_models.Servo.description.ilike(needle),
            )
        )
    return paginate(db, query)


def get_servo_by_id(db: Session, servo_id: int) -> Optional[servo_models.Servo]:
    return db.get(servo_models.Servo, servo_id)


def get_servo_by_slug(db: Session, slug: str) -> Optional[servo_models.Servo]:
    return db.scalars(
        select(servo_models.Servo).where(servo_models.Servo.slug == slug)
    ).first()


def _next_position(db: Session) -> int:
    rows = db.scalars(select(servo_models.Servo.position)).all()
    return (max(rows) + 1) if rows else 0


def create_servo(
    db: Session, servo: servo_schemas.ServoCreate, user_id: int
) -> servo_models.Servo:
    db_servo = servo_models.Servo(
        user_id=user_id,
        name=servo.name,
        slug=servo.slug,
        description=servo.description,
        processors=servo.processors,
        target_index=chain.TARGET_INDEX,
        enabled=servo.enabled,
        position=servo.position or _next_position(db),
        created_at=datetime.now(timezone.utc),
    )
    db.add(db_servo)
    db.commit()
    db.refresh(db_servo)
    chain.sync(db)
    db.refresh(db_servo)
    return db_servo


def update_servo(
    db: Session, db_servo: servo_models.Servo, update: servo_schemas.ServoUpdate
) -> servo_models.Servo:
    data = update.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(db_servo, key, value)
    db_servo.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(db_servo)
    chain.sync(db)
    db.refresh(db_servo)
    return db_servo


def delete_servo(db: Session, db_servo: servo_models.Servo) -> None:
    slug = db_servo.slug
    db.delete(db_servo)
    db.commit()
    # The chain is rewritten first, so nothing references the pipeline by the
    # time it goes.
    chain.sync(db)
    chain.delete_pipeline(slug)


def list_pipelines(db: Session) -> list[servo_schemas.PipelineSummary]:
    """Every ingest pipeline in the cluster, classified and annotated.

    System and external pipelines are read-only: they are managed in the repo
    (or by someone else) and OpenSearch records no modification time for them,
    so ``updated_at`` stays unset rather than invented.
    """
    servos_by_pipeline = {
        chain.pipeline_name(s.slug): s
        for s in db.scalars(select(servo_models.Servo)).all()
    }

    summaries = []
    for name, definition in chain.get_cluster_pipelines().items():
        kind = chain.classify(name)
        db_servo = servos_by_pipeline.get(name)
        if kind == "servo" and db_servo is None:
            # A servo_* pipeline with no row behind it is not ours to edit.
            kind = "external"
        summaries.append(
            servo_schemas.PipelineSummary(
                name=name,
                kind=kind,
                description=definition.get("description"),
                processor_types=chain.processor_types(definition),
                processor_count=len(definition.get("processors") or []),
                read_only=kind != "servo",
                updated_at=(
                    (db_servo.updated_at or db_servo.created_at) if db_servo else None
                ),
                servo_id=db_servo.id if db_servo else None,
                enabled=db_servo.enabled if db_servo else None,
            )
        )
    return sorted(summaries, key=lambda s: (s.kind != "system", s.name))


def get_pipeline(db: Session, name: str) -> Optional[servo_schemas.PipelineDetail]:
    definition = chain.get_cluster_pipeline(name)
    if definition is None:
        return None
    kind = chain.classify(name)
    db_servo = None
    if kind == "servo":
        db_servo = get_servo_by_slug(db, name[len(servo_schemas.SERVO_PREFIX) :])
        if db_servo is None:
            kind = "external"
    return servo_schemas.PipelineDetail(
        name=name,
        kind=kind,
        description=definition.get("description"),
        processor_types=chain.processor_types(definition),
        processor_count=len(definition.get("processors") or []),
        read_only=kind != "servo",
        updated_at=(db_servo.updated_at or db_servo.created_at) if db_servo else None,
        servo_id=db_servo.id if db_servo else None,
        enabled=db_servo.enabled if db_servo else None,
        definition=definition,
    )
