from unittest.mock import MagicMock, patch

import pytest
from uuid import UUID

from app.repositories import attributes as attributes_repository
from app.repositories import object_references as object_references_repository
from app.repositories import objects as objects_repository
from app.models import organisation as organisations_models
from app.models import server as server_models
from app.models import sharing_groups as sharing_groups_models
from app.models import tag as tag_models
from app.models import user as user_models
from app.repositories import events as events_repository
from app.repositories import servers as servers_repository
from app.settings import Settings
from app.tests.api_tester import ApiTester
from app.tests.scenarios import server_pull_scenarios
from sqlalchemy.orm import Session


class TestServersRepository(ApiTester):
    @pytest.fixture(scope="function")
    def scenario(self, test_case: str):
        yield server_pull_scenarios.test_cases[test_case]

    @pytest.mark.parametrize(
        "test_case", ["pull_all_communities_event", "pull_sharing_group_event"]
    )
    def test_pull_server_by_id(
        self,
        db: Session,
        server_1: server_models.Server,
        user_1: user_models.User,
        scenario: dict,
    ):
        # clear the database
        db.query(tag_models.Tag).delete()

        # mock remote MISP API calls
        with patch(
            "app.repositories.servers.get_remote_misp_connection"
        ) as mock_misp_client:
            mock_misp_client.return_value = MagicMock(
                # get remote event ids
                search_index=MagicMock(
                    return_value=scenario["mock_event_search_response"]
                ),
                # /events/view/{event_uuid}
                _prepare_request=MagicMock(
                    return_value=scenario["mock_event_view_response"]
                ),
                # raw event parsing
                _check_json_response=MagicMock(
                    return_value=scenario["mock_event_view_response"]
                ),
            )

            servers_repository.pull_server_by_id(
                db, server_1.id, user_1, scenario["pull_technique"]
            )
            servers_repository.pull_event_by_uuid(
                db,
                scenario["expected_result"]["event_uuids"][0],
                server_1,
                user_1,
                Settings()
            )

            # check that the events were created
            os_events = [
                events_repository.get_event_from_opensearch(UUID(uuid))
                for uuid in scenario["expected_result"]["event_uuids"]
            ]
            os_events = [e for e in os_events if e is not None]
            assert len(os_events) == len(scenario["expected_result"]["event_uuids"])

            # check that the attributes were created
            attributes = [
                attributes_repository.get_attribute_from_opensearch(UUID(u))
                for u in scenario["expected_result"]["attribute_uuids"]
            ]
            attributes = [a for a in attributes if a is not None]
            assert len(attributes) == len(
                scenario["expected_result"]["attribute_uuids"]
            )

            # check the objects were created
            objects = [
                objects_repository.get_object_from_opensearch(UUID(uuid))
                for uuid in scenario["expected_result"]["object_uuids"]
            ]
            objects = [o for o in objects if o is not None]
            assert len(objects) == len(scenario["expected_result"]["object_uuids"])

            # check the object references were created
            object_references = [
                object_references_repository.get_object_reference_by_uuid(db, UUID(uuid))
                for uuid in scenario["expected_result"]["object_reference_uuids"]
            ]
            object_references = [r for r in object_references if r is not None]
            assert len(object_references) == len(
                scenario["expected_result"]["object_reference_uuids"]
            )

            # check the sharing groups were created
            sharing_groups = (
                db.query(sharing_groups_models.SharingGroup)
                .filter(
                    sharing_groups_models.SharingGroup.uuid.in_(
                        scenario["expected_result"]["sharing_groups_uuids"]
                    )
                )
                .all()
            )
            assert len(sharing_groups) == len(
                scenario["expected_result"]["sharing_groups_uuids"]
            )

            # check the sharing groups orgs were created
            sharing_group_orgs = (
                db.query(sharing_groups_models.SharingGroupOrganisation)
                .join(organisations_models.Organisation)
                .filter(
                    organisations_models.Organisation.uuid.in_(
                        scenario["expected_result"]["sharing_group_org_uuids"]
                    )
                )
                .all()
            )
            assert len(sharing_group_orgs) == len(
                scenario["expected_result"]["sharing_group_org_uuids"]
            )

            # check the tags were created
            tags = db.query(tag_models.Tag).all()
            assert len(tags) == len(scenario["expected_result"]["tags"])

            # check the event tags were created
            event_tag_names = set()
            for event in os_events:
                for t in (event.tags or []):
                    event_tag_names.add(t.name)
            for tag_name in scenario["expected_result"]["event_tags"]:
                assert tag_name in event_tag_names

            # check the attribute tags were created
            all_attribute_tag_names = set()
            for attr in attributes:
                for t in (attr.tags or []):
                    all_attribute_tag_names.add(t.name)
            for attribute_tag in scenario["expected_result"]["attribute_tags"]:
                for tag_name in attribute_tag["tags"]:
                    assert tag_name in all_attribute_tag_names
