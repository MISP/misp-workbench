import os
from datetime import timedelta

import pytest
from app.auth import auth
from app.db.session import get_db
from app.main import app
from app.models import event as event_models
from app.models import feed as feed_models
from app.models import galaxy as galaxy_models
from app.models import hunt as hunt_models
from app.models import module as module_models
from app.models import organisation as organisation_models
from app.models import server as server_models
from app.models import sharing_groups as sharing_groups_models
from app.models import tag as tag_models
from app.models import notification as notification_models
from app.models import taxonomy as taxonomy_models
from app.models import user as user_models
from app.models import role as role_models
from app.settings import get_settings
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker
import sys


class ApiTester:
    @pytest.fixture(scope="class")
    def db(self):
        SQLALCHEMY_DATABASE_URL = "postgresql://{}:{}@{}:{}/{}".format(
            os.environ["POSTGRES_USER"],
            os.environ["POSTGRES_PASSWORD"],
            os.environ["POSTGRES_HOSTNAME"],
            os.environ["POSTGRES_PORT"],
            os.environ["POSTGRES_DB"],
        )

        engine = create_engine(SQLALCHEMY_DATABASE_URL)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        Base = declarative_base()
        Base.metadata.create_all(bind=engine)

        db = SessionLocal()
        yield db
        db.close()

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
        db.query(galaxy_models.GalaxyElement).delete(synchronize_session=False)
        db.query(galaxy_models.GalaxyClusterRelationTag).delete(synchronize_session=False)
        db.query(galaxy_models.GalaxyClusterRelation).delete(synchronize_session=False)
        db.query(galaxy_models.GalaxyCluster).delete(synchronize_session=False)
        db.query(galaxy_models.Galaxy).delete(synchronize_session=False)
        db.query(feed_models.Feed).delete(synchronize_session=False)
        db.query(tag_models.Tag).delete(synchronize_session=False)
        db.query(sharing_groups_models.SharingGroupOrganisation).delete(synchronize_session=False)
        db.query(sharing_groups_models.SharingGroupServer).delete(synchronize_session=False)
        db.query(sharing_groups_models.SharingGroup).delete(synchronize_session=False)
        db.query(server_models.Server).delete(synchronize_session=False)
        db.query(hunt_models.HuntRunHistory).delete(synchronize_session=False)
        db.query(hunt_models.Hunt).delete(synchronize_session=False)
        db.query(notification_models.Notification).delete(synchronize_session=False)
        db.query(user_models.User).delete(synchronize_session=False)
        db.query(module_models.ModuleSettings).delete(synchronize_session=False)
        db.query(taxonomy_models.TaxonomyEntry).delete(synchronize_session=False)
        db.query(taxonomy_models.TaxonomyPredicate).delete(synchronize_session=False)
        db.query(taxonomy_models.Taxonomy).delete(synchronize_session=False)
        db.query(organisation_models.Organisation).delete(synchronize_session=False)
        db.commit()

    @pytest.fixture(scope="class", autouse=True)
    def cleanup(self, db: Session):
        try:
            pass
        finally:
            # clean OpenSearch docs left over from previous test classes
            try:
                from app.services.opensearch import get_opensearch_client

                os_client = get_opensearch_client()
                for index in ("misp-events", "misp-attributes", "misp-objects"):
                    try:
                        os_client.delete_by_query(
                            index=index,
                            body={"query": {"match_all": {}}},
                            refresh=True,
                            ignore=[404],
                        )
                    except Exception as exc:
                        print(
                            f"Warning: failed to delete OpenSearch documents for index '{index}': {exc}",
                            file=sys.stderr,
                        )
            except Exception as exc:
                print(
                    f"Warning: OpenSearch cleanup skipped due to error: {exc}",
                    file=sys.stderr,
                )
            self.teardown_db(db)

    # MISP data model fixtures
    @pytest.fixture(scope="class")
    def role_10(self, db):
        role = role_models.Role(
            id=10,
            name="test role",
            scopes=["events:read", "attributes:read"],
            default_role=False,
        )
        db.add(role)
        db.commit()
        db.refresh(role)
        yield role

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
            uuid="816e8f93-f169-49c1-bf15-efe2ab3211c8",
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
        from datetime import datetime
        from uuid import UUID
        from app.repositories import events as events_repository
        from app.schemas import event as event_schemas

        event_create = event_schemas.EventCreate(
            info="test event",
            user_id=user_1.id,
            orgc_id=1,
            org_id=organisation_1.id,
            date=datetime(2020, 1, 1),
            uuid=UUID("ba4b11b6-dcce-4315-8fd0-67b69160ea76"),
            timestamp=1577836800,
        )
        event_1 = events_repository.create_event(db=db, event=event_create)

        yield event_1

    @pytest.fixture(scope="class")
    def attribute_1(self, db: Session, event_1):
        from uuid import UUID
        from app.repositories import attributes as attributes_repository
        from app.schemas import attribute as attribute_schemas

        attr_create = attribute_schemas.AttributeCreate(
            category="Network activity",
            type="ip-src",
            value="127.0.0.1",
            uuid=UUID("7f2fd15d-3c63-47ba-8a39-2c4b0b3314b0"),
            timestamp=157783680,
            event_uuid=event_1.uuid,
            deleted=False,
            to_ids=False,
            disable_correlation=False,
        )
        yield attributes_repository.create_attribute(db, attr_create)

    @pytest.fixture(scope="class")
    def object_1(self, db: Session, event_1):
        from datetime import datetime
        from uuid import UUID as _UUID
        from app.services.opensearch import get_opensearch_client

        obj_uuid = "90e06ef6-26f8-40dd-9fb7-75897445e2a0"
        obj_doc = {
            "uuid": obj_uuid,
            "event_uuid": str(event_1.uuid),
            "name": "test object",
            "meta_category": None,
            "template_uuid": None,
            "template_version": 0,
            "timestamp": 1577836800,
            "@timestamp": datetime.fromtimestamp(1577836800).isoformat(),
            "deleted": False,
            "distribution": 0,
            "sharing_group_id": None,
            "first_seen": None,
            "last_seen": None,
            "comment": "",
            "object_references": [],
        }

        client = get_opensearch_client()
        client.index(index="misp-objects", id=obj_uuid, body=obj_doc, refresh=True)

        from app.schemas import object as object_schemas
        yield object_schemas.Object.model_validate(obj_doc)

    @pytest.fixture(scope="class")
    def object_attribute_1(
        self, db: Session, event_1, object_1
    ):
        from uuid import UUID
        from app.repositories import attributes as attributes_repository
        from app.schemas import attribute as attribute_schemas
        from app.services.opensearch import get_opensearch_client

        attr_create = attribute_schemas.AttributeCreate(
            category="Network activity",
            type="ip-src",
            value="127.0.0.2",
            uuid=UUID("1355e435-aa0f-4f06-acd3-b44498131e82"),
            timestamp=1577836800,
            event_uuid=event_1.uuid,
            deleted=False,
        )
        object_attribute_1 = attributes_repository.create_attribute(db, attr_create)

        get_opensearch_client().update(
            index="misp-attributes",
            id=str(object_attribute_1.uuid),
            body={"doc": {"object_uuid": str(object_1.uuid)}},
            refresh=True,
        )

        yield object_attribute_1

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

    @pytest.fixture(scope="class")
    def tlp_white_tag(
        self,
        db: Session,
        organisation_1: organisation_models.Organisation,
        user_1: user_models.User,
    ):
        tlp_white_tag = tag_models.Tag(
            name="tlp:white",
            colour="#FFFFFF",
            exportable=True,
            org_id=organisation_1.id,
            user_id=user_1.id,
            hide_tag=False,
            numerical_value=0,
            is_galaxy=False,
            is_custom_galaxy=False,
            local_only=False,
        )
        db.add(tlp_white_tag)
        db.commit()
        db.refresh(tlp_white_tag)

        yield tlp_white_tag

    @pytest.fixture(scope="class")
    def module_1_settings(self, db: Session):
        module_1_settings = module_models.ModuleSettings(
            module_name="mmdb_lookup",
            created="2020-01-01 01:01:01",
            modified="2020-01-01 01:01:01",
            enabled=True,
            config={},
        )
        db.add(module_1_settings)
        db.commit()
        db.refresh(module_1_settings)

        yield module_1_settings

    @pytest.fixture(scope="class")
    def feed_1(self, db: Session, organisation_1: organisation_models.Organisation):
        feed_1 = feed_models.Feed(
            name="test feed",
            provider="test",
            url="http://localhost/test-feed",
            rules=None,
            enabled=True,
            distribution=event_models.DistributionLevel.ORGANISATION_ONLY,
            sharing_group_id=None,
            tag_id=None,
            default=False,
            source_format="misp",
            fixed_event=False,
            delta_merge=False,
            event_uuid=None,
            publish=False,
            override_ids=False,
            settings=None,
            input_source="network",
            delete_local_file=False,
            lookup_visible=False,
            headers=None,
            caching_enabled=False,
            force_to_ids=False,
            orgc_id=organisation_1.id,
            tag_collection_id=None,
            cached_elements=0,
            coverage_by_other_feeds=0,
        )
        db.add(feed_1)
        db.commit()
        db.refresh(feed_1)

        yield feed_1

    @pytest.fixture(scope="class")
    def tlp_taxonomy(
        self,
        db: Session,
        organisation_1: organisation_models.Organisation,
        user_1: user_models.User,
    ):
        tlp_taxonomy = taxonomy_models.Taxonomy(
            namespace="tlp",
            description="Traffic Light Protocol",
            version=1,
            enabled=True,
            exclusive=True,
            required=False,
            highlighted=False,
        )

        db.add(tlp_taxonomy)
        db.commit()
        db.refresh(tlp_taxonomy)

        yield tlp_taxonomy

    @pytest.fixture(scope="class")
    def tlp_white_predicate(
        self,
        db: Session,
        organisation_1: organisation_models.Organisation,
        user_1: user_models.User,
        tlp_taxonomy: taxonomy_models.Taxonomy,
    ):

        tlp_white_predicate = taxonomy_models.TaxonomyPredicate(
            taxonomy_id=tlp_taxonomy.id,
            value="white",
            expanded="(TLP:WHITE) Information can be shared publicly in accordance with the law.",
            colour="#FFFFFF",
            description="Disclosure is not limited.  Sources may use TLP:WHITE when information carries minimal or no foreseeable risk of misuse, in accordance with applicable rules and procedures for public release. Subject to standard copyright rules, TLP:WHITE information may be distributed without restriction. The version 2.0 of TLP doesn't mention anymore this tag which is most probably compatible with new TLP:CLEAR tag.",
        )

        db.add(tlp_white_predicate)
        db.commit()
        db.refresh(tlp_white_predicate)

        yield tlp_white_predicate

    @pytest.fixture(scope="class")
    def threat_actor_galaxy(
        self,
        db: Session,
        organisation_1: organisation_models.Organisation,
        user_1: user_models.User,
    ):
        threat_actor_galaxy = galaxy_models.Galaxy(
            name="Threat Actor",
            type="threat-actor",
            description="Threat actors are characteristics of malicious actors (or adversaries) representing a cyber attack threat including presumed intent and historically observed behaviour.",
            version=3,
            namespace="misp",
            icon="user-secret",
            enabled=True,
            local_only=False,
            default=False,
            org_id=organisation_1.id,
            orgc_id=organisation_1.id,
            created="2020-01-01 01:01:01",
            modified="2020-01-01 01:01:01",
        )

        db.add(threat_actor_galaxy)
        db.commit()
        db.refresh(threat_actor_galaxy)

        yield threat_actor_galaxy

    @pytest.fixture(scope="class")
    def threat_actor_galaxy_cluster_apt29(
        self,
        db: Session,
        organisation_1: organisation_models.Organisation,
        user_1: user_models.User,
        threat_actor_galaxy: galaxy_models.Galaxy,
    ):

        threat_actor_galaxy_cluster_apt29 = galaxy_models.GalaxyCluster(
            collection_uuid="7cdff317-a673-4474-84ec-4f1754947823",
            type="threat-actor",
            value="APT29",
            tag_name='misp-galaxy:threat-actor="APT29"',
            description="APT29 description.",
            galaxy_id=threat_actor_galaxy.id,
            source="MISP Project",
            authors=[
                "Author 1",
                "Author 2",
            ],
            version=1,
            uuid="b2056ff0-00b9-482e-b11c-c771daa5f28a",
            distribution=event_models.DistributionLevel.ALL_COMMUNITIES,
            sharing_group_id=None,
            org_id=organisation_1.id,
            orgc_id=organisation_1.id,
            published=True,
        )

        db.add(threat_actor_galaxy_cluster_apt29)
        db.commit()
        db.refresh(threat_actor_galaxy_cluster_apt29)

        yield threat_actor_galaxy_cluster_apt29

    @pytest.fixture(scope="class")
    def notification_1(self, db: Session, api_tester_user: user_models.User):
        from datetime import datetime

        notification_1 = notification_models.Notification(
            user_id=api_tester_user.id,
            type="event.created",
            entity_type="event",
            entity_uuid="ba4b11b6-dcce-4315-8fd0-67b69160ea76",
            read=False,
            payload={"event_name": "Test Event", "event_uuid": "ba4b11b6-dcce-4315-8fd0-67b69160ea76"},
            created_at=datetime(2024, 1, 1, 0, 0, 0),
        )
        db.add(notification_1)
        db.commit()
        db.refresh(notification_1)

        yield notification_1

    @pytest.fixture(scope="class")
    def hunt_1(self, db: Session, api_tester_user: user_models.User):
        from datetime import datetime, timezone

        hunt_1 = hunt_models.Hunt(
            user_id=api_tester_user.id,
            name="Test Hunt",
            description="A test hunt description",
            query="ip:1.2.3.4",
            hunt_type="opensearch",
            index_target="attributes",
            status="active",
            created_at=datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
        )
        db.add(hunt_1)
        db.commit()
        db.refresh(hunt_1)

        yield hunt_1

    @pytest.fixture(scope="class")
    def hunt_run_history_1(self, db: Session, hunt_1: hunt_models.Hunt):
        from datetime import datetime, timezone

        entry = hunt_models.HuntRunHistory(
            hunt_id=hunt_1.id,
            run_at=datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
            match_count=5,
        )
        db.add(entry)
        db.commit()
        db.refresh(entry)

        yield entry
