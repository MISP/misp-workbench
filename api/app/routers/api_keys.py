from app.auth.auth import AVAILABLE_SCOPES
from app.auth.security import get_current_active_user
from app.auth.utils import role_has_scope
from app.db.session import get_db
from app.repositories import api_keys as api_keys_repository
from app.schemas import api_key as api_key_schemas
from app.schemas import user as user_schemas
from app.services import audit
from fastapi import APIRouter, Depends, HTTPException, Request, Security, status
from sqlalchemy.orm import Session

router = APIRouter()


def _validate_requested_scopes(requested: list[str], user: user_schemas.User) -> None:
    if not requested:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one scope is required.",
        )

    role_scopes = list(user.role.scopes or [])
    unknown = [s for s in requested if s not in AVAILABLE_SCOPES and s != "*"]
    if unknown:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown scopes: {', '.join(unknown)}",
        )
    not_allowed = [s for s in requested if not role_has_scope(role_scopes, s)]
    if not_allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Scopes exceed your role: {', '.join(not_allowed)}",
        )


@router.get("/api-keys/", response_model=list[api_key_schemas.ApiKey])
def list_api_keys(
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["api_keys:read"]
    ),
):
    return api_keys_repository.list_keys_for_user(db, user_id=user.id)


@router.post(
    "/api-keys/",
    response_model=api_key_schemas.ApiKeyCreated,
    status_code=status.HTTP_201_CREATED,
)
def create_api_key(
    key_request: api_key_schemas.ApiKeyCreate,
    request: Request,
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["api_keys:create"]
    ),
):
    _validate_requested_scopes(key_request.scopes, user)

    db_key, raw_token = api_keys_repository.create_key(
        db,
        user_id=user.id,
        name=key_request.name,
        scopes=key_request.scopes,
        comment=key_request.comment,
        expires_at=key_request.expires_at,
    )
    audit.record(
        db,
        action="api_key.created",
        resource_type="api_key",
        resource_id=db_key.id,
        actor_user_id=user.id,
        request=request,
        metadata={
            "name": db_key.name,
            "scopes": list(db_key.scopes or []),
            "expires_at": db_key.expires_at.isoformat() if db_key.expires_at else None,
        },
    )
    db.commit()
    return api_key_schemas.ApiKeyCreated(
        **api_key_schemas.ApiKey.model_validate(db_key).model_dump(),
        token=raw_token,
    )


@router.patch("/api-keys/{key_id}", response_model=api_key_schemas.ApiKey)
def update_api_key(
    key_id: int,
    payload: api_key_schemas.ApiKeyUpdate,
    request: Request,
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["api_keys:update"]
    ),
):
    db_key = api_keys_repository.get_key_by_id(db, key_id=key_id, user_id=user.id)
    if db_key is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="API key not found"
        )
    was_disabled = db_key.disabled
    updated = api_keys_repository.set_disabled(db, db_key, payload.disabled)
    if was_disabled != updated.disabled:
        audit.record(
            db,
            action="api_key.disabled" if updated.disabled else "api_key.enabled",
            resource_type="api_key",
            resource_id=updated.id,
            actor_user_id=user.id,
            request=request,
        )
        db.commit()
    return updated


@router.delete("/api-keys/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_api_key(
    key_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["api_keys:delete"]
    ),
):
    db_key = api_keys_repository.get_key_by_id(db, key_id=key_id, user_id=user.id)
    if db_key is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="API key not found"
        )
    if db_key.admin_disabled:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "This API key has been locked by an administrator and cannot "
                "be deleted. Contact an administrator to unlock or delete it."
            ),
        )
    key_snapshot = {"id": db_key.id, "name": db_key.name}
    api_keys_repository.delete_key(db, db_key)
    audit.record(
        db,
        action="api_key.deleted",
        resource_type="api_key",
        resource_id=key_snapshot["id"],
        actor_user_id=user.id,
        request=request,
        metadata={"name": key_snapshot["name"]},
    )
    db.commit()


@router.get("/admin/api-keys/", response_model=list[api_key_schemas.ApiKey])
def admin_list_api_keys(
    user_id: int | None = None,
    db: Session = Depends(get_db),
    _admin: user_schemas.User = Security(
        get_current_active_user, scopes=["api_keys:admin"]
    ),
):
    return api_keys_repository.list_keys_admin(db, user_id=user_id)


@router.patch("/admin/api-keys/{key_id}", response_model=api_key_schemas.ApiKey)
def admin_update_api_key(
    key_id: int,
    payload: api_key_schemas.ApiKeyUpdate,
    request: Request,
    db: Session = Depends(get_db),
    admin: user_schemas.User = Security(
        get_current_active_user, scopes=["api_keys:admin"]
    ),
):
    db_key = api_keys_repository.get_key_by_id(db, key_id=key_id)
    if db_key is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="API key not found"
        )
    # The `disabled` field in the request body controls the admin hold; the
    # owner's own `disabled` flag is independent and not touched here.
    was_admin_disabled = db_key.admin_disabled
    target_user_id = db_key.user_id
    updated = api_keys_repository.set_admin_disabled(db, db_key, payload.disabled)
    if was_admin_disabled != updated.admin_disabled:
        audit.record(
            db,
            action=(
                "api_key.admin_locked"
                if updated.admin_disabled
                else "api_key.admin_unlocked"
            ),
            resource_type="api_key",
            resource_id=updated.id,
            actor_user_id=admin.id,
            request=request,
            metadata={"target_user_id": target_user_id},
        )
        db.commit()
    return updated


@router.delete("/admin/api-keys/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
def admin_delete_api_key(
    key_id: int,
    request: Request,
    db: Session = Depends(get_db),
    admin: user_schemas.User = Security(
        get_current_active_user, scopes=["api_keys:admin"]
    ),
):
    db_key = api_keys_repository.get_key_by_id(db, key_id=key_id)
    if db_key is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="API key not found"
        )
    snapshot = {
        "id": db_key.id,
        "name": db_key.name,
        "target_user_id": db_key.user_id,
    }
    api_keys_repository.delete_key(db, db_key)
    audit.record(
        db,
        action="api_key.admin_deleted",
        resource_type="api_key",
        resource_id=snapshot["id"],
        actor_user_id=admin.id,
        request=request,
        metadata={
            "name": snapshot["name"],
            "target_user_id": snapshot["target_user_id"],
        },
    )
    db.commit()
