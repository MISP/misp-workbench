import logging
from app.auth.security import get_current_active_user
from app.schemas import user as user_schemas
from app.repositories import sightings as sightings_repository
from fastapi import APIRouter, Security, Query, Depends, Body
from typing import Optional, Union, List

router = APIRouter()

logger = logging.getLogger(__name__)


async def get_sightings_parameters(
    attribute_uuid: Optional[str] = None, type: Optional[str] = None
):
    return {
        "attribute_uuid": attribute_uuid,
        "type": type,
    }


@router.get("/sightings/")
def get_sightings(
    params: dict = Depends(get_sightings_parameters),
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["sightings:read"]
    ),
):
    from_value = (page - 1) * size

    return sightings_repository.get_sightings(
        params=params, page=page, from_value=from_value, size=size
    )


@router.post("/sightings/")
def create_sightings(
    sightings: Union[dict, List[dict]] = Body(...),
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["sightings:create"]
    ),
):

    return sightings_repository.create_sightings(user, sightings)


async def get_sighting_activity_by_value_parameters(
    value: str, period: Optional[str] = "7d", interval: Optional[str] = "1h"
):
    return {
        "value": value,
        "period": period,
        "interval": interval,
    }


@router.get("/sightings/histogram")
def get_sighting_activity_by_value(
    params: dict = Depends(get_sighting_activity_by_value_parameters),
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["sightings:read"]
    ),
):
    return sightings_repository.get_sightings_activity_by_value(params)


@router.get("/sightings/stats")
def get_sighting_activity_by_value(
    params: dict = Depends(get_sighting_activity_by_value_parameters),
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["sightings:read"]
    ),
):
    return sightings_repository.get_sightings_stats_by_value(params)
