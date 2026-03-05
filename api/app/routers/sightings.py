import logging
from app.auth.security import get_current_active_user
from app.schemas import user as user_schemas
from app.schemas import sighting as sighting_schemas
from app.repositories import sightings as sightings_repository
from fastapi import APIRouter, Security, Query, Depends
from typing import Union

router = APIRouter()

logger = logging.getLogger(__name__)


async def get_sightings_parameters(
    attribute_uuid: str = None, type: str = None
) -> sighting_schemas.SightingQueryParams:
    return sighting_schemas.SightingQueryParams(attribute_uuid=attribute_uuid, type=type)


async def get_sighting_activity_params(
    value: str = Query(...),
    period: str = Query("7d"),
    interval: str = Query("1h"),
) -> sighting_schemas.SightingActivityParams:
    return sighting_schemas.SightingActivityParams(
        value=value, period=period, interval=interval
    )


@router.get("/sightings/", response_model=sighting_schemas.SightingListResponse)
def get_sightings(
    params: sighting_schemas.SightingQueryParams = Depends(get_sightings_parameters),
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["sightings:read"]
    ),
) -> sighting_schemas.SightingListResponse:
    from_value = (page - 1) * size
    return sightings_repository.get_sightings(
        params=params, page=page, from_value=from_value, size=size
    )


@router.post(
    "/sightings/",
    response_model=sighting_schemas.SightingCreateResponse,
    status_code=201,
)
def create_sightings(
    sightings: Union[sighting_schemas.SightingCreate, list[sighting_schemas.SightingCreate]],
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["sightings:create"]
    ),
) -> sighting_schemas.SightingCreateResponse:
    if isinstance(sightings, list):
        payload = [s.model_dump() for s in sightings]
    else:
        payload = sightings.model_dump()
    return sightings_repository.create_sightings(user, payload)


@router.get(
    "/sightings/histogram",
    response_model=sighting_schemas.SightingHistogramResponse,
)
def get_sighting_histogram(
    params: sighting_schemas.SightingActivityParams = Depends(get_sighting_activity_params),
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["sightings:read"]
    ),
) -> sighting_schemas.SightingHistogramResponse:
    return sightings_repository.get_sightings_activity_by_value(params)


@router.get(
    "/sightings/stats",
    response_model=sighting_schemas.SightingStatsResponse,
)
def get_sighting_stats(
    params: sighting_schemas.SightingActivityParams = Depends(get_sighting_activity_params),
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["sightings:read"]
    ),
) -> sighting_schemas.SightingStatsResponse:
    return sightings_repository.get_sightings_stats_by_value(params)
