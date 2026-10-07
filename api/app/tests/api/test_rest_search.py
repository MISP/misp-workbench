import csv
import io
import time

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from app.auth import auth
from app.repositories import rest_search as rest_search_repository
from app.services.opensearch import get_opensearch_client
from app.tests.api_tester import ApiTester

EVENT_PUBLISHED = "11111111-1111-4111-8111-111111111111"
EVENT_DRAFT = "22222222-2222-4222-8222-222222222222"
OBJECT_UUID = "33333333-3333-4333-8333-333333333333"

ATTR_IP = "aaaaaaaa-0000-4000-8000-000000000001"
ATTR_DOMAIN = "aaaaaaaa-0000-4000-8000-000000000002"
ATTR_URL = "aaaaaaaa-0000-4000-8000-000000000003"
ATTR_DRAFT_IP = "aaaaaaaa-0000-4000-8000-000000000004"
ATTR_DELETED = "aaaaaaaa-0000-4000-8000-000000000005"

NOW = int(time.time())
LONG_URL = "https://example.com/" + "a" * 300

_TAG_FLAGS = {
    "exportable": True,
    "hide_tag": False,
    "is_galaxy": False,
    "is_custom_galaxy": False,
    "local_only": False,
}
TLP_AMBER = {"id": 1, "name": "tlp:amber", "colour": "#FFC000", **_TAG_FLAGS}
APT = {
    "id": 2,
    "name": 'misp-galaxy:threat-actor="APT29"',
    "colour": "#000000",
    **_TAG_FLAGS,
    "is_galaxy": True,
}


def _event(uuid, info, published, tags, timestamp, event_id=None):
    return {
        "uuid": uuid,
        "id": event_id,
        "info": info,
        "published": published,
        "org_id": 1,
        "orgc_id": 1,
        "organisation": {
            "id": 1,
            "name": "CIRCL",
            "uuid": "55f6ea5e-2c60-40e5-964f-47a8950d210f",
            "date_created": "2024-01-01T00:00:00",
            "date_modified": "2024-01-01T00:00:00",
            "created_by": 1,
            "local": True,
        },
        "date": "2024-01-15",
        "distribution": 1,
        "threat_level": 1,
        "analysis": 2,
        "timestamp": timestamp,
        "publish_timestamp": timestamp if published else 0,
        "deleted": False,
        "tags": tags,
    }


def _attribute(uuid, event_uuid, type_, category, value, to_ids, timestamp, **extra):
    doc = {
        "uuid": uuid,
        "event_uuid": event_uuid,
        "type": type_,
        "category": category,
        "value": value,
        "to_ids": to_ids,
        "timestamp": timestamp,
        "distribution": 5,
        "comment": "",
        "deleted": False,
        "disable_correlation": False,
        "tags": [],
    }
    doc.update(extra)
    return doc


