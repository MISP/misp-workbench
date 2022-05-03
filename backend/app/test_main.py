import pytest
import os
from .models import user as user_models
from .dependencies import get_db
from .main import app
from fastapi.testclient import TestClient
from .database import Base, engine
from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker


@pytest.fixture(name="db")
def session_fixture():
    SQLALCHEMY_DATABASE_URL = "postgresql://%s:%s@%s/%s" % (
        os.environ['POSTGRES_USER'],
        os.environ['POSTGRES_PASSWORD'],
        os.environ['POSTGRES_HOSTNAME'],
        os.environ['DATABASE']
    )

    engine = create_engine(SQLALCHEMY_DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base = declarative_base()
    Base.metadata.create_all(bind=engine)

    yield SessionLocal()


@pytest.fixture(name="client")
def client_fixture(db: Session):
    def get_db_override():
        return db

    app.dependency_overrides[get_db] = get_db_override

    client = TestClient(app)
    yield client

    app.dependency_overrides.clear()


@pytest.fixture(scope="function", autouse=True)
def setup_cleanup(db: Session):
    try:
        # setup
        pass
    finally:
        # teardown
        db.execute("DELETE FROM users")
        db.execute("DELETE FROM attributes")
        db.execute("DELETE FROM events")


def test_get_users(db: Session, client: TestClient):
    user_1 = user_models.User(
        email="foo@bar.com",
        hashed_password=""
    )
    db.add(user_1)
    db.commit()

    response = client.get("/users/")
    data = response.json()

    assert response.status_code == 200

    assert len(data) == 1
    assert data[0]["email"] == user_1.email
