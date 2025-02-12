import random
import string
from datetime import datetime, timedelta
from typing import Union

import bcrypt
import jwt
from app.dependencies import get_db
from app.repositories import users as users_repository
from app.schemas import user as user_schemas
from app.settings import Settings, get_settings
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, SecurityScopes
from jwt.exceptions import InvalidTokenError
from pydantic import BaseModel, ValidationError
from sqlalchemy.orm import Session

# see: https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/
# see: https://fastapi.tiangolo.com/advanced/security/


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: str = ""
    scopes: list[str] = []


oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="auth/token",
    scopes={
        "users:me": "Read information about the current user.",
        "items": "Read items.",
        "users:create": "Create users.",
        "users:read": "Read users.",
        "users:update": "Update users.",
        "users:delete": "Delete users.",
        "organisations:create": "Create organisations.",
        "organisations:read": "Read organisations.",
        "organisations:update": "Update organisations.",
        "organisations:delete": "Delete organisations.",
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
        "objects:create": "Create objects.",
        "objects:read": "Read objects.",
        "objects:update": "Update objects.",
        "objects:delete": "Delete objects.",
        "servers:create": "Create servers.",
        "servers:read": "Read servers.",
        "servers:update": "Update servers.",
        "servers:delete": "Delete servers.",
        "servers:pull": "Pull server by id.",
        "servers:test": "Test server connection by id.",
        "servers:index": "Index server events by id.",
        "sharing_groups:create": "Create sharing groups.",
        "sharing_groups:read": "Read sharing groups.",
        "sharing_groups:update": "Update sharing groups.",
        "sharing_groups:delete": "Delete sharing groups.",
        "tags:create": "Create tags.",
        "tags:read": "Read tags.",
        "tags:update": "Update tags.",
        "tags:delete": "Delete tags.",
        "taxonomies:create": "Create taxonomies.",
        "taxonomies:read": "Read taxonomies.",
        "taxonomies:update": "Update taxonomies.",
        "taxonomies:delete": "Delete taxonomies.",
        "modules:read": "Read misp-modules.",
        "modules:update": "Update misp-modules.",
        "modules:query": "Query misp-modules.",
        "feeds:create": "Create feeds.",
        "feeds:read": "Read feeds.",
        "feeds:update": "Update feeds.",
        "feeds:delete": "Delete feeds.",
        "feeds:fetch": "Fetch feeds.",
        "feeds:test": "Test feed connection by id.",
        "galaxies:create": "Create galaxies.",
        "galaxies:read": "Read galaxies.",
        "galaxies:update": "Update galaxies.",
        "galaxies:delete": "Delete galaxies.",
        "attachments:download": "Download attachments.",
        "attachments:upload": "Upload attachments.",
        "attachments:delete": "Delete attachments.",
    },
)


def verify_password(plain_password, hashed_password):
    return bcrypt.checkpw(plain_password.encode(), hashed_password.encode())


def get_password_hash(password):
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def create_access_token(
    data: dict,
    expires_delta: Union[timedelta, None] = None,
    settings: Settings = get_settings(),
):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode, settings.OAuth2.secret_key, algorithm=settings.OAuth2.algorithm
    )
    return encoded_jwt


async def get_current_user(
    security_scopes: SecurityScopes,
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    if security_scopes.scopes:
        authenticate_value = f'Bearer scope="{security_scopes.scope_str}"'
    else:
        authenticate_value = "Bearer"
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": authenticate_value},
    )
    try:
        payload = jwt.decode(
            token, settings.OAuth2.secret_key, algorithms=[settings.OAuth2.algorithm]
        )
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_scopes = payload.get("scopes", [])
        token_data = TokenData(scopes=token_scopes, username=username)
    except (InvalidTokenError, ValidationError):
        raise credentials_exception
    user = users_repository.get_user_by_email(db, email=token_data.username)
    if user is None:
        raise credentials_exception

    if "*" in token_data.scopes:
        # "*" scope is superadmin, so it can access everything
        return user

    for scope in security_scopes.scopes:
        # check if the user has access to the requested scope
        resource = scope.split(":")[0]
        if scope not in token_data.scopes and f"{resource}:*" not in token_data.scopes:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not enough permissions",
                headers={"WWW-Authenticate": authenticate_value},
            )
    return user


async def get_current_active_user(
    current_user: user_schemas.User = Depends(get_current_user),
):
    if current_user.disabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user"
        )
    return current_user


def authenticate_user(db: Session, username: str, password: str):
    user = users_repository.get_user_by_email(db, username)
    if not user:
        return False
    if not verify_password(password, user.hashed_password):
        return False
    return user


def get_scopes_for_user(user: user_schemas.User):
    scopes = set()

    # TODO: review and move these mappings to a config file or database
    # TODO: remove redudant scopes, e.g. ["users:read", "users:*"] -> ["users:*"]

    if user.role.perm_full:
        return ["*"]

    if user.role.perm_admin:
        scopes.add("users:*")
        scopes.add("events:*")
        scopes.add("attributes:*")
        scopes.add("objects:*")
        scopes.add("servers:*")
        scopes.add("roles:*")
        scopes.add("sharing_groups:*")
        scopes.add("tags:*")
        scopes.add("modules:*")
        scopes.add("taxonomies:*")
        scopes.add("galaxies:*")

    if user.role.perm_auth:
        scopes.add("auth:login")

    if user.role.perm_add:
        scopes.add("events:create")
        scopes.add("attributes:create")
        scopes.add("objects:create")
        scopes.add("tags:create")

    if user.role.perm_modify:
        scopes.add("events:update")
        scopes.add("attributes:update")
        scopes.add("objects:update")
        scopes.add("tags:update")

    if user.role.perm_modify_org:
        pass

    if user.role.perm_publish:
        pass

    if user.role.perm_delegate:
        pass

    if user.role.perm_sync:
        pass

    if user.role.perm_admin:
        pass

    if user.role.perm_audit:
        pass

    if user.role.perm_full:
        pass

    if user.role.perm_auth:
        pass

    if user.role.perm_site_admin:
        pass

    if user.role.perm_regexp_access:
        pass

    if user.role.perm_tagger:
        pass

    if user.role.perm_template:
        pass

    if user.role.perm_sharing_group:
        pass

    if user.role.perm_tag_editor:
        pass

    if user.role.perm_sighting:
        pass

    if user.role.perm_object_template:
        pass

    if user.role.perm_galaxy_editor:
        pass

    if user.role.perm_warninglist:
        pass

    if user.role.perm_publish_zmq:
        pass

    if user.role.perm_publish_kafka:
        pass

    if user.role.perm_decaying:
        pass

    return list(scopes)


def get_random_password():
    return "".join(
        random.choice(
            string.ascii_lowercase
            + string.ascii_uppercase
            + string.digits
            + string.punctuation
        )
        for _ in range(12)
    )
