from app.auth import auth
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer,SecurityScopes
from sqlalchemy.orm import Session
from jwt import decode as jwt_decode
from jwt.exceptions import InvalidTokenError
from pydantic import BaseModel, ValidationError

from app.db.session import get_db
from app.settings import get_settings
from app.repositories import users as users_repository

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")

class TokenData(BaseModel):
    username: str = ""
    scopes: list[str] = []

async def get_current_active_user(
    security_scopes: SecurityScopes,
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
):
    settings = get_settings()
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

    try:
        payload = jwt_decode(
            token, settings.OAuth2.secret_key, algorithms=[settings.OAuth2.algorithm]
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
        token_scopes = payload.get("scopes", [])
        token_data = TokenData(scopes=token_scopes, username=username)
    except (InvalidTokenError, ValidationError):
        raise credentials_exception

    user = users_repository.get_user_by_email(db, email=token_data.username)
    if user is None or user.disabled:
        raise credentials_exception

    if "*" in token_data.scopes:
        return user

    for scope in security_scopes.scopes:
        resource = scope.split(":")[0]
        if scope not in token_data.scopes and f"{resource}:*" not in token_data.scopes:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not enough permissions",
                headers={"WWW-Authenticate": authenticate_value},
            )

    return user