class TestRestSearch(ApiTester):
    @pytest.fixture(scope="class", autouse=True)
    def dataset(self, cleanup):
        client = get_opensearch_client()
        events = [
            _event(EVENT_PUBLISHED, "APT29 campaign", True, [APT], NOW - 3600, 42),
            _event(EVENT_DRAFT, "Phishing draft", False, [], NOW - 30 * 86400),
        ]
        attributes = [
            _attribute(
                ATTR_IP,
                EVENT_PUBLISHED,
                "ip-dst",
                "Network activity",
                "198.51.100.7",
                True,
                NOW - 3600,
                tags=[TLP_AMBER],
            ),
            _attribute(
                ATTR_DOMAIN,
                EVENT_PUBLISHED,
                "domain",
                "Network activity",
                "evil.example.com",
                True,
                NOW - 3600,
                object_uuid=OBJECT_UUID,
                object_relation="domain",
            ),
            _attribute(
                ATTR_URL,
                EVENT_PUBLISHED,
                "url",
                "Network activity",
                LONG_URL,
                False,
                NOW - 3600,
            ),
            _attribute(
                ATTR_DRAFT_IP,
                EVENT_DRAFT,
                "ip-dst",
                "Network activity",
                "203.0.113.9",
                True,
                NOW - 30 * 86400,
            ),
            _attribute(
                ATTR_DELETED,
                EVENT_DRAFT,
                "ip-dst",
                "Network activity",
                "203.0.113.10",
                True,
                NOW - 30 * 86400,
                deleted=True,
            ),
        ]
        for doc in events:
            client.index(index="misp-events", id=doc["uuid"], body=doc)
        for doc in attributes:
            client.index(index="misp-attributes", id=doc["uuid"], body=doc)
        client.index(
            index="misp-objects",
            id=OBJECT_UUID,
            body={
                "uuid": OBJECT_UUID,
                "event_uuid": EVENT_PUBLISHED,
                "name": "domain-ip",
                "meta_category": "network",
                "template_version": 1,
                "timestamp": NOW,
                "deleted": False,
            },
        )
        for index in ("misp-events", "misp-attributes", "misp-objects"):
            client.indices.refresh(index=index)
        yield

    def _search(self, client, token, body, path="/attributes/restSearch"):
        return client.post(
            path, json=body, headers={"Authorization": "Bearer " + token}
        )

    def _attribute_uuids(self, response):
        assert response.status_code == status.HTTP_200_OK, response.text
        return sorted(a["uuid"] for a in response.json()["response"]["Attribute"])

    @pytest.mark.parametrize("scopes", [["attributes:read"]])
    def test_default_excludes_deleted(self, client: TestClient, auth_token: auth.Token):
        response = self._search(client, auth_token, {})
        assert self._attribute_uuids(response) == [
            ATTR_IP,
            ATTR_DOMAIN,
            ATTR_URL,
            ATTR_DRAFT_IP,
        ]

    @pytest.mark.parametrize("scopes", [["attributes:read"]])
    def test_get_with_query_params(self, client: TestClient, auth_token: auth.Token):
        response = client.get(
            "/attributes/restSearch",
            params={"value": "198.51.100.7"},
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert self._attribute_uuids(response) == [ATTR_IP]

    @pytest.mark.parametrize("scopes", [["attributes:read"]])
    def test_value_filters(self, client: TestClient, auth_token: auth.Token):
        assert self._attribute_uuids(
            self._search(
                client, auth_token, {"value": ["198.51.100.7", "evil.example.com"]}
            )
        ) == [ATTR_IP, ATTR_DOMAIN]
        assert self._attribute_uuids(
            self._search(client, auth_token, {"value": "%EVIL.example%"})
        ) == [ATTR_DOMAIN]
        # Longer than the keyword sub-field's ignore_above.
        assert self._attribute_uuids(
            self._search(client, auth_token, {"value": LONG_URL})
        ) == [ATTR_URL]

    @pytest.mark.parametrize("scopes", [["attributes:read"]])
    def test_type_negation_and_to_ids(self, client: TestClient, auth_token: auth.Token):
        assert self._attribute_uuids(
            self._search(client, auth_token, {"type": ["!ip-dst"]})
        ) == [ATTR_DOMAIN, ATTR_URL]
        assert self._attribute_uuids(
            self._search(
                client, auth_token, {"to_ids": 1, "type": {"OR": ["ip-dst", "url"]}}
            )
        ) == [ATTR_IP, ATTR_DRAFT_IP]

    @pytest.mark.parametrize("scopes", [["attributes:read"]])
    def test_deleted(self, client: TestClient, auth_token: auth.Token):
        assert self._attribute_uuids(
            self._search(client, auth_token, {"deleted": 1})
        ) == [ATTR_DELETED]
        assert (
            len(
                self._attribute_uuids(
                    self._search(client, auth_token, {"deleted": [0, 1]})
                )
            )
            == 5
        )

    @pytest.mark.parametrize("scopes", [["attributes:read"]])
    def test_event_level_filters(self, client: TestClient, auth_token: auth.Token):
        assert self._attribute_uuids(
            self._search(client, auth_token, {"published": 1})
        ) == [ATTR_IP, ATTR_DOMAIN, ATTR_URL]
        assert self._attribute_uuids(
            self._search(client, auth_token, {"published": 0})
        ) == [ATTR_DRAFT_IP]
        assert self._attribute_uuids(
            self._search(client, auth_token, {"last": "1d", "type": "ip-dst"})
        ) == [ATTR_IP]
        assert self._attribute_uuids(
            self._search(client, auth_token, {"eventinfo": "%phishing%"})
        ) == [ATTR_DRAFT_IP]
        assert self._attribute_uuids(
            self._search(client, auth_token, {"eventid": "42"})
        ) == [ATTR_IP, ATTR_DOMAIN, ATTR_URL]
        assert self._attribute_uuids(
            self._search(client, auth_token, {"org": "CIRCL", "type": "domain"})
        ) == [ATTR_DOMAIN]

    @pytest.mark.parametrize("scopes", [["attributes:read"]])
    def test_tags_match_attribute_and_event_tags(
        self, client: TestClient, auth_token: auth.Token
    ):
        assert self._attribute_uuids(
            self._search(client, auth_token, {"tags": "tlp:amber"})
        ) == [ATTR_IP]
        # Event tag: every attribute of the tagged event.
        assert self._attribute_uuids(
            self._search(client, auth_token, {"tags": ["%APT29%"]})
        ) == [ATTR_IP, ATTR_DOMAIN, ATTR_URL]
        assert self._attribute_uuids(
            self._search(client, auth_token, {"tags": ["!tlp:amber"], "published": 1})
        ) == [ATTR_DOMAIN, ATTR_URL]

    @pytest.mark.parametrize("scopes", [["attributes:read"]])
    def test_timestamp_range(self, client: TestClient, auth_token: auth.Token):
        assert self._attribute_uuids(
            self._search(
                client, auth_token, {"timestamp": [NOW - 40 * 86400, NOW - 20 * 86400]}
            )
        ) == [ATTR_DRAFT_IP]

    @pytest.mark.parametrize("scopes", [["attributes:read"]])
    def test_pagination(self, client: TestClient, auth_token: auth.Token):
        seen = []
        for page in (1, 2, 3):
            response = self._search(client, auth_token, {"limit": 2, "page": page})
            seen.extend(self._attribute_uuids(response))
        assert sorted(seen) == [ATTR_IP, ATTR_DOMAIN, ATTR_URL, ATTR_DRAFT_IP]

    @pytest.mark.parametrize("scopes", [["attributes:read"]])
    def test_json_shape_with_context(self, client: TestClient, auth_token: auth.Token):
        response = self._search(
            client,
            auth_token,
            {"value": "198.51.100.7", "includeEventTags": 1, "includeContext": 1},
        )
        [attribute] = response.json()["response"]["Attribute"]
        assert attribute["event_id"] == "42"
        assert attribute["timestamp"] == str(NOW - 3600)
        assert attribute["to_ids"] is True
        assert attribute["Event"]["uuid"] == EVENT_PUBLISHED
        assert attribute["Event"]["info"] == "APT29 campaign"
        assert attribute["Event"]["Orgc"]["name"] == "CIRCL"
        tags = {t["name"]: t for t in attribute["Tag"]}
        assert "inherited" not in tags["tlp:amber"]
        assert tags['misp-galaxy:threat-actor="APT29"']["inherited"] == 1

        # Locally-created events have no numeric id: fall back to the uuid.
        [draft] = self._search(client, auth_token, {"value": "203.0.113.9"}).json()[
            "response"
        ]["Attribute"]
        assert draft["event_id"] == EVENT_DRAFT

    @pytest.mark.parametrize("scopes", [["attributes:read"]])
    def test_csv(self, client: TestClient, auth_token: auth.Token):
        response = self._search(
            client, auth_token, {"returnFormat": "csv", "type": "domain"}
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.headers["content-type"].startswith("text/csv")
        rows = list(csv.DictReader(io.StringIO(response.text)))
        assert list(rows[0].keys()) == rest_search_repository.CSV_COLUMNS
        assert rows[0]["value"] == "evil.example.com"
        assert rows[0]["to_ids"] == "1"
        assert rows[0]["event_id"] == "42"
        assert rows[0]["object_name"] == "domain-ip"
        assert rows[0]["object_meta-category"] == "network"

    @pytest.mark.parametrize("scopes", [["attributes:read"]])
    def test_text(self, client: TestClient, auth_token: auth.Token):
        response = self._search(
            client, auth_token, {"returnFormat": "text", "type": "ip-dst"}
        )
        assert response.status_code == status.HTTP_200_OK
        assert sorted(response.text.split()) == ["198.51.100.7", "203.0.113.9"]

    @pytest.mark.parametrize("scopes", [["attributes:read"]])
    def test_invalid_params(self, client: TestClient, auth_token: auth.Token):
        for body in (
            {"returnFormat": "stix2"},
            {"to_ids": "maybe"},
            {"last": "yesterday"},
            {"limit": 0},
            {"tags": {"XOR": ["a"]}},
        ):
            response = self._search(client, auth_token, body)
            assert response.status_code == status.HTTP_400_BAD_REQUEST, body

    @pytest.mark.parametrize("scopes", [["attributes:read"]])
    def test_legacy_request_wrapper(self, client: TestClient, auth_token: auth.Token):
        response = self._search(
            client, auth_token, {"request": {"value": "198.51.100.7"}}
        )
        assert self._attribute_uuids(response) == [ATTR_IP]

    @pytest.mark.parametrize("scopes", [[]])
    def test_requires_scope(self, client: TestClient, auth_token: auth.Token):
        assert (
            self._search(client, auth_token, {}).status_code
            == status.HTTP_401_UNAUTHORIZED
        )
        assert (
            self._search(client, auth_token, {}, path="/events/restSearch").status_code
            == status.HTTP_401_UNAUTHORIZED
        )

    @pytest.mark.parametrize("scopes", [["events:read"]])
    def test_events_search(self, client: TestClient, auth_token: auth.Token):
        response = self._search(
            client, auth_token, {"published": 1}, path="/events/restSearch"
        )
        assert response.status_code == status.HTTP_200_OK, response.text
        [event] = response.json()["response"]
        assert event["Event"]["uuid"] == EVENT_PUBLISHED
        assert event["Event"]["id"] == "42"
        assert sorted(a["uuid"] for a in event["Event"]["Attribute"]) == [
            ATTR_IP,
            ATTR_URL,
        ]

    @pytest.mark.parametrize("scopes", [["events:read"]])
    def test_events_search_by_attribute_value(
        self, client: TestClient, auth_token: auth.Token
    ):
        response = self._search(
            client,
            auth_token,
            {"value": "203.0.113.9", "metadata": 1},
            path="/events/restSearch",
        )
        [event] = response.json()["response"]
        assert event["Event"]["uuid"] == EVENT_DRAFT
        assert event["Event"]["Attribute"] == []

    @pytest.mark.parametrize("scopes", [["events:read"]])
    def test_events_search_by_tag(self, client: TestClient, auth_token: auth.Token):
        response = self._search(
            client, auth_token, {"tags": "!%APT29%"}, path="/events/restSearch"
        )
        assert [e["Event"]["uuid"] for e in response.json()["response"]] == [
            EVENT_DRAFT
        ]


class TestRestSearchParsing:
    def test_split_filter(self):
        split = rest_search_repository._split_filter
        assert split(["a", "!b"]) == (["a"], [], ["b"])
        assert split({"OR": "a", "AND": ["b", "c"], "NOT": ["d"]}) == (
            ["a"],
            ["b", "c"],
            ["d"],
        )
        assert split(None) == ([], [], [])

    def test_parse_timestamp(self):
        parse = rest_search_repository._parse_timestamp
        assert parse("1700000000", "t") == 1700000000
        assert parse("7d", "t", now=1_000_000) == 1_000_000 - 7 * 86400
        assert parse("30m", "t", now=1_000_000) == 1_000_000 - 1800
        assert parse("2024-01-01", "t") == 1704067200
        with pytest.raises(rest_search_repository.RestSearchError):
            parse("soon", "t")

    def test_parse_bool(self):
        parse = rest_search_repository._parse_bool
        assert parse("1", "x") is True
        assert parse(False, "x") is False
        assert parse([0, 1], "x") is None
        assert parse("", "x") is None

    def test_terms_any_chunks_large_sets(self, monkeypatch):
        monkeypatch.setattr(rest_search_repository, "MAX_TERMS_PER_CLAUSE", 2)
        clause = rest_search_repository._terms_any("f", ["a", "b", "c"])
        assert clause["bool"]["should"] == [
            {"terms": {"f": ["a", "b"]}},
            {"terms": {"f": ["c"]}},
        ]

    def test_event_resolver_uses_smaller_side(self):
        class FakeClient:
            def __init__(self):
                self.searched = []

            def count(self, index, body=None):
                return {"count": 9 if body else 10}

            def search(self, index, body):
                self.searched.append(body["query"])
                return {"hits": {"hits": [{"_source": {"uuid": "x"}, "sort": ["x"]}]}}

        fake = FakeClient()
        clause = rest_search_repository._EventResolver(fake).clause(
            {"term": {"published": True}}
        )
        # 9 of 10 events match: fetch the single non-matching one and negate.
        assert clause == {"bool": {"must_not": [{"terms": {"event_uuid": ["x"]}}]}}
        assert fake.searched == [
            {"bool": {"must_not": [{"term": {"published": True}}]}}
        ]
