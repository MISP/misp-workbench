import os
from datetime import timedelta

import pytest
from app.auth import auth
from app.dependencies import get_db
from app.main import app
from app.models import attribute as attribute_models
from app.models import event as event_models
from app.models import object as object_models
from app.models import object_reference as object_reference_models
from app.models import organisations as organisation_models
from app.models import server as server_models
from app.models import sharing_groups as sharing_groups_models
from app.models import user as user_models
from app.settings import get_settings
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, sessionmaker


class ApiTester:
    @pytest.fixture(scope="class")
    def db(self):
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

    @pytest.fixture(scope="class")
    def client(self, db: Session):
        def get_db_override():
            return db

        app.dependency_overrides[get_db] = get_db_override

        client = TestClient(app)
        yield client

        app.dependency_overrides.clear()

    @pytest.fixture(scope="class")
    def settings(self):
        yield get_settings()

    def teardown_db(self, db: Session):
        db.query(attribute_models.Attribute).delete()
        db.query(object_reference_models.ObjectReference).delete()
        db.query(object_models.Object).delete()
        db.query(event_models.Event).delete()
        db.query(sharing_groups_models.SharingGroupOrganisation).delete()
        db.query(sharing_groups_models.SharingGroupServer).delete()
        db.query(sharing_groups_models.SharingGroup).delete()
        db.query(server_models.Server).delete()
        db.query(user_models.User).delete()
        db.query(organisation_models.Organisation).delete()

    @pytest.fixture(scope="class", autouse=True)
    def cleanup(self, db: Session):
        try:
            pass
        finally:
            # teardown
            self.teardown_db(db)

    # MISP data model fixtures

    @pytest.fixture(scope="class")
    def api_tester_user(
        self, db: Session, organisation_1: organisation_models.Organisation
    ):
        api_tester_user = user_models.User(
            org_id=organisation_1.id,
            role_id=3,
            email="api@tester.local",
            hashed_password="secret",
        )
        db.add(api_tester_user)
        db.commit()
        db.refresh(api_tester_user)

        yield api_tester_user

    @pytest.fixture(scope="class")
    def organisation_1(self, db: Session):
        organisation_1 = organisation_models.Organisation(
            name="test organisation",
            date_created="2020-01-01 01:01:01",
            date_modified="2020-01-01 01:01:01",
            type="test",
            sector="test",
            nationality="test",
            created_by=1,
            local=False,
        )
        db.add(organisation_1)
        db.commit()
        db.refresh(organisation_1)

        yield organisation_1

    @pytest.fixture(scope="class")
    def user_1(self, db: Session, organisation_1: organisation_models.Organisation):
        user_1 = user_models.User(
            org_id=organisation_1.id,
            role_id=1,
            email="foo@bar.com",
            hashed_password="secret",
        )
        db.add(user_1)
        db.commit()
        db.refresh(user_1)

        yield user_1

    @pytest.fixture(scope="class")
    def event_1(
        self,
        db: Session,
        organisation_1: organisation_models.Organisation,
        user_1: user_models.User,
    ):
        event_1 = event_models.Event(
            info="test event",
            user_id=user_1.id,
            orgc_id=1,
            org_id=organisation_1.id,
            date="2020-01-01",
        )
        db.add(event_1)
        db.commit()
        db.refresh(event_1)

        yield event_1

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
        db.refresh(attribute_1)

        yield attribute_1

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
        db.refresh(object_1)

        yield object_1

    @pytest.fixture(scope="class")
    def server_1(self, db: Session, organisation_1: organisation_models.Organisation):
        server_1 = server_models.Server(
            name="test server",
            url="http://localhost",
            authkey="JOvupq7Y96531wkWZBrIgbaxqaZIQqaYs9izZJ0g",
            org_id=organisation_1.id,
            remote_org_id=1,
            push=False,
            pull=True,
            push_sightings=False,
            push_galaxy_clusters=False,
            pull_galaxy_clusters=False,
            publish_without_email=True,
            self_signed=True,
            internal=False,
            unpublish_event=False,
            skip_proxy=False,
            caching_enabled=False,
            priority=0,
        )
        db.add(server_1)
        db.commit()
        db.refresh(server_1)

        yield server_1

    @pytest.fixture(scope="class")
    def sharing_group_1(
        self, db: Session, organisation_1: organisation_models.Organisation
    ):
        sharing_group_1 = sharing_groups_models.SharingGroup(
            name="test sharing group",
            releasability="releasability",
            description="description",
            uuid="04750a80-3c22-432b-a016-8c743385b696",
            organisation_uuid=organisation_1.uuid,
            org_id=organisation_1.id,
            sync_user_id=None,
            active=True,
            local=False,
            roaming=False,
            created="2020-01-01 01:01:01",
            modified="2020-01-01 01:01:01",
        )
        db.add(sharing_group_1)
        db.commit()
        db.refresh(sharing_group_1)

        yield sharing_group_1

    @pytest.fixture(scope="class")
    def sharing_group_2(
        self, db: Session, organisation_1: organisation_models.Organisation
    ):
        sharing_group_2 = sharing_groups_models.SharingGroup(
            name="test sharing group (for delete)",
            releasability="releasability",
            description="description",
            uuid="04750a80-3c22-432b-a016-8c743385b695",
            organisation_uuid=organisation_1.uuid,
            org_id=organisation_1.id,
            sync_user_id=None,
            active=True,
            local=False,
            roaming=False,
            created="2020-01-01 01:01:01",
            modified="2020-01-01 01:01:01",
        )
        db.add(sharing_group_2)
        db.commit()
        db.refresh(sharing_group_2)

        yield sharing_group_2

    @pytest.fixture(scope="function")
    def auth_token(
        self, api_tester_user: user_models.User, scopes: list, expires_in: int = 3600
    ):
        access_token_expires = timedelta(seconds=expires_in)
        auth_token = auth.create_access_token(
            data={"sub": api_tester_user.email, "scopes": scopes},
            expires_delta=access_token_expires,
        )

        yield auth_token
