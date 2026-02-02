from datetime import timedelta

from app.auth import auth
from app.db.session import get_db
from app.settings import Settings, get_settings
from fastapi import APIRouter, Depends, HTTPException, status, Security
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.schemas import user as user_schemas
from app.auth.security import get_current_active_user

router = APIRouter()


@router.post("/auth/token", response_model=auth.Token)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    user = auth.authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(
        minutes=int(settings.OAuth2.access_token_expire_minutes)
    )
    refresh_token_expires = timedelta(
        minutes=int(settings.OAuth2.refresh_token_expire_days * 24 * 60)
    )

    scopes = auth.get_scopes_for_user(user)
    access_token = auth.create_access_token(
        data={"sub": user.email, "scopes": scopes},
        expires_delta=access_token_expires,
    )
    refresh_token = auth.create_refresh_token(
        data={"sub": user.email, "scopes": scopes},
        expires_delta=refresh_token_expires,
    )
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }


@router.post("/auth/refresh", response_model=auth.Token)
async def refresh_access_token(
    refresh_token: str,
    settings: Settings = Depends(get_settings),
):
    try:
        payload = auth.jwt.decode(
            refresh_token,
            settings.OAuth2.refresh_secret_key,
            algorithms=[settings.OAuth2.algorithm],
        )

        if auth.is_token_revoked(payload):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has been revoked",
                headers={"WWW-Authenticate": "Bearer"},
            )

        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
    except auth.jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(
        minutes=int(settings.OAuth2.access_token_expire_minutes)
    )
    scopes = payload.get("scopes", [])
    access_token = auth.create_access_token(
        data={"sub": username, "scopes": scopes},
        expires_delta=access_token_expires,
    )

    refresh_token_expires = timedelta(
        minutes=int(settings.OAuth2.refresh_token_expire_days * 24 * 60)
    )
    refresh_token = auth.create_refresh_token(
        data={"sub": username, "scopes": scopes},
        expires_delta=refresh_token_expires,
    )

    auth.add_token_to_denylist(payload["jti"])

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "refresh_token": refresh_token,
    }


@router.post("/auth/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout_current_user(
    user: user_schemas.User = Security(get_current_active_user),
    token: str = Depends(auth.oauth2_scheme),
    settings: Settings = Depends(get_settings),
):
    try:
        payload = auth.jwt.decode(
            token,
            settings.OAuth2.secret_key,
            algorithms=[settings.OAuth2.algorithm],
        )
        auth.add_token_to_denylist(payload["jti"])
    except auth.jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )