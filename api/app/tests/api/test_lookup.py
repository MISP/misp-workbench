import pytest
from fastapi import status
from fastapi.testclient import TestClient

from app.auth import auth
from app.repositories import lookup as lookup_repository
from app.services.opensearch import get_opensearch_client
from app.services.redis import get_redis_client
from app.tests.api_tester import ApiTester

EVENT = "99999999-9999-4999-8999-999999999999"
IDS_A = "ffffffff-0000-4000-8000-000000000001"
IDS_A_TWIN = "ffffffff-0000-4000-8000-000000000002"
NOT_IDS = "ffffffff-0000-4000-8000-000000000003"
DELETED = "ffffffff-0000-4000-8000-000000000004"
LONG = "ffffffff-0000-4000-8000-000000000005"
LATE = "ffffffff-0000-4000-8000-000000000006"
LONG_VALUE = "https://example.com/" + "q" * 300

_TAG = {
    "exportable": True,
    "hide_tag": False,
    "is_galaxy": False,
    "is_custom_galaxy": False,
    "local_only": False,
    "colour": "#000000",
}


def _attribute(
    uuid, value, type_="ip-dst", to_ids=True, deleted=False, timestamp=1700000000
):
    return {
        "uuid": uuid,
        "event_uuid": EVENT,
        "type": type_,
        "category": "Network activity",
        "value": value,
        "to_ids": to_ids,
        "deleted": deleted,
        "comment": "",
        "timestamp": timestamp,
        "tags": [{"id": 1, "name": "tlp:amber", **_TAG}],
    }


def _index(*docs):
    client = get_opensearch_client()
    for doc in docs:
        client.index(index="misp-attributes", id=doc["uuid"], body=doc)
    client.indices.refresh(index="misp-attributes")


LOOKUP_KEYS = (
    lookup_repository.VALUES_KEY,
    lookup_repository.BUILT_AT_KEY,
    lookup_repository.CURSOR_KEY,
    lookup_repository.REBUILD_LOCK_KEY,
    f"{lookup_repository.REBUILD_LOCK_KEY}:queued",
    lookup_repository.SYNC_LOCK_KEY,
)


