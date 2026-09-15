"""Tech Lab — Transformation Servos router.

Servos are user-authored OpenSearch ingest pipelines that run on every
attribute indexed into ``misp-attributes``. Endpoints live under
``/tech-lab/servos`` alongside the rest of the Tech Lab umbrella.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Security, status
from fastapi_pagination import Page
from sqlalchemy.orm import Session

from app.auth.security import get_current_active_user
from app.db.session import get_db
from app.repositories import servos as servos_repository
from app.schemas import servo as servo_schemas
from app.schemas import user as user_schemas
from app.services import audit
from app.services.tech_lab.servos import chain

router = APIRouter()


async def _list_params(
    filter: Optional[str] = None,
) -> servo_schemas.ServoQueryParams:
    return servo_schemas.ServoQueryParams(filter=filter)


def _validate_processors(processors: list[dict], sample_doc: Optional[dict] = None):
    """Reject a servo OpenSearch would not accept, before it reaches the DB.

    A pipeline that fails to parse would otherwise be written to Postgres and
    then blow up at sync time, leaving the row and the cluster disagreeing.
    """
    doc = sample_doc or {"type": "ip-src", "value": "1.2.3.4"}
    ok, _docs, error = chain.simulate(processors, [doc])
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"OpenSearch rejected the processors: {error}",
        )


# ── Pipeline inventory (read-only) ──────────────────────────────────────────


@router.get(
    "/tech-lab/servos/pipelines",
    response_model=list[servo_schemas.PipelineSummary],
)
async def list_pipelines(
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(get_current_active_user, scopes=["servos:read"]),
):
    """Every ingest pipeline in the cluster: shipped system ones, servos, and
    anything a third party put there."""
    return servos_repository.list_pipelines(db)


@router.get(
    "/tech-lab/servos/pipelines/{name}",
    response_model=servo_schemas.PipelineDetail,
)
async def get_pipeline(
    name: str,
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(get_current_active_user, scopes=["servos:read"]),
):
    pipeline = servos_repository.get_pipeline(db, name)
    if pipeline is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Pipeline not found"
        )
    return pipeline


@router.get(
    "/tech-lab/servos/templates",
    response_model=list[servo_schemas.ServoTemplate],
)
async def list_templates(
    user: user_schemas.User = Security(get_current_active_user, scopes=["servos:read"]),
):
    """Starter processor sets for the common transformations."""
    return chain.load_templates()


# ── Dry run ─────────────────────────────────────────────────────────────────


@router.post(
    "/tech-lab/servos/simulate",
    response_model=servo_schemas.ServoSimulateResponse,
)
async def simulate(
    payload: servo_schemas.ServoSimulateRequest,
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["servos:create"]
    ),
):
    """Run processors against sample documents without persisting anything."""
    docs = list(payload.docs or [])
    if payload.attribute_uuids:
        docs += chain.fetch_sample_docs(payload.attribute_uuids)
    if not docs:
        docs = [{"type": "ip-src", "value": "1.2.3.4"}]

    ok, results, error = chain.simulate(payload.processors, docs)
    return servo_schemas.ServoSimulateResponse(ok=ok, docs=results, error=error)


# ── Servo CRUD ──────────────────────────────────────────────────────────────


@router.get("/tech-lab/servos/", response_model=Page[servo_schemas.Servo])
async def list_servos(
    db: Session = Depends(get_db),
    params: servo_schemas.ServoQueryParams = Depends(_list_params),
    user: user_schemas.User = Security(get_current_active_user, scopes=["servos:read"]),
):
    return servos_repository.get_servos(db, params=params)


@router.post(
    "/tech-lab/servos/",
    response_model=servo_schemas.Servo,
    status_code=status.HTTP_201_CREATED,
)
async def create_servo(
    payload: servo_schemas.ServoCreate,
    request: Request,
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["servos:create"]
    ),
):
    if servos_repository.get_servo_by_slug(db, payload.slug) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A servo with slug '{payload.slug}' already exists",
        )
    _validate_processors(payload.processors)

    db_servo = servos_repository.create_servo(db, payload, user_id=user.id)
    audit.record(
        db,
        action="servo.created",
        resource_type="servo",
        resource_id=db_servo.id,
        actor_user_id=user.id,
        request=request,
        metadata={
            "slug": db_servo.slug,
            "enabled": db_servo.enabled,
            "processors": db_servo.processors,
        },
    )
    db.commit()
    return db_servo


@router.get("/tech-lab/servos/{servo_id}", response_model=servo_schemas.Servo)
async def get_servo(
    servo_id: int,
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(get_current_active_user, scopes=["servos:read"]),
):
    db_servo = servos_repository.get_servo_by_id(db, servo_id)
    if db_servo is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Servo not found"
        )
    return db_servo


@router.patch("/tech-lab/servos/{servo_id}", response_model=servo_schemas.Servo)
async def update_servo(
    servo_id: int,
    payload: servo_schemas.ServoUpdate,
    request: Request,
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["servos:update"]
    ),
):
    db_servo = servos_repository.get_servo_by_id(db, servo_id)
    if db_servo is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Servo not found"
        )
    if payload.processors is not None:
        _validate_processors(payload.processors)

    changed = payload.model_dump(exclude_unset=True)
    db_servo = servos_repository.update_servo(db, db_servo, payload)
    audit.record(
        db,
        action="servo.updated",
        resource_type="servo",
        resource_id=db_servo.id,
        actor_user_id=user.id,
        request=request,
        metadata={"slug": db_servo.slug, "changed": sorted(changed)},
    )
    db.commit()
    return db_servo


@router.delete("/tech-lab/servos/{servo_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_servo(
    servo_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["servos:delete"]
    ),
):
    db_servo = servos_repository.get_servo_by_id(db, servo_id)
    if db_servo is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Servo not found"
        )
    snapshot = {"id": db_servo.id, "slug": db_servo.slug, "name": db_servo.name}
    servos_repository.delete_servo(db, db_servo)
    audit.record(
        db,
        action="servo.deleted",
        resource_type="servo",
        resource_id=snapshot["id"],
        actor_user_id=user.id,
        request=request,
        metadata=snapshot,
    )
    db.commit()
