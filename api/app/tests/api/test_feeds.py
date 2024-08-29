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
