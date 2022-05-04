import pytest
import os
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from ..models import user as user_models
from ..models import event as event_models
from ..models import attribute as attribute_models
from ..dependencies import get_db
from ..main import app
from ..database import Base, engine


class ApiTest:

    @pytest.fixture(scope="class", name="db")
    def session_fixture(self):
        SQLALCHEMY_DATABASE_URL = "postgresql://%s:%s@%s/%s" % (
            os.environ['POSTGRES_USER'],
            os.environ['POSTGRES_PASSWORD'],
            os.environ['POSTGRES_HOSTNAME'],
            os.environ['DATABASE']
        )

        engine = create_engine(SQLALCHEMY_DATABASE_URL)
        SessionLocal = sessionmaker(
            autocommit=False, autoflush=False, bind=engine)
        Base = declarative_base()
        Base.metadata.create_all(bind=engine)

        yield SessionLocal()

    @pytest.fixture(scope="class", name="client")
    def client_fixture(self, db: Session):
        def get_db_override():
            return db

        app.dependency_overrides[get_db] = get_db_override

        client = TestClient(app)
        yield client

        app.dependency_overrides.clear()

    @pytest.fixture(scope="class", autouse=True)
    def setup_cleanup(self, db: Session):
        try:
            # setup
            pass
        finally:
            # teardown
            db.execute("DELETE FROM attributes")
            db.execute("DELETE FROM events")
            db.execute("DELETE FROM users")
            db.commit()

    # MISP data model fixtures

    @pytest.fixture(scope="class")
    def user_1(self, db: Session):
        user_1 = user_models.User(
            id=1,
            email="foo@bar.com",
            hashed_password="secret"
        )
        db.add(user_1)
        db.commit()

        return user_1

    @pytest.fixture(scope="class")
    def event_1(self, db: Session, user_1: user_models.User):
        event_1 = event_models.Event(
            id=1,
            info="test event",
            user_id=user_1.id,
            orgc_id=1,
            org_id=1,
            date="2020-01-01"
        )
        db.add(event_1)
        db.commit()

        return event_1

    @pytest.fixture(scope="class")
    def attribute_1(self, db: Session, event_1: event_models.Event):
        attribute_1 = attribute_models.Attribute(
            id=1,
            event_id=event_1.id,
            category="Network activity",
            type="ip-src",
            value1="127.0.0.1"
        )
        db.add(attribute_1)
        db.commit()

        return attribute_1
