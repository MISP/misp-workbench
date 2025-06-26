import logging
from app.auth.auth import get_current_active_user
from app.schemas import user as user_schemas
from app.repositories import sightings as sightings_repository
from fastapi import APIRouter, Security, Query, Depends
from typing import Optional

router = APIRouter()

logger = logging.getLogger(__name__)


async def get_sightings_parameters(
    attribute_uuid: Optional[str] = None, sighting_type: Optional[str] = None
):
    return {
        "attribute_uuid": attribute_uuid,
        "sighting_type": sighting_type,
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
    sightings: list[dict],
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["sightings:create"]
    ),
):

    return sightings_repository.create_sightings(user, sightings)
