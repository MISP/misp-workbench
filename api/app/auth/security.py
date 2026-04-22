import re
from datetime import datetime, timedelta, timezone

from app.auth import auth
from app.auth.utils import role_has_scope
from app.db.session import get_db
from app.repositories import api_keys as api_keys_repository
from app.repositories import users as users_repository
from app.settings import get_settings
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer, SecurityScopes
from fastapi.security.utils import get_authorization_scheme_param
from jwt import decode as jwt_decode
from jwt.exceptions import InvalidTokenError
from pydantic import BaseModel, ValidationError
from sqlalchemy.orm import Session

# Declared so FastAPI/OpenAPI still documents the OAuth2 scheme; parsing is done manually below.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token", auto_error=False)

_LAST_USED_DEBOUNCE = timedelta(minutes=1)

# MISP-style raw API key: 40 lowercase hex chars (see TOKEN_BYTES in repositories/api_keys.py).
_RAW_API_KEY_RE = re.compile(r"^[0-9a-f]{40}$")


class TokenData(BaseModel):
    username: str = ""
    scopes: list[str] = []


def _extract_token(authorization: str | None) -> str | None:
    if not authorization:
        return None
    scheme, param = get_authorization_scheme_param(authorization)
    if scheme and scheme.lower() == "bearer":
        return param or None
    # MISP-style: the raw token is sent as the whole Authorization value
    # (no scheme, no whitespace). Only accept the recognized 40-hex format
    # to avoid misinterpreting other schemes (e.g. Basic <creds>) as tokens.
    if scheme and not param and _RAW_API_KEY_RE.match(scheme):
        return scheme
    return None


def _looks_like_jwt(token: str) -> bool:
    return token.count(".") == 2


def _check_scopes(
    granted_scopes: list[str],
    required_scopes: list[str],
    authenticate_value: str,
) -> None:
    if "*" in granted_scopes:
        return
    for scope in required_scopes:
        if not role_has_scope(granted_scopes, scope):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not enough permissions",
                headers={"WWW-Authenticate": authenticate_value},
            )


def _authenticate_jwt(
    token: str,
    db: Session,
    security_scopes: SecurityScopes,
    authenticate_value: str,
    credentials_exception: HTTPException,
):
    settings = get_settings()
    try:
        payload = jwt_decode(
            token,
            settings.OAuth2.secret_key,
            algorithms=[settings.OAuth2.algorithm],
        )
        if auth.is_token_revoked(payload):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has been revoked",
                headers={"WWW-Authenticate": authenticate_value},
            )
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(
            scopes=payload.get("scopes", []), username=username
        )
    except (InvalidTokenError, ValidationError):
        raise credentials_exception

    user = users_repository.get_user_by_email(db, email=token_data.username)
    if user is None or user.disabled:
        raise credentials_exception

    _check_scopes(token_data.scopes, security_scopes.scopes, authenticate_value)
    return user


def _authenticate_api_key(
    token: str,
    db: Session,
    security_scopes: SecurityScopes,
    authenticate_value: str,
    credentials_exception: HTTPException,
):
    db_key = api_keys_repository.get_key_by_token(db, token)
    if db_key is None or db_key.disabled:
        raise credentials_exception

    if db_key.expires_at is not None and db_key.expires_at < datetime.now(timezone.utc):
        raise credentials_exception

    user = db_key.user
    if user is None or user.disabled:
        raise credentials_exception

    # A key cannot grant more than its owner's role permits, so check both.
    role_scopes = list(user.role.scopes or [])
    _check_scopes(role_scopes, security_scopes.scopes, authenticate_value)
    _check_scopes(list(db_key.scopes or []), security_scopes.scopes, authenticate_value)

    now = datetime.now(timezone.utc)
    if db_key.last_used_at is None or (now - db_key.last_used_at) > _LAST_USED_DEBOUNCE:
        try:
            api_keys_repository.touch_last_used(db, db_key)
        except Exception:
            db.rollback()

    return user


async def get_current_active_user(
    security_scopes: SecurityScopes,
    request: Request,
    _token: str | None = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
):
    authenticate_value = (
        f'Bearer scope="{security_scopes.scope_str}"'
        if security_scopes.scopes
        else "Bearer"
    )

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": authenticate_value},
    )

    token = _extract_token(request.headers.get("Authorization"))
    if not token:
        raise credentials_exception

    if _looks_like_jwt(token):
        return _authenticate_jwt(
            token, db, security_scopes, authenticate_value, credentials_exception
        )

    return _authenticate_api_key(
        token, db, security_scopes, authenticate_value, credentials_exception
    )
