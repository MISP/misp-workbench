from app.schemas import user as user_schemas
from app.services.runtime_settings import RuntimeSettings
from app.services.user_settings import UserSettings
from fastapi import Depends
from sqlalchemy.orm import Session
from app.auth.security import get_current_active_user
from app.schemas import user as user_schemas
from fastapi import Security, Depends
from app.db.session import get_db
from app.services.runtime_settings_provider import get_runtime_settings

def get_user_settings(
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["user_settings:read"]
    ),
    db: Session = Depends(get_db),
    runtime_settings: RuntimeSettings = Depends(get_runtime_settings),
) -> UserSettings:
    return UserSettings(db, user.id, runtime_settings)