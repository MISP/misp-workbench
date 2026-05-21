import io
import json
import tarfile
import zipfile
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
        assert data[0]["event_uuid"] == feed_1.event_uuid
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
    def test_preview_local_source_reads_from_storage(self, client: TestClient, auth_token: auth.Token):
        with patch(
            "app.repositories.feeds.fetch_json_content_from_local",
            return_value=_ARRAY_FEED,
        ):
            response = client.post(
                "/feeds/json/preview",
                json={
                    **_BASE_REQUEST,
                    "input_source": "local",
                    "url": "feed-uploads/abc",
                    "settings": _settings(),
                },
                headers={"Authorization": "Bearer " + auth_token},
            )
        assert response.status_code == status.HTTP_200_OK
        assert len(response.json()["items"]) == 3

    @pytest.mark.parametrize("scopes", [_PREVIEW_SCOPE])
    def test_preview_local_source_missing_key_returns_400(self, client: TestClient, auth_token: auth.Token):
        response = client.post(
            "/feeds/json/preview",
            json={**_BASE_REQUEST, "input_source": "local", "url": "", "settings": _settings()},
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


# ──────────────────────────────────────────────────────────────────────────────
# Local file feed tests
# ──────────────────────────────────────────────────────────────────────────────


_UPLOAD_SCOPE = ["feeds:create"]


def _csv_settings() -> dict:
    """CSV settings shape that the preview processor accepts without raising."""
    return {
        "csvConfig": {
            "mode": "attribute",
            "delimiter": ",",
            "header": False,
            "attribute": {
                "value_column": 0,
                "type": {
                    "strategy": "fixed",
                    "value": "ip-dst",
                    "mappings": [],
                },
                "properties": {
                    # timestamp must be a dict for process_csv_feed_row_to_attribute
                    "timestamp": {"strategy": "fixed", "value": 0},
                    "comment": None,
                    "tags": None,
                    "to_ids": None,
                    "first_seen": None,
                    "last_seen": None,
                },
            },
        }
    }


def _build_misp_zip(members: dict) -> bytes:
    """Return zip bytes whose members map to {filename: bytes}."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, content in members.items():
            zf.writestr(name, content)
    return buf.getvalue()


def _build_misp_targz(members: dict) -> bytes:
    """Return tar.gz bytes whose members map to {filename: bytes}."""
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tf:
        for name, content in members.items():
            data = content.encode() if isinstance(content, str) else content
            info = tarfile.TarInfo(name=name)
            info.size = len(data)
            tf.addfile(info, io.BytesIO(data))
    return buf.getvalue()


class TestFeedUpload(ApiTester):
    @pytest.mark.parametrize("scopes", [_UPLOAD_SCOPE])
    def test_upload_csv_returns_key_and_metadata(
        self, client: TestClient, auth_token: auth.Token
    ):
        stored = {}

        def fake_store(filename, content):
            stored[filename] = content

        with patch(
            "app.repositories.attachments.store_attachment", side_effect=fake_store
        ):
            response = client.post(
                "/feeds/upload",
                files={"file": ("ioc.csv", b"1.2.3.4\n5.6.7.8\n", "text/csv")},
                data={"source_format": "csv"},
                headers={"Authorization": "Bearer " + auth_token},
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["key"].startswith("feed-uploads/")
        assert data["filename"] == "ioc.csv"
        assert data["size"] == len(b"1.2.3.4\n5.6.7.8\n")
        assert data["source_format"] == "csv"
        # CSV is stored as a single blob at the key
        assert data["key"] in stored

    @pytest.mark.parametrize("scopes", [_UPLOAD_SCOPE])
    def test_upload_json_returns_key(
        self, client: TestClient, auth_token: auth.Token
    ):
        with patch("app.repositories.attachments.store_attachment"):
            response = client.post(
                "/feeds/upload",
                files={"file": ("ioc.json", b'[{"v":"1.2.3.4"}]', "application/json")},
                data={"source_format": "json"},
                headers={"Authorization": "Bearer " + auth_token},
            )

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["source_format"] == "json"

    @pytest.mark.parametrize("scopes", [_UPLOAD_SCOPE])
    def test_upload_freetext_returns_key(
        self, client: TestClient, auth_token: auth.Token
    ):
        with patch("app.repositories.attachments.store_attachment"):
            response = client.post(
                "/feeds/upload",
                files={"file": ("ioc.txt", b"example.com\nbad.tld\n", "text/plain")},
                data={"source_format": "freetext"},
                headers={"Authorization": "Bearer " + auth_token},
            )

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["source_format"] == "freetext"

    @pytest.mark.parametrize("scopes", [_UPLOAD_SCOPE])
    def test_upload_misp_zip_extracts_members(
        self, client: TestClient, auth_token: auth.Token
    ):
        zip_bytes = _build_misp_zip({
            "manifest.json": json.dumps({"abc-uuid": {"timestamp": "1"}}),
            "abc-uuid.json": json.dumps({"Event": {"uuid": "abc-uuid"}}),
            "hashes.csv": "abc,def\n",
            # Should be ignored — not a relevant member
            "README.md": "ignore me",
        })

        stored = {}

        def fake_store(filename, content):
            stored[filename] = content

        with patch(
            "app.repositories.attachments.store_attachment", side_effect=fake_store
        ):
            response = client.post(
                "/feeds/upload",
                files={"file": ("feed.zip", zip_bytes, "application/zip")},
                data={"source_format": "misp"},
                headers={"Authorization": "Bearer " + auth_token},
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        key = data["key"]
        assert data["source_format"] == "misp"
        # Each relevant member is stored under the key prefix
        assert f"{key}/manifest.json" in stored
        assert f"{key}/abc-uuid.json" in stored
        assert f"{key}/hashes.csv" in stored
        # README.md is filtered out
        assert f"{key}/README.md" not in stored

    @pytest.mark.parametrize("scopes", [_UPLOAD_SCOPE])
    def test_upload_misp_targz_extracts_members(
        self, client: TestClient, auth_token: auth.Token
    ):
        tar_bytes = _build_misp_targz({
            "manifest.json": json.dumps({"u": {"timestamp": "1"}}),
            "u.json": json.dumps({"Event": {"uuid": "u"}}),
        })

        stored = {}

        def fake_store(filename, content):
            stored[filename] = content

        with patch(
            "app.repositories.attachments.store_attachment", side_effect=fake_store
        ):
            response = client.post(
                "/feeds/upload",
                files={"file": ("feed.tar.gz", tar_bytes, "application/gzip")},
                data={"source_format": "misp"},
                headers={"Authorization": "Bearer " + auth_token},
            )

        assert response.status_code == status.HTTP_200_OK
        key = response.json()["key"]
        assert f"{key}/manifest.json" in stored
        assert f"{key}/u.json" in stored

    @pytest.mark.parametrize("scopes", [_UPLOAD_SCOPE])
    def test_upload_misp_zip_without_manifest_returns_400(
        self, client: TestClient, auth_token: auth.Token
    ):
        zip_bytes = _build_misp_zip({
            "abc-uuid.json": json.dumps({"Event": {"uuid": "abc-uuid"}}),
        })
        with patch("app.repositories.attachments.store_attachment"):
            response = client.post(
                "/feeds/upload",
                files={"file": ("feed.zip", zip_bytes, "application/zip")},
                data={"source_format": "misp"},
                headers={"Authorization": "Bearer " + auth_token},
            )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "manifest.json" in response.json()["detail"]

    @pytest.mark.parametrize("scopes", [_UPLOAD_SCOPE])
    def test_upload_misp_with_non_archive_returns_400(
        self, client: TestClient, auth_token: auth.Token
    ):
        with patch("app.repositories.attachments.store_attachment"):
            response = client.post(
                "/feeds/upload",
                files={"file": ("feed.json", b"{}", "application/json")},
                data={"source_format": "misp"},
                headers={"Authorization": "Bearer " + auth_token},
            )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "archive" in response.json()["detail"].lower()

    @pytest.mark.parametrize("scopes", [_UPLOAD_SCOPE])
    def test_upload_misp_with_corrupt_zip_returns_400(
        self, client: TestClient, auth_token: auth.Token
    ):
        with patch("app.repositories.attachments.store_attachment"):
            response = client.post(
                "/feeds/upload",
                files={"file": ("feed.zip", b"not really a zip", "application/zip")},
                data={"source_format": "misp"},
                headers={"Authorization": "Bearer " + auth_token},
            )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.parametrize("scopes", [_UPLOAD_SCOPE])
    def test_upload_unsupported_source_format_returns_400(
        self, client: TestClient, auth_token: auth.Token
    ):
        with patch("app.repositories.attachments.store_attachment"):
            response = client.post(
                "/feeds/upload",
                files={"file": ("x.bin", b"abc", "application/octet-stream")},
                data={"source_format": "stix"},
                headers={"Authorization": "Bearer " + auth_token},
            )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.parametrize("scopes", [_UPLOAD_SCOPE])
    def test_upload_empty_file_returns_400(
        self, client: TestClient, auth_token: auth.Token
    ):
        with patch("app.repositories.attachments.store_attachment"):
            response = client.post(
                "/feeds/upload",
                files={"file": ("empty.csv", b"", "text/csv")},
                data={"source_format": "csv"},
                headers={"Authorization": "Bearer " + auth_token},
            )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.parametrize("scopes", [[]])
    def test_upload_unauthorized(self, client: TestClient, auth_token: auth.Token):
        response = client.post(
            "/feeds/upload",
            files={"file": ("ioc.csv", b"x", "text/csv")},
            data={"source_format": "csv"},
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestLocalFeedPreview(ApiTester):
    """Preview endpoints reading from local storage instead of network."""

    @pytest.mark.parametrize("scopes", [_PREVIEW_SCOPE])
    def test_csv_preview_local_reads_from_storage(
        self, client: TestClient, auth_token: auth.Token
    ):
        with patch(
            "app.repositories.feeds.fetch_csv_content_from_local",
            return_value=["1.2.3.4", "5.6.7.8", "example.com"],
        ):
            response = client.post(
                "/feeds/csv/preview",
                json={
                    "url": "feed-uploads/abc",
                    "input_source": "local",
                    "settings": _csv_settings(),
                },
                headers={"Authorization": "Bearer " + auth_token},
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["result"] == "success"
        assert len(data["preview"]) == 3
        assert data["preview"][0]["value"] == "1.2.3.4"
        assert data["preview"][0]["type"] == "ip-dst"

    @pytest.mark.parametrize("scopes", [_PREVIEW_SCOPE])
    def test_csv_preview_local_missing_key_returns_400(
        self, client: TestClient, auth_token: auth.Token
    ):
        response = client.post(
            "/feeds/csv/preview",
            json={
                "url": "",
                "input_source": "local",
                "settings": _csv_settings(),
            },
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.parametrize("scopes", [_PREVIEW_SCOPE])
    def test_json_preview_local_reads_from_storage(
        self, client: TestClient, auth_token: auth.Token
    ):
        with patch(
            "app.repositories.feeds.fetch_json_content_from_local",
            return_value=_ARRAY_FEED,
        ):
            response = client.post(
                "/feeds/json/preview",
                json={
                    "url": "feed-uploads/abc",
                    "input_source": "local",
                    "settings": _settings(),
                },
                headers={"Authorization": "Bearer " + auth_token},
            )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["result"] == "success"
        assert len(data["items"]) == 3

    @pytest.mark.parametrize("scopes", [_PREVIEW_SCOPE])
    def test_freetext_preview_local_reads_from_storage(
        self, client: TestClient, auth_token: auth.Token
    ):
        with patch(
            "app.repositories.feeds.fetch_csv_content_from_local",
            return_value=["1.2.3.4", "evil.example.com"],
        ):
            response = client.post(
                "/feeds/freetext/preview",
                json={
                    "url": "feed-uploads/abc",
                    "input_source": "local",
                    "settings": {"freetextConfig": {"type_detection": "automatic"}},
                },
                headers={"Authorization": "Bearer " + auth_token},
            )

        assert response.status_code == status.HTTP_200_OK
        rows = response.json()["rows"]
        assert len(rows) == 2
        assert rows[0]["value"] == "1.2.3.4"
        assert rows[0]["type"] == "ip-src"
        assert rows[1]["value"] == "evil.example.com"
        assert rows[1]["type"] == "domain"

    @pytest.mark.parametrize("scopes", [_PREVIEW_SCOPE])
    def test_freetext_preview_local_missing_key_returns_400(
        self, client: TestClient, auth_token: auth.Token
    ):
        response = client.post(
            "/feeds/freetext/preview",
            json={
                "url": "",
                "input_source": "local",
                "settings": {"freetextConfig": {"type_detection": "automatic"}},
            },
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST


class TestLocalFeedRepoHelpers:
    """Direct tests of the local-storage repo helpers used by feed fetch."""

    def test_fetch_csv_content_from_local_decodes_and_filters_comments(self):
        from app.repositories import feeds as feeds_repository

        content = b"# comment\n1.2.3.4\n\nexample.com\n"
        with patch(
            "app.repositories.feeds.get_attachment", return_value=content
        ):
            lines = feeds_repository.fetch_csv_content_from_local("feed-uploads/x")

        assert lines == ["1.2.3.4", "example.com"]

    def test_fetch_json_content_from_local_returns_decoded_string(self):
        from app.repositories import feeds as feeds_repository

        with patch(
            "app.repositories.feeds.get_attachment", return_value=b'{"k":"v"}'
        ):
            content = feeds_repository.fetch_json_content_from_local("feed-uploads/x")

        assert content == '{"k":"v"}'

    def test_get_local_misp_manifest_parses_json(self):
        from app.repositories import feeds as feeds_repository

        manifest = {"abc-uuid": {"timestamp": "1"}}
        with patch(
            "app.repositories.feeds.get_attachment",
            return_value=json.dumps(manifest).encode(),
        ):
            result = feeds_repository.get_local_misp_manifest("feed-uploads/x")

        assert result == manifest

    def test_get_local_misp_event_parses_json(self):
        from app.repositories import feeds as feeds_repository

        event = {"Event": {"uuid": "abc-uuid", "info": "test"}}
        with patch(
            "app.repositories.feeds.get_attachment",
            return_value=json.dumps(event).encode(),
        ):
            result = feeds_repository.get_local_misp_event(
                "feed-uploads/x", "abc-uuid"
            )

        assert result == event

    def test_get_feed_manifest_local_returns_adapter_response(self):
        from app.repositories import feeds as feeds_repository

        class _Feed:
            url = "feed-uploads/x"
            input_source = "local"
            headers = {}

        manifest = {"e": {"timestamp": "1"}}
        with patch(
            "app.repositories.feeds.get_local_misp_manifest", return_value=manifest
        ):
            response = feeds_repository.get_feed_manifest(_Feed())

        assert response.status_code == 200
        assert response.json() == manifest

    def test_fetch_feed_event_by_uuid_local(self):
        from app.repositories import feeds as feeds_repository

        class _Feed:
            url = "feed-uploads/x"
            input_source = "local"
            headers = {}

        event = {"Event": {"uuid": "abc-uuid"}}
        with patch(
            "app.repositories.feeds.get_local_misp_event", return_value=event
        ):
            result = feeds_repository.fetch_feed_event_by_uuid(_Feed(), "abc-uuid")

        assert result == event

    def test_extract_misp_archive_zip(self):
        from app.repositories import feeds as feeds_repository

        zip_bytes = _build_misp_zip({
            "manifest.json": '{"a":1}',
            "evt.json": '{"e":1}',
            "hashes.csv": "x,y\n",
            "ignored.md": "skip",
        })
        members = feeds_repository._extract_misp_archive(zip_bytes, "feed.zip")
        assert set(members.keys()) == {"manifest.json", "evt.json", "hashes.csv"}

    def test_extract_misp_archive_rejects_unknown_extension(self):
        from fastapi import HTTPException

        from app.repositories import feeds as feeds_repository

        with pytest.raises(HTTPException) as exc:
            feeds_repository._extract_misp_archive(b"\x00\x01", "feed.bin")
        assert exc.value.status_code == status.HTTP_400_BAD_REQUEST

    def test_extract_misp_archive_strips_path_traversal(self):
        from app.repositories import feeds as feeds_repository

        zip_bytes = _build_misp_zip({
            "manifest.json": '{"a":1}',
            "../escape.json": '{"e":1}',
        })
        members = feeds_repository._extract_misp_archive(zip_bytes, "feed.zip")
        # Path-traversal entries are filtered out
        assert "../escape.json" not in members
        assert "escape.json" not in members
        assert "manifest.json" in members

    def test_store_feed_upload_rejects_oversize(self):
        from fastapi import HTTPException

        from app.repositories import feeds as feeds_repository

        class _FakeUpload:
            filename = "big.csv"

            class file:
                @staticmethod
                def read():
                    return b"x" * (feeds_repository.MAX_UPLOAD_BYTES + 1)

        with pytest.raises(HTTPException) as exc:
            feeds_repository.store_feed_upload(_FakeUpload(), "csv")
        assert exc.value.status_code == status.HTTP_400_BAD_REQUEST
