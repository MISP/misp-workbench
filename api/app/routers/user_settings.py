from app.auth.security import get_current_active_user
from app.services.user_settings_provider import get_user_settings
from app.schemas import user as user_schemas
from fastapi import APIRouter, Security, Depends
from app.services.user_settings import UserSettings

router = APIRouter()


@router.get("/settings/user")
def list_user_settings(
    user_settings: UserSettings = Depends(get_user_settings),
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["user_settings:read"]
    ),
):
    return user_settings.all()


@router.get("/settings/user/{namespace}")
def list_user_setting(
    namespace: str,
    user_settings: UserSettings = Depends(get_user_settings),
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["user_settings:read"]
    ),
):
    return {namespace: user_settings.get(namespace)}


@router.post("/settings/user/{namespace}")
def set_user_setting(
    namespace: str,
    value: dict,
    user_settings: UserSettings = Depends(get_user_settings),
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["user_settings:update"]
    ),
):
    user_settings.set(namespace, value)
    return {"message": "User setting updated"}


@router.delete("/settings/user/{namespace}")
def delete_user_setting(
    namespace: str,
    user_settings: UserSettings = Depends(get_user_settings),
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["user_settings:delete"]
    ),
):
    user_settings.delete(namespace)
    return {"message": "User setting deleted"}
