from ..schemas import user as user_schemas
from ..repositories import users as users_repository
from ..dependencies import get_db
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

router = APIRouter()


@router.get("/users/", response_model=list[user_schemas.User])
def get_users(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    users = users_repository.get_users(db, skip=skip, limit=limit)
    return users


@router.get("/users/{user_id}", response_model=user_schemas.User)
def get_user_by_id(user_id: int, db: Session = Depends(get_db)):
    db_user = users_repository.get_user_by_id(db, user_id=user_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user


@router.post("/users/", response_model=user_schemas.User)
def create_user(user: user_schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = users_repository.get_user_by_email(db, email=user.email)
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    return users_repository.create_user(db=db, user=user)
