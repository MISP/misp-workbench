from app.auth.auth import get_current_active_user
from app.repositories import modules as modules_repository
from app.schemas import module as module_schemas
from app.schemas import user as user_schemas
from fastapi import APIRouter, Security

router = APIRouter()


@router.get("/modules/", response_model=list[module_schemas.Module])
async def get_events(
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["modules:read"]
    ),
) -> list[module_schemas.Module]:

    return modules_repository.get_modules()
