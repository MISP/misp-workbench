from ..dependencies import get_db
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordRequestForm
from datetime import timedelta
from ..auth import auth
from ..config import Settings, get_settings

router = APIRouter()


@router.post("/auth/token", response_model=auth.Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db), config: Settings = Depends(get_settings)):
    user = auth.authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=int(config.OAuth2.access_token_expire_minutes))
    access_token = auth.create_access_token(
        data={"sub": user.email, "scopes": ["users:me", "users:read"]},  # TODO: get scopes from db based on role
        expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}
