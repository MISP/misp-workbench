from app.auth.auth import get_current_active_user
from app.dependencies import get_runtime_settings
from app.schemas import user as user_schemas
from fastapi import APIRouter, Security, Depends
from app.services.runtime_settings import RuntimeSettings

router = APIRouter()


@router.get("/settings")
def list_runtime_settings(
    runtime: RuntimeSettings = Depends(get_runtime_settings),
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["setting:read"]
    ),
):
    return runtime.all()


@router.get("/settings/{namespace}")
def get_runtime_setting(
    namespace: str,
    runtime: RuntimeSettings = Depends(get_runtime_settings),
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["setting:read"]
    ),
):
    return {namespace: runtime.get(namespace)}


@router.post("/settings/{namespace}")
def set_runtime_setting(
    namespace: str,
    value: dict,
    runtime: RuntimeSettings = Depends(get_runtime_settings),
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["setting:update"]
    ),
):
    runtime.set(namespace, value)
    return {"message": "Setting updated"}


@router.delete("/settings/{namespace}")
def delete_runtime_setting(
    namespace: str,
    runtime: RuntimeSettings = Depends(get_runtime_settings),
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["setting:delete"]
    ),
):
    runtime.delete(namespace)
    return {"message": "Setting deleted"}
