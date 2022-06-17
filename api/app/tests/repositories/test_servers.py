from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.orm import Session

from ...models import attribute as attribute_models
from ...models import event as event_models
from ...models import object as object_models
from ...models import object_reference as object_reference_models
from ...models import server as server_models
from ...models import user as user_models
from ...repositories import servers as servers_repository
from ...settings import Settings
from ..api_tester import ApiTester


class TestServersRepository(ApiTester):
    @pytest.fixture(scope="class")
    def mock_event_search_response_1(self) -> list:
        return [
            {
                "id": "1",
                "timestamp": "1655364474",
                "sighting_timestamp": "0",
                "published": True,
                "uuid": "572503da-c87f-4520-a9bc-8de08b9c92e5",
                "orgc_uuid": "10c8f445-888b-4a2d-bac8-4e1e8861d595",
            }
        ]

    @pytest.fixture(scope="class")
    def mock_event_1(self) -> dict:
        return {
            "Event": {
                "id": "1",
                "orgc_id": "1",
                "org_id": "1",
                "date": "2022-06-09",
                "threat_level_id": "1",
                "info": "test pull from misp-lite",
                "published": True,
                "uuid": "572503da-c87f-4520-a9bc-8de08b9c92e5",
                "attribute_count": "5",
                "analysis": "0",
                "timestamp": "1655364474",
                "distribution": "2",
                "proposal_email_lock": False,
                "locked": False,
                "publish_timestamp": "1655365142",
                "sharing_group_id": "0",
                "disable_correlation": False,
                "extends_uuid": "",
                "protected": None,
                "event_creator_email": "admin@admin.test",
                "Org": {
                    "id": "1",
                    "name": "HOST",
                    "uuid": "10c8f445-888b-4a2d-bac8-4e1e8861d595",
                    "local": True,
                },
                "Orgc": {
                    "id": "1",
                    "name": "HOST",
                    "uuid": "10c8f445-888b-4a2d-bac8-4e1e8861d595",
                    "local": True,
                },
                "Attribute": [
                    {
                        "id": "1",
                        "type": "ip-src",
                        "category": "Network activity",
                        "to_ids": False,
                        "uuid": "e437b43c-8b13-4599-9ccf-f31c61007dd2",
                        "event_id": "1",
                        "distribution": "5",
                        "timestamp": "1654760393",
                        "comment": "",
                        "sharing_group_id": "0",
                        "deleted": False,
                        "disable_correlation": False,
                        "object_id": "0",
                        "object_relation": None,
                        "first_seen": None,
                        "last_seen": None,
                        "value": "1.1.1.1",
                        "Galaxy": [],
                        "ShadowAttribute": [],
                    }
                ],
                "ShadowAttribute": [],
                "RelatedEvent": [],
                "Galaxy": [],
                "Object": [
                    {
                        "id": "1",
                        "name": "ip-port",
                        "meta-category": "network",
                        "description": "An IP address (or domain or hostname) and a port seen as a tuple (or as a triple) in a specific time frame.",
                        "template_uuid": "9f8cea74-16fe-4968-a2b4-026676949ac6",
                        "template_version": "9",
                        "event_id": "1",
                        "uuid": "519090c8-470a-4429-9990-f771969cc375",
                        "timestamp": "1655213042",
                        "distribution": "5",
                        "sharing_group_id": "0",
                        "comment": "",
                        "deleted": False,
                        "first_seen": None,
                        "last_seen": None,
                        "ObjectReference": [
                            {
                                "id": "1",
                                "uuid": "ca7f0f25-80c8-4383-ae83-899ba96a36fc",
                                "timestamp": "1655454733",
                                "object_id": "1",
                                "referenced_uuid": "576a7264-0029-46e5-8eaa-771d3a9ec3d3",
                                "referenced_id": "2",
                                "referenced_type": "1",
                                "relationship_type": "uses",
                                "comment": "",
                                "deleted": False,
                                "event_id": "1",
                                "source_uuid": "519090c8-470a-4429-9990-f771969cc375",
                                "Object": {
                                    "distribution": "5",
                                    "sharing_group_id": "0",
                                    "uuid": "576a7264-0029-46e5-8eaa-771d3a9ec3d3",
                                    "name": "email",
                                    "meta-category": "network",
                                },
                            }
                        ],
                        "Attribute": [
                            {
                                "id": "3",
                                "type": "domain",
                                "category": "Network activity",
                                "to_ids": True,
                                "uuid": "201257fb-8d9e-4b27-ac26-d00cdf35a744",
                                "event_id": "1",
                                "distribution": "5",
                                "timestamp": "1655213042",
                                "comment": "",
                                "sharing_group_id": "0",
                                "deleted": False,
                                "disable_correlation": False,
                                "object_id": "1",
                                "object_relation": "domain",
                                "first_seen": None,
                                "last_seen": None,
                                "value": "evil.com",
                                "Galaxy": [],
                                "ShadowAttribute": [],
                            },
                            {
                                "id": "4",
                                "type": "port",
                                "category": "Network activity",
                                "to_ids": False,
                                "uuid": "75fa97cb-55ee-4bcf-af96-12c669c4283c",
                                "event_id": "1",
                                "distribution": "5",
                                "timestamp": "1655213042",
                                "comment": "",
                                "sharing_group_id": "0",
                                "deleted": False,
                                "disable_correlation": True,
                                "object_id": "1",
                                "object_relation": "dst-port",
                                "first_seen": None,
                                "last_seen": None,
                                "value": "54321",
                                "Galaxy": [],
                                "ShadowAttribute": [],
                            },
                            {
                                "id": "5",
                                "type": "ip-dst",
                                "category": "Network activity",
                                "to_ids": True,
                                "uuid": "0041ec54-a699-4984-8d6c-860cc9ef378b",
                                "event_id": "1",
                                "distribution": "5",
                                "timestamp": "1655213042",
                                "comment": "",
                                "sharing_group_id": "0",
                                "deleted": False,
                                "disable_correlation": False,
                                "object_id": "1",
                                "object_relation": "ip",
                                "first_seen": None,
                                "last_seen": None,
                                "value": "9.9.9.9",
                                "Galaxy": [],
                                "ShadowAttribute": [],
                            },
                        ],
                    },
                    {
                        "id": "2",
                        "name": "email",
                        "meta-category": "network",
                        "description": "Email object describing an email with meta-information",
                        "template_uuid": "a0c666e0-fc65-4be8-b48f-3423d788b552",
                        "template_version": "18",
                        "event_id": "1",
                        "uuid": "576a7264-0029-46e5-8eaa-771d3a9ec3d3",
                        "timestamp": "1655364474",
                        "distribution": "5",
                        "sharing_group_id": "0",
                        "comment": "",
                        "deleted": False,
                        "first_seen": None,
                        "last_seen": None,
                        "ObjectReference": [],
                        "Attribute": [
                            {
                                "id": "6",
                                "type": "email-src",
                                "category": "Payload delivery",
                                "to_ids": True,
                                "uuid": "f489ac2f-8f5e-4232-ac0d-f2e70839afdc",
                                "event_id": "1",
                                "distribution": "5",
                                "timestamp": "1655364474",
                                "comment": "",
                                "sharing_group_id": "0",
                                "deleted": False,
                                "disable_correlation": False,
                                "object_id": "2",
                                "object_relation": "from",
                                "first_seen": None,
                                "last_seen": None,
                                "value": "hacker@evil.com",
                                "Galaxy": [],
                                "ShadowAttribute": [],
                            }
                        ],
                    },
                ],
                "EventReport": [],
                "CryptographicKey": [],
            }
        }

    def test_full_pull_server_by_id(
        self,
        db: Session,
        settings: Settings,
        server_1: server_models.Server,
        user_1: user_models.User,
        mock_event_search_response_1: dict,
        mock_event_1: dict,
    ):

        # mock remote MISP API calls
        with patch(
            "app.repositories.servers.get_remote_misp_connection"
        ) as mock_misp_client:
            mock_misp_client.return_value = MagicMock(
                # get remote event ids
                search_index=MagicMock(return_value=mock_event_search_response_1),
                # /events/view/{event_uuid}
                _prepare_request=MagicMock(return_value=mock_event_1),
                # raw event parsing
                _check_json_response=MagicMock(return_value=mock_event_1),
            )

            servers_repository.pull_server_by_id(
                db, settings, server_1.id, user_1, "full"
            )

            # check that the event was inserted
            event = (
                db.query(event_models.Event)
                .filter(
                    event_models.Event.uuid == "572503da-c87f-4520-a9bc-8de08b9c92e5"
                )
                .first()
            )
            assert event is not None

            # check that the attributes were inserted
            attributes = (
                db.query(attribute_models.Attribute)
                .filter(
                    attribute_models.Attribute.uuid.in_(
                        (
                            "e437b43c-8b13-4599-9ccf-f31c61007dd2",
                            "201257fb-8d9e-4b27-ac26-d00cdf35a744",
                            "75fa97cb-55ee-4bcf-af96-12c669c4283c",
                            "0041ec54-a699-4984-8d6c-860cc9ef378b",
                            "f489ac2f-8f5e-4232-ac0d-f2e70839afdc",
                        )
                    )
                )
                .all()
            )
            assert len(attributes) == 5

            # check the objects were inserted
            objects = (
                db.query(object_models.Object)
                .filter(
                    object_models.Object.uuid.in_(
                        (
                            "519090c8-470a-4429-9990-f771969cc375",
                            "576a7264-0029-46e5-8eaa-771d3a9ec3d3",
                        )
                    )
                )
                .all()
            )
            assert len(objects) == 2

            # check the object references were inserted
            object_reference_1 = (
                db.query(object_reference_models.ObjectReference)
                .filter(
                    object_reference_models.ObjectReference.uuid
                    == "ca7f0f25-80c8-4383-ae83-899ba96a36fc"
                )
                .first()
            )
            assert object_reference_1 is not None
