import logging
from app.auth.security import get_current_active_user
from app.schemas import user as user_schemas
from app.schemas import task as task_schemas
from app.schemas import correlation as correlation_schemas
from app.repositories import correlations as correlations_repository
from app.worker import tasks
from fastapi import APIRouter, Security, Query, Depends, status
from typing import Optional

router = APIRouter()

logger = logging.getLogger(__name__)


async def get_correlations_parameters(
    source_attribute_uuid: Optional[str] = None,
    source_event_uuid: Optional[str] = None,
    target_attribute_uuid: Optional[str] = None,
    target_event_uuid: Optional[str] = None,
    match_type: Optional[str] = None,
) -> correlation_schemas.CorrelationQueryParams:
    return correlation_schemas.CorrelationQueryParams(
        source_attribute_uuid=source_attribute_uuid,
        source_event_uuid=source_event_uuid,
        target_attribute_uuid=target_attribute_uuid,
        target_event_uuid=target_event_uuid,
        match_type=match_type,
    )


@router.get("/correlations/", response_model=correlation_schemas.CorrelationListResponse)
def get_correlations(
    params: correlation_schemas.CorrelationQueryParams = Depends(get_correlations_parameters),
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["correlations:read"]
    ),
) -> correlation_schemas.CorrelationListResponse:
    from_value = (page - 1) * size

    return correlations_repository.get_correlations(
        params=params, page=page, from_value=from_value, size=size
    )


@router.get(
    "/correlations/events/{source_event_uuid}/top",
    response_model=list[correlation_schemas.CorrelationEventBucket],
)
def get_top_correlated_events(
    source_event_uuid: str,
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["correlations:read"]
    ),
) -> list[correlation_schemas.CorrelationEventBucket]:
    return correlations_repository.get_top_correlated_events(
        source_event_uuid=source_event_uuid
    )


@router.post(
    "/correlations/run",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=task_schemas.Task,
)
def run_correlations(
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["correlations:create"]
    ),
) -> task_schemas.Task:
    task = tasks.generate_correlations.delay()
    logger.info("Enqueued generate_correlations task with ID: %s", task.id)

    return task_schemas.Task(
        task_id=task.id,
        status=task.status,
        message="generate correlations job enqueued",
    )


@router.get(
    "/correlations/stats",
    response_model=correlation_schemas.CorrelationStatsResponse,
)
def get_correlations_stats(
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["correlations:read"]
    ),
) -> correlation_schemas.CorrelationStatsResponse:
    return correlations_repository.get_correlations_stats()


@router.delete(
    "/correlations/",
    response_model=correlation_schemas.CorrelationDeleteResponse,
)
def delete_correlations(
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["correlations:delete"]
    ),
) -> correlation_schemas.CorrelationDeleteResponse:
    return correlations_repository.delete_correlations()
