from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, Security, status
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.orm import Session

from app.auth.security import get_current_active_user
from app.db.session import get_db
from app.repositories import events as events_repository
from app.repositories import sinks as sinks_repository
from app.schemas import sink as sink_schemas
from app.schemas import user as user_schemas
from app.worker import tasks

router = APIRouter()


def _get_sink_or_404(db: Session, sink_id: int):
    db_sink = sinks_repository.get_sink(db, sink_id)
    if db_sink is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Sink not found"
        )
    return db_sink


@router.get("/sinks/", response_model=list[sink_schemas.Sink])
def get_sinks(
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(get_current_active_user, scopes=["sinks:read"]),
):
    return sinks_repository.get_sinks(db)


@router.post(
    "/sinks/", response_model=sink_schemas.Sink, status_code=status.HTTP_201_CREATED
)
def create_sink(
    sink: sink_schemas.SinkCreate,
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["sinks:create"]
    ),
):
    return sinks_repository.create_sink(db, sink)


@router.get("/sinks/{sink_id}", response_model=sink_schemas.Sink)
def get_sink(
    sink_id: int,
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(get_current_active_user, scopes=["sinks:read"]),
):
    return _get_sink_or_404(db, sink_id)


@router.patch("/sinks/{sink_id}", response_model=sink_schemas.Sink)
def update_sink(
    sink_id: int,
    payload: sink_schemas.SinkUpdate,
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["sinks:update"]
    ),
):
    db_sink = _get_sink_or_404(db, sink_id)
    try:
        return sinks_repository.update_sink(db, db_sink, payload)
    except ValueError as error:
        # An invalid config for the sink's type, or a new destination without
        # its secret. Neither message carries config values.
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)
        )


@router.delete("/sinks/{sink_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_sink(
    sink_id: int,
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["sinks:delete"]
    ),
):
    sinks_repository.delete_sink(db, _get_sink_or_404(db, sink_id))
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/sinks/{sink_id}/test", response_model=sink_schemas.SinkTestResult)
async def test_sink(
    sink_id: int,
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(get_current_active_user, scopes=["sinks:test"]),
):
    """Send one synthetic indicator now and report whether the sink took it."""
    db_sink = _get_sink_or_404(db, sink_id)
    return await run_in_threadpool(sinks_repository.send_test, db_sink)


@router.post(
    "/sinks/{sink_id}/deliver/{event_uuid}",
    response_model=sink_schemas.SinkDeliveryQueued,
    status_code=status.HTTP_202_ACCEPTED,
)
def deliver_event(
    sink_id: int,
    event_uuid: UUID,
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(get_current_active_user, scopes=["sinks:test"]),
):
    """Queue a delivery of one event to the sink, published or not.

    For backfilling a new sink or replaying an event a SIEM missed.
    """
    db_sink = _get_sink_or_404(db, sink_id)
    if events_repository.get_event_from_opensearch(event_uuid) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Event not found"
        )
    result = tasks.deliver_to_sink.apply_async(
        (db_sink.id, str(event_uuid)), queue=sinks_repository.SINKS_QUEUE
    )
    return sink_schemas.SinkDeliveryQueued(task_id=result.id)
