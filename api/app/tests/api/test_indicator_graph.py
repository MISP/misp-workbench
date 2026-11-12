import pytest
from fastapi import status
from fastapi.testclient import TestClient

from app.auth import auth
from app.repositories import indicators
from app.services.opensearch import get_opensearch_client
from app.tests.api_tester import ApiTester

DOMAIN = "graph.example.org"
IP = "203.0.113.9"

PLAIN_EVENT = "9a9a0000-0000-4000-8000-000000000001"
OBJECT_EVENT = "9a9a0000-0000-4000-8000-000000000002"
DELETED_EVENT = "9a9a0000-0000-4000-8000-000000000003"
DOMAIN_IP = "9a9a0000-1000-4000-8000-000000000001"

PLAIN = "9a9a0000-2000-4000-8000-000000000001"
IN_OBJECT = "9a9a0000-2000-4000-8000-000000000002"
SIBLING_IP = "9a9a0000-2000-4000-8000-000000000003"
IN_DELETED_EVENT = "9a9a0000-2000-4000-8000-000000000004"
DELETED = "9a9a0000-2000-4000-8000-000000000005"


def _event(uuid, timestamp, deleted=False, source=None):
    return {
        "uuid": uuid,
        "info": f"graph event {uuid[-1]}",
        "date": "2026-11-01",
        "timestamp": timestamp,
        "deleted": deleted,
        "published": True,
        "organisation": {"id": None, "name": "Graph Org"},
        "source": source or {"type": "local", "id": None, "name": None},
        "tags": [],
    }


def _attribute(uuid, event_uuid, type_, value, deleted=False, **extra):
    return {
        "uuid": uuid,
        "event_uuid": event_uuid,
        "type": type_,
        "category": "Network activity",
        "value": value,
        "to_ids": True,
        "deleted": deleted,
        "comment": "",
        "timestamp": 1790000000,
        "tags": [],
        **extra,
    }


