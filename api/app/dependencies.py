from app.database import SessionLocal
from app.opensearch import OpenSearchClient
from app.miniocli import MinioClient
from app.services.runtime_settings import RuntimeSettings
from fastapi import Depends
from sqlalchemy.orm import Session

async def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_opensearch_client():
    return OpenSearchClient

def get_minio_client():
    return MinioClient

def get_runtime_settings(db: Session = Depends(get_db)) -> RuntimeSettings:
    return RuntimeSettings(db)