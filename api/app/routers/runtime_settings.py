from app.auth.security import get_current_active_user
from app.services.runtime_settings_provider import get_runtime_settings
from app.schemas import user as user_schemas
from fastapi import APIRouter, Security, Depends
from app.services.runtime_settings import RuntimeSettings

router = APIRouter()


@router.get("/settings/runtime")
def list_runtime_settings(
    runtime_settings: RuntimeSettings = Depends(get_runtime_settings),
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["settings:read"]
    ),
):
    return runtime_settings.all()


@router.get("/settings/runtime/{namespace}")
def get_runtime_setting(
    namespace: str,
    runtime_settings: RuntimeSettings = Depends(get_runtime_settings),
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["settings:read"]
    ),
):
    return {namespace: runtime_settings.get(namespace)}


@router.post("/settings/runtime/{namespace}")
def set_runtime_setting(
    namespace: str,
    value: dict,
    runtime_settings: RuntimeSettings = Depends(get_runtime_settings),
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["settings:update"]
    ),
):
    runtime_settings.set(namespace, value)
    return {"message": "Setting updated"}


@router.delete("/settings/runtime/{namespace}")
def delete_runtime_setting(
    namespace: str,
    runtime_settings: RuntimeSettings = Depends(get_runtime_settings),
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["settings:delete"]
    ),
):
    runtime_settings.delete(namespace)
    return {"message": "Setting deleted"}
