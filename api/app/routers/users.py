from app.auth.security import get_current_active_user
from app.db.session import get_db
from app.repositories import users as users_repository
from app.schemas import user as user_schemas
from fastapi import APIRouter, Depends, HTTPException, Security, status
from sqlalchemy.orm import Session

router = APIRouter()


@router.get("/users/", response_model=list[user_schemas.User])
def get_users(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(get_current_active_user, scopes=["users:read"]),
):
    return users_repository.get_users(db, skip=skip, limit=limit)


@router.get("/users/me", response_model=user_schemas.User)
def get_current_user(
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(get_current_active_user, scopes=["users:me"]),
):
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not enough permissions"
        )
    return user


@router.get("/users/{user_id}", response_model=user_schemas.User)
def get_user_by_id(
    user_id: int,
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(get_current_active_user, scopes=["users:read"]),
):
    db_user = users_repository.get_user_by_id(db, user_id=user_id)
    if db_user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    return db_user


@router.post(
    "/users/", response_model=user_schemas.User, status_code=status.HTTP_201_CREATED
)
def create_user(
    user_request: user_schemas.UserCreate,
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["users:create"]
    ),
):
    db_user = users_repository.get_user_by_email(db, email=user_request.email)
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered"
        )
    return users_repository.create_user(db=db, user=user_request)


@router.patch("/users/{user_id}", response_model=user_schemas.User)
def update_user(
    user_id: int,
    user: user_schemas.UserUpdate,
    db: Session = Depends(get_db),
    current_user: user_schemas.User = Security(
        get_current_active_user, scopes=["users:update"]
    ),
):
    return users_repository.update_user(db=db, user_id=user_id, user=user)


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["users:delete"]
    ),
):
    return users_repository.delete_user(db=db, user_id=user_id)