class TestLookup(ApiTester):
    @pytest.fixture(scope="class", autouse=True)
    def dataset(self, cleanup):
        get_opensearch_client().index(
            index="misp-events",
            id=EVENT,
            body={
                "uuid": EVENT,
                "info": "lookup test event",
                "published": True,
                "threat_level": 1,
                "organisation": {"name": "CIRCL"},
                "deleted": False,
                "tags": [],
            },
            refresh=True,
        )
        _index(
            _attribute(IDS_A, "198.51.100.10", timestamp=1700000001),
            _attribute(IDS_A_TWIN, "198.51.100.10", timestamp=1700000002),
            _attribute(NOT_IDS, "198.51.100.20", to_ids=False),
            _attribute(DELETED, "198.51.100.30", deleted=True),
            _attribute(LONG, LONG_VALUE, type_="url"),
        )
        redis = get_redis_client()
        redis.delete(*LOOKUP_KEYS)
        assert lookup_repository.rebuild_cache() == 2
        yield
        redis.delete(*LOOKUP_KEYS)

    def _post(self, client, token, **body):
        return client.post(
            "/lookup", json=body, headers={"Authorization": "Bearer " + token}
        )

    @pytest.mark.parametrize("scopes", [["attributes:read"]])
    def test_bulk_lookup(self, client: TestClient, auth_token: auth.Token):
        response = self._post(
            client,
            auth_token,
            values=[
                "192.0.2.1",
                "198.51.100.10",
                LONG_VALUE,
                "198.51.100.20",
                "198.51.100.30",
            ],
        )
        assert response.status_code == status.HTTP_200_OK, response.text
        data = response.json()
        assert data["checked"] == 5
        assert data["source"] == "cache"
        # Only live IDS indicators were candidates; misses never reached OpenSearch.
        assert data["candidates"] == 2
        assert [m["value"] for m in data["matches"]] == ["198.51.100.10", LONG_VALUE]

        match = data["matches"][0]
        assert match["attribute_count"] == 2
        # Newest first.
        assert [a["uuid"] for a in match["attributes"]] == [IDS_A_TWIN, IDS_A]
        attribute = match["attributes"][0]
        assert attribute["tags"] == ["tlp:amber"]
        assert attribute["event"]["info"] == "lookup test event"
        assert attribute["event"]["org"] == "CIRCL"

    @pytest.mark.parametrize("scopes", [["attributes:read"]])
    def test_any_attribute_mode(self, client: TestClient, auth_token: auth.Token):
        data = self._post(
            client,
            auth_token,
            values=["198.51.100.20", "198.51.100.30"],
            to_ids_only=False,
        ).json()
        assert data["source"] == "opensearch"
        # Non-IDS counts here; deleted never does.
        assert [m["value"] for m in data["matches"]] == ["198.51.100.20"]

    @pytest.mark.parametrize("scopes", [["attributes:read"]])
    def test_stale_cache_entries_are_verified_away(
        self, client: TestClient, auth_token: auth.Token
    ):
        # A value left in the set after its attribute stopped being an indicator.
        get_redis_client().sadd(lookup_repository.VALUES_KEY, "198.51.100.20")
        data = self._post(client, auth_token, values=["198.51.100.20"]).json()
        assert data["candidates"] == 1
        assert data["matches"] == []

    @pytest.mark.parametrize("scopes", [["attributes:read"]])
    def test_max_attributes(self, client: TestClient, auth_token: auth.Token):
        [match] = self._post(
            client, auth_token, values=["198.51.100.10"], max_attributes=1
        ).json()["matches"]
        assert match["attribute_count"] == 2
        assert len(match["attributes"]) == 1

    @pytest.mark.parametrize("scopes", [["attributes:read"]])
    def test_single_lookup(self, client: TestClient, auth_token: auth.Token):
        headers = {"Authorization": "Bearer " + auth_token}
        hit = client.get("/lookup", params={"value": "198.51.100.10"}, headers=headers)
        assert hit.json()["match"] is True
        assert hit.json()["attribute_count"] == 2
        miss = client.get("/lookup", params={"value": "192.0.2.99"}, headers=headers)
        assert miss.json() == {
            "value": "192.0.2.99",
            "match": False,
            "attribute_count": 0,
            "attributes": [],
        }

    @pytest.mark.parametrize("scopes", [["attributes:read"]])
    def test_limits_and_validation(self, client: TestClient, auth_token: auth.Token):
        too_many = [str(i) for i in range(lookup_repository.MAX_VALUES_PER_REQUEST + 1)]
        response = self._post(client, auth_token, values=too_many)
        assert response.status_code == status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
        response = self._post(client, auth_token, values=["x"], max_attributes=0)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.parametrize("scopes", [[]])
    def test_requires_scope(self, client: TestClient, auth_token: auth.Token):
        response = self._post(client, auth_token, values=["x"])
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.parametrize("scopes", [["attributes:read"]])
    def test_sync_picks_up_new_indicators(
        self, client: TestClient, auth_token: auth.Token
    ):
        _index(_attribute(LATE, "198.51.100.99"))
        miss = self._post(client, auth_token, values=["198.51.100.99"]).json()
        # Not in the prefilter yet: a cache miss until the next sync.
        assert miss["matches"] == []

        added = lookup_repository.sync_cache()
        assert added >= 1
        hit = self._post(client, auth_token, values=["198.51.100.99"]).json()
        assert [m["value"] for m in hit["matches"]] == ["198.51.100.99"]

        status_response = client.get(
            "/lookup/cache", headers={"Authorization": "Bearer " + auth_token}
        ).json()
        assert status_response["built"] is True
        assert status_response["values"] >= 3
