from fastapi import Depends, HTTPException, status, Security
from fastapi.security import OAuth2PasswordBearer, SecurityScopes
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import Union, List
from pydantic import BaseModel, ValidationError
from jose import JWTError, jwt
from passlib.context import CryptContext
from datetime import datetime, timedelta
from ..repositories import users as users_repository
from ..dependencies import get_db
from ..schemas import user as user_schemas
from ..config import Settings, get_settings


# see: https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/
# see: https://fastapi.tiangolo.com/advanced/security/

class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: Union[str, None] = None
    scopes: List[str] = []


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="auth/token",
    scopes={
        "users:me": "Read information about the current user.", "items": "Read items.",
        "users:create": "Create users.",
        "users:read": "Read users.",
        "users:update": "Update users.",
        "users:delete": "Delete users.",
        "roles:create": "Create roles.",
        "roles:read": "Read roles.",
        "roles:update": "Update roles.",
        "roles:delete": "Delete roles.",
        "events:create": "Create events.",
        "events:read": "Read events.",
        "events:update": "Update events.",
        "events:delete": "Delete events.",
        "attributes:create": "Create attributes.",
        "attributes:read": "Read attributes.",
        "attributes:update": "Update attributes.",
        "attributes:delete": "Delete attributes.",
        "servers:create": "Create servers.",
        "servers:read": "Read servers.",
        "servers:update": "Update servers.",
        "servers:delete": "Delete servers.",
        "servers:pull": "Pull server by id.",

    }
)


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Union[timedelta, None] = None, config: Settings = Depends(get_settings)):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, config.OAuth2.secret_key, algorithm=config.OAuth2.algorithm)
    return encoded_jwt


async def get_current_user(security_scopes: SecurityScopes, token: str = Depends(oauth2_scheme), db: Session = Depends(get_db), config: Settings = Depends(get_settings)):
    if security_scopes.scopes:
        authenticate_value = f'Bearer scope="{security_scopes.scope_str}"'
    else:
        authenticate_value = f"Bearer"
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": authenticate_value},
    )
    try:
        payload = jwt.decode(token, config.OAuth2.secret_key, algorithms=[config.OAuth2.algorithm])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_scopes = payload.get("scopes", [])
        token_data = TokenData(scopes=token_scopes, username=username)
    except (JWTError, ValidationError):
        raise credentials_exception
    user = users_repository.get_user_by_email(db, email=token_data.username)
    if user is None:
        raise credentials_exception
    for scope in security_scopes.scopes:
        if scope not in token_data.scopes:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not enough permissions",
                headers={"WWW-Authenticate": authenticate_value},
            )
    return user


async def get_current_active_user(current_user: user_schemas.User = Depends(get_current_user)):
    if current_user.disabled:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user")
    return current_user


def authenticate_user(db: Session, username: str, password: str):
    user = users_repository.get_user_by_email(db, username)
    if not user:
        return False
    if not verify_password(password, user.hashed_password):
        return False
    return user
