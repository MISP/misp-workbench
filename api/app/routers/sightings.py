import logging
from app.auth.security import get_current_active_user
from app.schemas import user as user_schemas
from app.schemas import sighting as sighting_schemas
from app.repositories import sightings as sightings_repository
from fastapi import APIRouter, HTTPException, Security, Query, Depends, status
from typing import Optional, Union

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
        payload = [s.model_dump(exclude_none=True) for s in sightings]
    else:
        payload = sightings.model_dump(exclude_none=True)
    try:
        return sightings_repository.create_sightings(user, payload)
    except sightings_repository.TooManySightings as error:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail=str(error)
        )


def _misp_add(
    payload: sighting_schemas.MispSightingAdd,
    user,
    attribute_ref: Optional[str] = None,
) -> sighting_schemas.MispSightingAddResponse:
    try:
        sightings = sightings_repository.sightings_from_misp(payload, attribute_ref)
        sightings_repository.create_sightings(user, sightings)
    except sightings_repository.SightingTargetNotFound as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error))
    except sightings_repository.TooManySightings as error:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail=str(error)
        )
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error))

    count = len(sightings)
    message = f"{count} sighting{'s' if count != 1 else ''} successfully added."
    return sighting_schemas.MispSightingAddResponse(
        saved=True, success=True, name=message, message=message, url="/sightings/add"
    )


@router.post(
    "/sightings/add", response_model=sighting_schemas.MispSightingAddResponse
)
def misp_add_sightings(
    payload: sighting_schemas.MispSightingAdd,
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["sightings:create"]
    ),
) -> sighting_schemas.MispSightingAddResponse:
    """MISP-compatible: sight ``value``/``values``, or an attribute by ``uuid``/``id``."""
    return _misp_add(payload, user)


@router.post(
    "/sightings/add/{attribute_ref}",
    response_model=sighting_schemas.MispSightingAddResponse,
)
def misp_add_attribute_sighting(
    attribute_ref: str,
    payload: Optional[sighting_schemas.MispSightingAdd] = None,
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["sightings:create"]
    ),
) -> sighting_schemas.MispSightingAddResponse:
    """MISP-compatible: sight one attribute by uuid (or MISP numeric id)."""
    return _misp_add(payload or sighting_schemas.MispSightingAdd(), user, attribute_ref)


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
