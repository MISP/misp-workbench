import json
from unittest.mock import patch

import pytest
from app.auth import auth
from app.models import feed as feed_models
from app.models import organisation as organisation_models
from app.tests.api_tester import ApiTester
from fastapi import status
from fastapi.testclient import TestClient


class TestFeedsResource(ApiTester):
    @pytest.mark.parametrize("scopes", [["feeds:read"]])
    def test_get_feeds(
        self,
        client: TestClient,
        feed_1: feed_models.Feed,
        auth_token: auth.Token,
    ):
        response = client.get(
            "/feeds/", headers={"Authorization": "Bearer " + auth_token}
        )
        data = response.json()

        assert response.status_code == status.HTTP_200_OK

        assert len(data) == 1
        assert data[0]["id"] == feed_1.id
        assert data[0]["name"] == feed_1.name
        assert data[0]["url"] == feed_1.url
        assert data[0]["provider"] == feed_1.provider
        assert data[0]["source_format"] == feed_1.source_format
        assert data[0]["input_source"] == feed_1.input_source
        assert data[0]["rules"] == feed_1.rules
        assert data[0]["enabled"] == feed_1.enabled
        assert data[0]["distribution"] == feed_1.distribution.value
        assert data[0]["sharing_group_id"] == feed_1.sharing_group_id
        assert data[0]["tag_id"] == feed_1.tag_id
        assert data[0]["default"] == feed_1.default
        assert data[0]["fixed_event"] == feed_1.fixed_event
        assert data[0]["delta_merge"] == feed_1.delta_merge
        assert data[0]["event_id"] == feed_1.event_id
        assert data[0]["publish"] == feed_1.publish
        assert data[0]["override_ids"] == feed_1.override_ids
        assert data[0]["settings"] == feed_1.settings
        assert data[0]["delete_local_file"] == feed_1.delete_local_file
        assert data[0]["lookup_visible"] == feed_1.lookup_visible
        assert data[0]["headers"] == feed_1.headers
        assert data[0]["caching_enabled"] == feed_1.caching_enabled
        assert data[0]["force_to_ids"] == feed_1.force_to_ids
        assert data[0]["orgc_id"] == feed_1.orgc_id
        assert data[0]["tag_collection_id"] == feed_1.tag_collection_id
        assert data[0]["cached_elements"] == feed_1.cached_elements
        assert data[0]["coverage_by_other_feeds"] == feed_1.coverage_by_other_feeds

    @pytest.mark.parametrize("scopes", [[]])
    def test_get_feeds_unauthorized(self, client: TestClient, auth_token: auth.Token):
        response = client.get(
            "/feeds/", headers={"Authorization": "Bearer " + auth_token}
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.parametrize("scopes", [["feeds:create"]])
    def test_create_feed(
        self,
        client: TestClient,
        organisation_1: organisation_models.Organisation,
        auth_token: auth.Token,
    ):
        response = client.post(
            "/feeds/",
            json={
                "name": "test",
                "url": "http://localhost",
                "provider": "test",
                "source_format": "misp",
                "input_source": "network",
            },
            headers={"Authorization": "Bearer " + auth_token},
        )
        data = response.json()

        assert response.status_code == status.HTTP_201_CREATED
        assert data["id"] is not None
        assert data["name"] == "test"
        assert data["url"] == "http://localhost"
        assert data["provider"] == "test"
        assert data["source_format"] == "misp"
        assert data["input_source"] == "network"

    @pytest.mark.parametrize("scopes", [["feeds:read"]])
    def test_create_feed_unauthorized(self, client: TestClient, auth_token: auth.Token):
        response = client.post(
            "/feeds/",
            json={
                "name": "test",
                "url": "http://localhost",
                "provider": "test",
                "source_format": "misp",
                "input_source": "network",
            },
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.parametrize("scopes", [["feeds:create"]])
    def test_create_feed_incomplete(self, client: TestClient, auth_token: auth.Token):
        # missing value
        response = client.post(
            "/feeds/",
            json={
                "name": "foobar",
            },
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.parametrize("scopes", [["feeds:update"]])
    def test_update_feed(
        self,
        client: TestClient,
        feed_1: feed_models.Feed,
        auth_token: auth.Token,
    ):
        response = client.patch(
            f"/feeds/{feed_1.id}",
            json={
                "name": "updated via API",
            },
            headers={"Authorization": "Bearer " + auth_token},
        )
        data = response.json()

        assert response.status_code == status.HTTP_200_OK
        assert data["name"] == "updated via API"

    @pytest.mark.parametrize("scopes", [["feeds:delete"]])
    def test_delete_feed(
        self,
        client: TestClient,
        feed_1: feed_models.Feed,
        auth_token: auth.Token,
    ):
        response = client.delete(
            f"/feeds/{feed_1.id}",
            headers={"Authorization": "Bearer " + auth_token},
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT

    @pytest.mark.parametrize("scopes", [["feeds:read"]])
    def test_get_default_feeds(self, client: TestClient, auth_token: auth.Token):
        response = client.get(
            "/feeds/defaults", headers={"Authorization": "Bearer " + auth_token}
        )
        data = response.json()

        assert response.status_code == status.HTTP_200_OK
        assert isinstance(data, list)
        assert len(data) > 0

    @pytest.mark.parametrize("scopes", [["feeds:read"]])
    def test_get_default_feeds_schema(self, client: TestClient, auth_token: auth.Token):
        response = client.get(
            "/feeds/defaults", headers={"Authorization": "Bearer " + auth_token}
        )
        data = response.json()

        required_fields = {"name", "provider", "url", "source_format", "input_source"}
        for feed in data:
            assert required_fields.issubset(feed.keys())
            assert isinstance(feed["name"], str)
            assert isinstance(feed["url"], str)
            assert isinstance(feed["provider"], str)
            assert isinstance(feed["source_format"], str)
            assert isinstance(feed["distribution"], int)
            assert isinstance(feed["rules"], dict)
            assert isinstance(feed["settings"], dict)

    @pytest.mark.parametrize("scopes", [["feeds:read"]])
    def test_get_default_feeds_source_formats(
        self, client: TestClient, auth_token: auth.Token
    ):
        response = client.get(
            "/feeds/defaults", headers={"Authorization": "Bearer " + auth_token}
        )
        data = response.json()

        source_formats = {feed["source_format"] for feed in data}
        assert source_formats.issubset({"misp", "csv", "freetext", "json"})

    @pytest.mark.parametrize("scopes", [[]])
    def test_get_default_feeds_unauthorized(
        self, client: TestClient, auth_token: auth.Token
    ):
        response = client.get(
            "/feeds/defaults", headers={"Authorization": "Bearer " + auth_token}
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


_PREVIEW_SCOPE = ["feeds:preview"]

_BASE_REQUEST = {
    "url": "http://test.local/feed.json",
    "input_source": "network",
}

_ARRAY_FEED = json.dumps([
    {"indicator": "1.2.3.4", "type": "ip-dst"},
    {"indicator": "5.6.7.8", "type": "ip-dst"},
    {"indicator": "example.com", "type": "domain"},
])

_OBJECT_FEED = json.dumps({"indicator": "1.2.3.4", "type": "ip-dst"})

_NDJSON_FEED = '{"indicator":"1.2.3.4"}\n{"indicator":"5.6.7.8"}\n{"indicator":"example.com"}'

_PRIMITIVE_FEED = json.dumps(["1.2.3.4", "5.6.7.8", "example.com"])


def _settings(fmt="array", items_path="", value_field="indicator", type_strategy="fixed",
              type_value="ip-dst", type_field="type", mappings=None):
    return {
        "jsonConfig": {
            "format": fmt,
            "items_path": items_path,
            "attribute": {
                "value": value_field,
                "type": {
                    "strategy": type_strategy,
                    "value": type_value,
                    "field": type_field,
                    "mappings": mappings or [],
                },
                "properties": {"comment": None, "tags": None, "to_ids": None},
            },
        }
    }


class TestJsonFeedPreview(ApiTester):
    @pytest.mark.parametrize("scopes", [_PREVIEW_SCOPE])
    def test_preview_array_feed_fixed_type(self, client: TestClient, auth_token: auth.Token):
        with patch("app.repositories.feeds.fetch_json_content_from_network", return_value=_ARRAY_FEED):
            response = client.post(
                "/feeds/json/preview",
                json={**_BASE_REQUEST, "settings": _settings()},
                headers={"Authorization": "Bearer " + auth_token},
            )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["result"] == "success"
        assert len(data["items"]) == 3
        assert len(data["preview"]) == 3
        assert data["preview"][0]["value"] == "1.2.3.4"
        assert data["preview"][0]["type"] == "ip-dst"

    @pytest.mark.parametrize("scopes", [_PREVIEW_SCOPE])
    def test_preview_array_feed_field_type(self, client: TestClient, auth_token: auth.Token):
        with patch("app.repositories.feeds.fetch_json_content_from_network", return_value=_ARRAY_FEED):
            response = client.post(
                "/feeds/json/preview",
                json={**_BASE_REQUEST, "settings": _settings(type_strategy="field")},
                headers={"Authorization": "Bearer " + auth_token},
            )
        assert response.status_code == status.HTTP_200_OK
        preview = response.json()["preview"]
        assert preview[0]["type"] == "ip-dst"
        assert preview[2]["type"] == "domain"

    @pytest.mark.parametrize("scopes", [_PREVIEW_SCOPE])
    def test_preview_array_feed_type_mappings(self, client: TestClient, auth_token: auth.Token):
        mappings = [{"from": "ip-dst", "to": "ip-src"}]
        with patch("app.repositories.feeds.fetch_json_content_from_network", return_value=_ARRAY_FEED):
            response = client.post(
                "/feeds/json/preview",
                json={**_BASE_REQUEST, "settings": _settings(
                    type_strategy="field", mappings=mappings
                )},
                headers={"Authorization": "Bearer " + auth_token},
            )
        assert response.status_code == status.HTTP_200_OK
        preview = response.json()["preview"]
        assert preview[0]["type"] == "ip-src"
        assert preview[2]["type"] == "domain"  # unmapped passes through

    @pytest.mark.parametrize("scopes", [_PREVIEW_SCOPE])
    def test_preview_object_feed(self, client: TestClient, auth_token: auth.Token):
        with patch("app.repositories.feeds.fetch_json_content_from_network", return_value=_OBJECT_FEED):
            response = client.post(
                "/feeds/json/preview",
                json={**_BASE_REQUEST, "settings": _settings(fmt="object")},
                headers={"Authorization": "Bearer " + auth_token},
            )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["items"]) == 1
        assert data["preview"][0]["value"] == "1.2.3.4"

    @pytest.mark.parametrize("scopes", [_PREVIEW_SCOPE])
    def test_preview_ndjson_feed(self, client: TestClient, auth_token: auth.Token):
        with patch("app.repositories.feeds.fetch_json_content_from_network", return_value=_NDJSON_FEED):
            response = client.post(
                "/feeds/json/preview",
                json={**_BASE_REQUEST, "settings": _settings(fmt="ndjson")},
                headers={"Authorization": "Bearer " + auth_token},
            )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["items"]) == 3
        assert data["preview"][1]["value"] == "5.6.7.8"

    @pytest.mark.parametrize("scopes", [_PREVIEW_SCOPE])
    def test_preview_with_nested_items_path(self, client: TestClient, auth_token: auth.Token):
        feed_data = json.dumps({"response": {"data": [{"indicator": "1.2.3.4"}]}})
        with patch("app.repositories.feeds.fetch_json_content_from_network", return_value=feed_data):
            response = client.post(
                "/feeds/json/preview",
                json={**_BASE_REQUEST, "settings": _settings(items_path="response.data")},
                headers={"Authorization": "Bearer " + auth_token},
            )
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["preview"][0]["value"] == "1.2.3.4"

    @pytest.mark.parametrize("scopes", [_PREVIEW_SCOPE])
    def test_preview_primitive_items(self, client: TestClient, auth_token: auth.Token):
        with patch("app.repositories.feeds.fetch_json_content_from_network", return_value=_PRIMITIVE_FEED):
            response = client.post(
                "/feeds/json/preview",
                json={**_BASE_REQUEST, "settings": _settings(value_field="")},
                headers={"Authorization": "Bearer " + auth_token},
            )
        assert response.status_code == status.HTTP_200_OK
        preview = response.json()["preview"]
        assert preview[0]["value"] == "1.2.3.4"
        assert preview[0]["type"] == "ip-dst"

    @pytest.mark.parametrize("scopes", [_PREVIEW_SCOPE])
    def test_preview_limited_to_5_items(self, client: TestClient, auth_token: auth.Token):
        large_feed = json.dumps([{"indicator": str(i)} for i in range(20)])
        with patch("app.repositories.feeds.fetch_json_content_from_network", return_value=large_feed):
            response = client.post(
                "/feeds/json/preview",
                json={**_BASE_REQUEST, "settings": _settings()},
                headers={"Authorization": "Bearer " + auth_token},
            )
        assert response.status_code == status.HTTP_200_OK
        assert len(response.json()["items"]) == 5

    @pytest.mark.parametrize("scopes", [_PREVIEW_SCOPE])
    def test_preview_wrong_items_path_returns_400(self, client: TestClient, auth_token: auth.Token):
        with patch("app.repositories.feeds.fetch_json_content_from_network", return_value=_ARRAY_FEED):
            response = client.post(
                "/feeds/json/preview",
                json={**_BASE_REQUEST, "settings": _settings(items_path="does.not.exist")},
                headers={"Authorization": "Bearer " + auth_token},
            )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.parametrize("scopes", [_PREVIEW_SCOPE])
    def test_preview_local_source_returns_400(self, client: TestClient, auth_token: auth.Token):
        response = client.post(
            "/feeds/json/preview",
            json={**_BASE_REQUEST, "input_source": "local", "settings": _settings()},
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.parametrize("scopes", [[]])
    def test_preview_unauthorized(self, client: TestClient, auth_token: auth.Token):
        response = client.post(
            "/feeds/json/preview",
            json={**_BASE_REQUEST, "settings": _settings()},
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
