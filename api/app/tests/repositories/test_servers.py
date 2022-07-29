from unittest.mock import MagicMock, patch

import pytest
from app.models import attribute as attribute_models
from app.models import event as event_models
from app.models import object as object_models
from app.models import object_reference as object_reference_models
from app.models import organisation as organisations_models
from app.models import server as server_models
from app.models import sharing_groups as sharing_groups_models
from app.models import tag as tag_models
from app.models import user as user_models
from app.repositories import servers as servers_repository
from app.settings import Settings
from app.tests.api_tester import ApiTester
from app.tests.scenarios import server_pull_scenarios
from sqlalchemy import and_
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
        settings: Settings,
        server_1: server_models.Server,
        user_1: user_models.User,
        scenario: dict,
    ):

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
                db, settings, server_1.id, user_1, scenario["pull_technique"]
            )

            # check that the events were created
            events = (
                db.query(event_models.Event)
                .filter(
                    event_models.Event.uuid.in_(
                        scenario["expected_result"]["event_uuids"]
                    )
                )
                .all()
            )
            assert len(events) == len(scenario["expected_result"]["event_uuids"])

            # check that the attributes were created
            attributes = (
                db.query(attribute_models.Attribute)
                .filter(
                    attribute_models.Attribute.uuid.in_(
                        scenario["expected_result"]["attribute_uuids"]
                    )
                )
                .all()
            )
            assert len(attributes) == len(
                scenario["expected_result"]["attribute_uuids"]
            )

            # check the objects were created
            objects = (
                db.query(object_models.Object)
                .filter(
                    object_models.Object.uuid.in_(
                        scenario["expected_result"]["object_uuids"]
                    )
                )
                .all()
            )
            assert len(objects) == len(scenario["expected_result"]["object_uuids"])

            # check the object references were created
            object_references = (
                db.query(object_reference_models.ObjectReference)
                .filter(
                    object_reference_models.ObjectReference.uuid.in_(
                        scenario["expected_result"]["object_reference_uuids"]
                    )
                )
                .all()
            )
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
            tags = (
                db.query(tag_models.Tag)
                .filter(tag_models.Tag.name.in_(scenario["expected_result"]["tags"]))
                .all()
            )
            assert len(tags) == len(scenario["expected_result"]["tags"])

            # check the event tags were created
            event_tags = (
                db.query(tag_models.Tag)
                .join(tag_models.EventTag)
                .filter(
                    tag_models.Tag.name.in_(scenario["expected_result"]["event_tags"])
                )
                .all()
            )
            assert len(event_tags) == len(scenario["expected_result"]["event_tags"])

            # check the attribute tags were created
            for attribute_tag in scenario["expected_result"]["attribute_tags"]:
                attribute_tags = (
                    db.query(tag_models.Tag)
                    .join(tag_models.AttributeTag)
                    .filter(
                        and_(
                            tag_models.Tag.name.in_(attribute_tag["tags"]),
                            attribute_models.Attribute.uuid
                            == attribute_tag["attribute_uuid"],
                            attribute_models.Attribute.id
                            == tag_models.AttributeTag.attribute_id,
                        )
                    )
                    .all()
                )
                assert len(attribute_tags) == len(attribute_tag["tags"])
