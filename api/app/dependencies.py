from app.database import SessionLocal
from app.opensearch import OpenSearchClient
from app.miniocli import MinioClient


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