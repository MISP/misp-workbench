from unittest.mock import MagicMock, patch

import pytest
from uuid import UUID

from app.models.event import DistributionLevel
from app.repositories import attributes as attributes_repository
from app.repositories import object_references as object_references_repository
from app.repositories import objects as objects_repository
from app.models import organisation as organisations_models
from app.models import server as server_models
from app.models import sharing_groups as sharing_groups_models
from app.models import tag as tag_models
from app.models import user as user_models
from app.repositories import analyst_data as analyst_data_repository
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
                Settings(),
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

            # check the event distribution was downgraded on pull
            assert (
                os_events[0].distribution
                == scenario["expected_result"]["event_distribution"]
            )

            # check the analyst data was captured, threads included
            expected_analyst_data = scenario["expected_result"]["analyst_data"]
            captured = {
                document["uuid"]: document
                for document in analyst_data_repository.get_all_analyst_data_for_event(
                    scenario["expected_result"]["event_uuids"][0]
                )
            }

            for uuid, (
                analyst_type,
                object_uuid,
                object_type,
            ) in expected_analyst_data.items():
                assert uuid in captured, f"analyst data {uuid} was not captured"
                document = captured[uuid]
                assert document["analyst_type"] == analyst_type
                assert document["object_uuid"] == object_uuid
                assert document["object_type"] == object_type
                # pulled from an external server, so the distribution is
                # downgraded from connected communities to community only
                assert (
                    document["distribution"] == DistributionLevel.COMMUNITY_ONLY.value
                )

            if expected_analyst_data:
                # the thread hangs off the event note rather than the event
                threads = analyst_data_repository.get_analyst_data_by_event_uuid(
                    scenario["expected_result"]["event_uuids"][0]
                )
                assert [n.uuid for n in threads.notes] == [
                    "a1b11111-1111-4111-8111-111111111111"
                ]
                assert [o.uuid for o in threads.opinions] == [
                    "a1b44444-4444-4444-8444-444444444444"
                ]
                assert [r.uuid for r in threads.relationships] == [
                    "a1b55555-5555-4555-8555-555555555555"
                ]

                event_note = threads.notes[0]
                assert [n.uuid for n in event_note.notes] == [
                    "a1b22222-2222-4222-8222-222222222222"
                ]
                assert [o.uuid for o in event_note.opinions] == [
                    "a1b33333-3333-4333-8333-333333333333"
                ]

                # analyst data on an attribute is read by the attribute uuid
                attribute_threads = (
                    analyst_data_repository.get_analyst_data_by_object_uuid(
                        "e437b43c-8b13-4599-9ccf-f31c61007dd2", "Attribute"
                    )
                )
                assert [n.uuid for n in attribute_threads.notes] == [
                    "a1b66666-6666-4666-8666-666666666666"
                ]

            # check the objects were created
            objects = [
                objects_repository.get_object_from_opensearch(UUID(uuid))
                for uuid in scenario["expected_result"]["object_uuids"]
            ]
            objects = [o for o in objects if o is not None]
            assert len(objects) == len(scenario["expected_result"]["object_uuids"])

            # check the object references were created
            object_references = [
                object_references_repository.get_object_reference_by_uuid(
                    db, UUID(uuid)
                )
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
                for t in event.tags or []:
                    event_tag_names.add(t.name)
            for tag_name in scenario["expected_result"]["event_tags"]:
                assert tag_name in event_tag_names

            # check the attribute tags were created
            all_attribute_tag_names = set()
            for attr in attributes:
                for t in attr.tags or []:
                    all_attribute_tag_names.add(t.name)
            for attribute_tag in scenario["expected_result"]["attribute_tags"]:
                for tag_name in attribute_tag["tags"]:
                    assert tag_name in all_attribute_tag_names


class TestDowngradeDistribution:
    """
    downgrade_distribution guards against over-sharing data pulled from an
    external server, so each level is pinned explicitly.
    """

    @pytest.mark.parametrize(
        "level,expected",
        [
            (DistributionLevel.ORGANISATION_ONLY.value, 0),
            (DistributionLevel.COMMUNITY_ONLY.value, 0),
            (DistributionLevel.CONNECTED_COMMUNITIES.value, 1),
            (DistributionLevel.ALL_COMMUNITIES.value, 3),
            (DistributionLevel.SHARING_GROUP.value, 4),
            (DistributionLevel.INHERIT_EVENT.value, 5),
        ],
    )
    def test_downgrades_only_community_and_connected(self, level, expected):
        assert servers_repository.downgrade_distribution(level) == expected

    @pytest.mark.parametrize("level", ["1", "2", "4"])
    def test_accepts_the_strings_misp_json_carries(self, level):
        assert servers_repository.downgrade_distribution(
            level
        ) == servers_repository.downgrade_distribution(int(level))

    @pytest.mark.parametrize(
        "level",
        [
            DistributionLevel.COMMUNITY_ONLY,
            DistributionLevel.CONNECTED_COMMUNITIES,
            DistributionLevel.SHARING_GROUP,
        ],
    )
    def test_accepts_a_distribution_level_member(self, level):
        # the members are a plain Enum, so they never compare equal to the ints
        # pymisp supplies -- passing one must still downgrade
        assert servers_repository.downgrade_distribution(
            level
        ) == servers_repository.downgrade_distribution(level.value)

    @pytest.mark.parametrize("missing", [None, ""])
    def test_missing_level_becomes_community_only(self, missing):
        assert (
            servers_repository.downgrade_distribution(missing)
            == DistributionLevel.COMMUNITY_ONLY.value
        )

    def test_unreadable_level_fails_closed(self):
        assert (
            servers_repository.downgrade_distribution("not-a-level")
            == DistributionLevel.ORGANISATION_ONLY.value
        )

    @pytest.mark.parametrize(
        "level", [0, 1, 2, "2", None, "", DistributionLevel.COMMUNITY_ONLY]
    )
    def test_always_returns_a_plain_int(self, level):
        result = servers_repository.downgrade_distribution(level)

        # the ingest reads this back with int(), which a plain Enum member does
        # not support, so an enum must never be returned
        assert type(result) is int
