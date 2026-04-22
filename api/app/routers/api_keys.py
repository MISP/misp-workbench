from app.auth.auth import AVAILABLE_SCOPES
from app.auth.security import get_current_active_user
from app.auth.utils import role_has_scope
from app.db.session import get_db
from app.repositories import api_keys as api_keys_repository
from app.schemas import api_key as api_key_schemas
from app.schemas import user as user_schemas
from fastapi import APIRouter, Depends, HTTPException, Security, status
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
    return api_key_schemas.ApiKeyCreated(
        **api_key_schemas.ApiKey.model_validate(db_key).model_dump(),
        token=raw_token,
    )


@router.patch("/api-keys/{key_id}", response_model=api_key_schemas.ApiKey)
def update_api_key(
    key_id: int,
    payload: api_key_schemas.ApiKeyUpdate,
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
    return api_keys_repository.set_disabled(db, db_key, payload.disabled)


@router.delete("/api-keys/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_api_key(
    key_id: int,
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
    api_keys_repository.delete_key(db, db_key)
