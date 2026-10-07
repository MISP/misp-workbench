from unittest.mock import patch

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.auth import auth
from app.repositories import runtime_settings as runtime_settings_repository
from app.repositories import sightings as sightings_repository
from app.services.opensearch import get_opensearch_client
from app.tests.api_tester import ApiTester
from app.worker import tasks

EVENT = "88888888-8888-4888-8888-888888888888"
NOISY = "eeeeeeee-0000-4000-8000-000000000001"
NOISY_TWIN = "eeeeeeee-0000-4000-8000-000000000002"
QUIET = "eeeeeeee-0000-4000-8000-000000000003"
LONG = "eeeeeeee-0000-4000-8000-000000000004"
LONG_VALUE = "https://example.com/" + "p" * 300


def _attribute(uuid, value, attribute_id=None):
    return {
        "uuid": uuid,
        "id": attribute_id,
        "event_uuid": EVENT,
        "type": "ip-dst",
        "category": "Network activity",
        "value": value,
        "to_ids": True,
        "deleted": False,
        "timestamp": 1700000000,
        "tags": [],
    }


class TestSightingsIngestion(ApiTester):
    @pytest.fixture(scope="class", autouse=True)
    def dataset(self, cleanup):
        client = get_opensearch_client()
        for doc in (
            _attribute(NOISY, "198.51.100.66", attribute_id=4242),
            _attribute(NOISY_TWIN, "198.51.100.66"),
            _attribute(QUIET, "198.51.100.77"),
            _attribute(LONG, LONG_VALUE),
        ):
            client.index(index="misp-attributes", id=doc["uuid"], body=doc)
        client.indices.refresh(index="misp-attributes")
        yield
        client.delete_by_query(
            index="misp-sightings",
            body={"query": {"match_all": {}}},
            ignore=[404],
            refresh=True,
        )

    def _headers(self, token):
        return {"Authorization": "Bearer " + token}

    # ── bulk ingestion ───────────────────────────────────────────────────

    @pytest.mark.parametrize("scopes", [["sightings:create"]])
    def test_bulk_queues_one_task_per_batch(
        self, client: TestClient, auth_token: auth.Token
    ):
        sightings = [{"value": f"203.0.113.{i % 250}"} for i in range(2500)]
        with patch.object(tasks.handle_created_sightings, "delay") as delay:
            response = client.post(
                "/sightings/", json=sightings, headers=self._headers(auth_token)
            )
        assert response.status_code == status.HTTP_201_CREATED, response.text
        # 2500 sightings -> 3 tasks, not 2500.
        assert [len(call.args[0]) for call in delay.call_args_list] == [1000, 1000, 500]
        item = delay.call_args_list[0].args[0][0]
        assert set(item) == {"value", "type", "organisation", "timestamp"}

    @pytest.mark.parametrize("scopes", [["sightings:create"]])
    def test_request_size_cap(self, client: TestClient, auth_token: auth.Token):
        too_many = [{"value": "x"}] * (
            sightings_repository.MAX_SIGHTINGS_PER_REQUEST + 1
        )
        with patch.object(tasks.handle_created_sightings, "delay"):
            response = client.post(
                "/sightings/", json=too_many, headers=self._headers(auth_token)
            )
        assert response.status_code == status.HTTP_413_REQUEST_ENTITY_TOO_LARGE

    # ── MISP /sightings/add ──────────────────────────────────────────────

    @pytest.mark.parametrize("scopes", [["sightings:create"]])
    def test_misp_add(self, client: TestClient, auth_token: auth.Token):
        with patch.object(tasks.handle_created_sightings, "delay") as delay:
            by_values = client.post(
                "/sightings/add",
                json={
                    "values": ["198.51.100.77", "203.0.113.9"],
                    "type": "0",
                    "source": "wazuh",
                },
                headers=self._headers(auth_token),
            )
            by_uuid = client.post(
                "/sightings/add",
                json={"uuid": QUIET, "type": 1},
                headers=self._headers(auth_token),
            )
            by_misp_id = client.post(
                "/sightings/add/4242", headers=self._headers(auth_token)
            )
        assert by_values.status_code == status.HTTP_200_OK, by_values.text
        assert by_values.json()["message"] == "2 sightings successfully added."
        assert by_values.json()["saved"] is True
        assert by_uuid.json()["message"] == "1 sighting successfully added."
        assert by_misp_id.status_code == status.HTTP_200_OK, by_misp_id.text

        queued = [item for call in delay.call_args_list for item in call.args[0]]
        assert [(i["value"], i["type"]) for i in queued] == [
            ("198.51.100.77", "positive"),
            ("203.0.113.9", "positive"),
            # By uuid; the false positive lands on QUIET so it doesn't count
            # towards test_false_positive_feedback's threshold on NOISY.
            ("198.51.100.77", "false-positive"),
            ("198.51.100.66", "positive"),
        ]

        client_os = get_opensearch_client()
        client_os.indices.refresh(index="misp-sightings")
        stored = client_os.search(
            index="misp-sightings",
            body={"query": {"term": {"attribute_uuid": QUIET}}, "size": 5},
        )["hits"]["hits"]
        assert stored[0]["_source"]["event_uuid"] == EVENT
        assert stored[0]["_source"]["observer"]["organisation"]

    @pytest.mark.parametrize("scopes", [["sightings:create"]])
    def test_misp_add_errors(self, client: TestClient, auth_token: auth.Token):
        def add(path="/sightings/add", **body):
            return client.post(path, json=body, headers=self._headers(auth_token))

        assert add(value="x", type=9).status_code == status.HTTP_400_BAD_REQUEST
        assert add().status_code == status.HTTP_400_BAD_REQUEST
        missing = add(uuid="00000000-0000-4000-8000-0000000000ff")
        assert missing.status_code == status.HTTP_404_NOT_FOUND
        assert add("/sightings/add/999999").status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.parametrize("scopes", [["sightings:read"]])
    def test_misp_add_needs_create_scope(
        self, client: TestClient, auth_token: auth.Token
    ):
        response = client.post(
            "/sightings/add", json={"value": "x"}, headers=self._headers(auth_token)
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    # ── post-processing ──────────────────────────────────────────────────

    def test_finds_attributes_by_exact_value(self):
        found = sightings_repository.find_sighted_attributes(
            ["198.51.100.66", LONG_VALUE, "192.0.2.200"]
        )
        assert sorted(h["_source"]["uuid"] for h in found["198.51.100.66"]) == sorted(
            [NOISY, NOISY_TWIN]
        )
        assert [h["_source"]["uuid"] for h in found[LONG_VALUE]] == [LONG]
        assert "192.0.2.200" not in found

    def test_false_positive_feedback(self, db: Session, api_tester_user):
        client = get_opensearch_client()

        def to_ids(uuid):
            return client.get(index="misp-attributes", id=uuid)["_source"]["to_ids"]

        def report_false_positive(value):
            sightings_repository.create_sightings(
                api_tester_user, {"value": value, "type": "false-positive"}
            )

        def process(value):
            return sightings_repository.process_created_sightings(
                db,
                [{"value": value, "type": "false-positive", "organisation": "x"}],
            )

        with patch.object(tasks.handle_created_sightings, "delay"):
            # Off by default: reports alone change nothing.
            report_false_positive("198.51.100.66")
            assert process("198.51.100.66")["to_ids_disabled"] == []

            runtime_settings_repository.set_setting(
                db, "sightings", {"false_positive_threshold": 3}
            )
            try:
                report_false_positive("198.51.100.66")
                assert process("198.51.100.66")["to_ids_disabled"] == []
                assert to_ids(NOISY) is True

                report_false_positive("198.51.100.66")
                result = process("198.51.100.66")
            finally:
                runtime_settings_repository.delete_setting(db, "sightings")

        assert result["to_ids_disabled"] == ["198.51.100.66"]
        # Every attribute with the value stops being an IDS indicator...
        assert to_ids(NOISY) is False
        assert to_ids(NOISY_TWIN) is False
        # ...and only those.
        assert to_ids(QUIET) is True