class TestIndicatorGraph(ApiTester):
    @pytest.fixture(scope="class", autouse=True)
    def dataset(self, cleanup):
        client = get_opensearch_client()
        for event in (
            _event(PLAIN_EVENT, 1790000000),
            _event(
                OBJECT_EVENT,
                1790000500,
                source={"type": "feed", "id": 3, "name": "Feed G"},
            ),
            _event(DELETED_EVENT, 1790000900, deleted=True),
        ):
            client.index(index="misp-events", id=event["uuid"], body=event)
        client.index(
            index="misp-objects",
            id=DOMAIN_IP,
            body={
                "uuid": DOMAIN_IP,
                "name": "domain-ip",
                "meta_category": "network",
                "event_uuid": OBJECT_EVENT,
                "deleted": False,
                "timestamp": 1790000500,
            },
        )
        for doc in (
            _attribute(PLAIN, PLAIN_EVENT, "domain", DOMAIN),
            _attribute(
                IN_OBJECT,
                OBJECT_EVENT,
                "domain",
                DOMAIN,
                object_uuid=DOMAIN_IP,
                object_relation="domain",
            ),
            _attribute(
                SIBLING_IP,
                OBJECT_EVENT,
                "ip-dst",
                IP,
                object_uuid=DOMAIN_IP,
                object_relation="ip",
            ),
            _attribute(IN_DELETED_EVENT, DELETED_EVENT, "domain", DOMAIN),
            _attribute(DELETED, PLAIN_EVENT, "domain", DOMAIN, deleted=True),
        ):
            client.index(index="misp-attributes", id=doc["uuid"], body=doc)
        client.indices.refresh(index="misp-events,misp-objects,misp-attributes")
        indicators.refresh_values([DOMAIN, IP])
        client.indices.refresh(index=indicators.INDEX)
        yield

    def _graph(self, client, auth_token, type_, value, **params):
        return client.get(
            f"/indicators/{indicators.indicator_uuid(type_, value)}/graph",
            params=params,
            headers={"Authorization": "Bearer " + auth_token},
        )

    @pytest.mark.parametrize("scopes", [["attributes:read"]])
    def test_plain_and_object_attributes(
        self, client: TestClient, auth_token: auth.Token
    ):
        response = self._graph(client, auth_token, "domain", DOMAIN)
        assert response.status_code == status.HTTP_200_OK, response.text
        graph = response.json()
        assert graph["indicator"] == {
            "uuid": indicators.indicator_uuid("domain", DOMAIN),
            "type": "domain",
            "value": DOMAIN,
            "deleted": False,
        }
        # Neither the deleted attribute nor the one in a deleted event.
        by_uuid = {a["uuid"]: a for a in graph["attributes"]}
        assert set(by_uuid) == {PLAIN, IN_OBJECT}
        assert (by_uuid[PLAIN]["event_uuid"], by_uuid[PLAIN]["object_uuid"]) == (
            PLAIN_EVENT,
            None,
        )
        assert by_uuid[IN_OBJECT]["object_uuid"] == DOMAIN_IP
        assert by_uuid[IN_OBJECT]["object_relation"] == "domain"

        # The object, with its other attributes as context.
        [obj] = graph["objects"]
        assert (obj["uuid"], obj["name"], obj["event_uuid"]) == (
            DOMAIN_IP,
            "domain-ip",
            OBJECT_EVENT,
        )
        assert [(a["uuid"], a["object_relation"]) for a in obj["attributes"]] == [
            (SIBLING_IP, "ip")
        ]
        assert obj["attribute_count"] == 1

        # Newest event first, with its source.
        assert [e["uuid"] for e in graph["events"]] == [OBJECT_EVENT, PLAIN_EVENT]
        assert graph["events"][0]["source"] == {
            "type": "feed",
            "id": 3,
            "name": "Feed G",
        }
        assert graph["events"][0]["info"] == "graph event 2"
        assert (
            graph["attribute_count"],
            graph["event_count"],
            graph["omitted_events"],
        ) == (2, 2, 0)

    @pytest.mark.parametrize("scopes", [["attributes:read"]])
    def test_capped(self, client: TestClient, auth_token: auth.Token):
        graph = self._graph(client, auth_token, "domain", DOMAIN, max_events=1).json()
        assert [e["uuid"] for e in graph["events"]] == [OBJECT_EVENT]
        assert [a["uuid"] for a in graph["attributes"]] == [IN_OBJECT]
        assert (graph["event_count"], graph["omitted_events"]) == (2, 1)
        assert (
            self._graph(client, auth_token, "domain", DOMAIN, max_events=0).status_code
            == status.HTTP_422_UNPROCESSABLE_ENTITY
        )

    @pytest.mark.parametrize("scopes", [["attributes:read"]])
    def test_missing_and_tombstoned(self, client: TestClient, auth_token: auth.Token):
        missing = client.get(
            "/indicators/00000000-0000-4000-8000-000000000000/graph",
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert missing.status_code == status.HTTP_404_NOT_FOUND

        # The object's IP loses its only attribute: a tombstone, drawn empty.
        os_client = get_opensearch_client()
        os_client.update(
            index="misp-attributes",
            id=SIBLING_IP,
            body={"doc": {"deleted": True}},
            refresh=True,
        )
        indicators.refresh_values([IP])
        os_client.indices.refresh(index=indicators.INDEX)
        graph = self._graph(client, auth_token, "ip-dst", IP).json()
        assert graph["indicator"]["deleted"] is True
        assert (graph["attributes"], graph["objects"], graph["events"]) == (
            [],
            [],
            [],
        )

    @pytest.mark.parametrize("scopes", [[]])
    def test_needs_the_scope(self, client: TestClient, auth_token: auth.Token):
        response = self._graph(client, auth_token, "domain", DOMAIN)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
