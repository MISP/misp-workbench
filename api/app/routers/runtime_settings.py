from app.auth.security import get_current_active_user
from app.db.session import get_db
from app.services import audit
from app.services.runtime_settings_provider import get_runtime_settings
from app.schemas import user as user_schemas
from fastapi import APIRouter, Security, Depends, Request
from sqlalchemy.orm import Session
from app.services.runtime_settings import RuntimeSettings

router = APIRouter()


def _diff_settings(before, after) -> dict:
    """Shallow diff of two setting values. Reports added/removed/changed keys
    when both sides are dicts; falls back to a before/after snapshot otherwise.
    """
    if before is None:
        return {"added": after}
    if not isinstance(before, dict) or not isinstance(after, dict):
        return {"before": before, "after": after}

    added = {k: after[k] for k in after if k not in before}
    removed = {k: before[k] for k in before if k not in after}
    changed = {
        k: {"before": before[k], "after": after[k]}
        for k in after
        if k in before and before[k] != after[k]
    }
    diff = {}
    if added:
        diff["added"] = added
    if removed:
        diff["removed"] = removed
    if changed:
        diff["changed"] = changed
    return diff


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
    request: Request,
    db: Session = Depends(get_db),
    runtime_settings: RuntimeSettings = Depends(get_runtime_settings),
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["settings:update"]
    ),
):
    previous = runtime_settings.get(namespace)
    runtime_settings.set(namespace, value)
    audit.record(
        db,
        action="runtime_setting.updated",
        resource_type="runtime_setting",
        actor_user_id=user.id,
        request=request,
        metadata={"namespace": namespace, "diff": _diff_settings(previous, value)},
    )
    db.commit()
    return {"message": "Setting updated"}


@router.delete("/settings/runtime/{namespace}")
def delete_runtime_setting(
    namespace: str,
    request: Request,
    db: Session = Depends(get_db),
    runtime_settings: RuntimeSettings = Depends(get_runtime_settings),
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["settings:delete"]
    ),
):
    previous = runtime_settings.get(namespace)
    runtime_settings.delete(namespace)
    audit.record(
        db,
        action="runtime_setting.deleted",
        resource_type="runtime_setting",
        actor_user_id=user.id,
        request=request,
        metadata={"namespace": namespace, "previous": previous},
    )
    db.commit()
    return {"message": "Setting deleted"}
