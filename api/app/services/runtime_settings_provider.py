from fastapi import Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.services.runtime_settings import RuntimeSettings

def get_runtime_settings(db: Session = Depends(get_db)) -> RuntimeSettings:
    return RuntimeSettings(db)