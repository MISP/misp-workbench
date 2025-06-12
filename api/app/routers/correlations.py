from app.auth.auth import get_current_active_user
from app.schemas import user as user_schemas
from app.repositories import correlations as correlations_repository
from fastapi import APIRouter, Security, Query

router = APIRouter()


@router.get("/correlations/")
def get_correlations(
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["correlations:read"]
    ),
):
    from_value = (page - 1) * size

    return correlations_repository.get_correlations(
        page=page, from_value=from_value, size=size
    )


@router.post("/correlations/run")
def run_correlations(
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["correlations:create"]
    ),
):
    return correlations_repository.run_correlations()
