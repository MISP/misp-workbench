import os
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, sessionmaker

from ...auth import auth
from ...dependencies import get_db
from ...main import app
from ...models import attribute as attribute_models
from ...models import event as event_models
from ...models import object as object_models
from ...models import server as server_models
from ...models import user as user_models


class ApiTest:
    @pytest.fixture(scope="class", name="db")
    def session_fixture(self):
        SQLALCHEMY_DATABASE_URL = "postgresql://{}:{}@{}:{}/{}".format(
            os.environ["POSTGRES_USER"],
            os.environ["POSTGRES_PASSWORD"],
            os.environ["POSTGRES_HOSTNAME"],
            os.environ["POSTGRES_PORT"],
            os.environ["POSTGRES_DATABASE"],
        )

        engine = create_engine(SQLALCHEMY_DATABASE_URL)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
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
    def cleanup(self, db: Session):
        try:
            pass
        finally:
            # teardown
            db.execute("DELETE FROM servers")
            db.execute("DELETE FROM attributes")
            db.execute("DELETE FROM objects")
            db.execute("DELETE FROM events")
            db.execute("DELETE FROM users")
            db.execute("DELETE FROM servers")
            db.commit()

    # MISP data model fixtures
    @pytest.fixture(scope="class")
    def api_tester_user(self, db: Session):
        api_tester_user = user_models.User(
            org_id=1, role_id=3, email="api@tester.local", hashed_password="secret"
        )
        db.add(api_tester_user)
        db.commit()

        return api_tester_user

    @pytest.fixture(scope="class")
    def user_1(self, db: Session):
        user_1 = user_models.User(
            org_id=1, role_id=1, email="foo@bar.com", hashed_password="secret"
        )
        db.add(user_1)
        db.commit()

        return user_1

    @pytest.fixture(scope="class")
    def event_1(self, db: Session, user_1: user_models.User):
        event_1 = event_models.Event(
            info="test event", user_id=user_1.id, orgc_id=1, org_id=1, date="2020-01-01"
        )
        db.add(event_1)
        db.commit()

        return event_1

    @pytest.fixture(scope="class")
    def attribute_1(self, db: Session, event_1: event_models.Event):
        attribute_1 = attribute_models.Attribute(
            event_id=event_1.id,
            category="Network activity",
            type="ip-src",
            value="127.0.0.1",
        )
        db.add(attribute_1)
        db.commit()

        return attribute_1

    @pytest.fixture(scope="class")
    def object_1(self, db: Session, event_1: event_models.Event):
        object_1 = object_models.Object(
            event_id=event_1.id,
            name="test object",
            template_version=0,
            timestamp=0,
            deleted=False,
        )
        db.add(object_1)
        db.commit()

        return object_1

    @pytest.fixture(scope="class")
    def server_1(self, db: Session, event_1: event_models.Event):
        server_1 = server_models.Server(
            name="test server",
            url="http://localhost",
            authkey="JOvupq7Y96531wkWZBrIgbaxqaZIQqaYs9izZJ0g",
            org_id=1,
            remote_org_id=1,
            push=False,
            pull=True,
            push_sightings=False,
            push_galaxy_clusters=False,
            pull_galaxy_clusters=False,
            publish_without_email=True,
            self_signed=True,
            internal=True,
            unpublish_event=False,
            skip_proxy=False,
            caching_enabled=False,
            priority=0,
        )
        db.add(server_1)
        db.commit()

        return server_1

    @pytest.fixture(scope="function")
    def auth_token(
        self, api_tester_user: user_models.User, scopes: list, expires_in: int = 3600
    ):
        access_token_expires = timedelta(seconds=expires_in)
        auth_token = auth.create_access_token(
            data={"sub": api_tester_user.email, "scopes": scopes},
            expires_delta=access_token_expires,
        )

        return auth_token
