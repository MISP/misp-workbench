from app.database import SessionLocal
from app.opensearch import OpenSearchClient


async def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_opensearch_client():
    return OpenSearchClient
