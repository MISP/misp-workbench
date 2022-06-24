import pytest
from app.auth import auth
from app.models import organisations as organisation_models
from app.models import server as server_models
from app.tests.api_tester import ApiTester
from fastapi.testclient import TestClient


class TestServersResource(ApiTester):
    @pytest.mark.parametrize("scopes", [["servers:read"]])
    def test_get_servers(
        self,
        client: TestClient,
        server_1: server_models.Server,
        auth_token: auth.Token,
    ):
        response = client.get(
            "/servers/", headers={"Authorization": "Bearer " + auth_token}
        )
        data = response.json()

        assert response.status_code == 200

        assert len(data) == 1
        assert data[0]["id"] == server_1.id
        assert data[0]["name"] == server_1.name
        assert data[0]["url"] == server_1.url
        assert data[0]["org_id"] == server_1.org_id
        assert data[0]["remote_org_id"] == server_1.remote_org_id
        assert data[0]["push"] == server_1.push
        assert data[0]["pull"] == server_1.pull
        assert data[0]["push_sightings"] == server_1.push_sightings
        assert data[0]["push_galaxy_clusters"] == server_1.push_galaxy_clusters
        assert data[0]["pull_galaxy_clusters"] == server_1.pull_galaxy_clusters
        assert data[0]["publish_without_email"] == server_1.publish_without_email
        assert data[0]["self_signed"] == server_1.self_signed
        assert data[0]["internal"] == server_1.internal
        assert data[0]["unpublish_event"] == server_1.unpublish_event
        assert data[0]["skip_proxy"] == server_1.skip_proxy
        assert data[0]["caching_enabled"] == server_1.caching_enabled
        assert data[0]["priority"] == server_1.priority

    @pytest.mark.parametrize("scopes", [[]])
    def test_get_servers_unauthorized(self, client: TestClient, auth_token: auth.Token):
        response = client.get(
            "/servers/", headers={"Authorization": "Bearer " + auth_token}
        )

        assert response.status_code == 401

    @pytest.mark.parametrize("scopes", [["servers:create"]])
    def test_create_server(
        self,
        client: TestClient,
        organisation_1: organisation_models.Organisation,
        auth_token: auth.Token,
    ):
        response = client.post(
            "/servers/",
            json={
                "name": "test",
                "url": "http://localhost",
                "authkey": "JOvupq7Y96531wkWZBrIgbaxqaZIQqaYs9izZJ0g",
                "org_id": organisation_1.id,
                "remote_org_id": 1,
                "push": False,
                "pull": True,
                "push_sightings": False,
                "push_galaxy_clusters": False,
                "pull_galaxy_clusters": False,
                "publish_without_email": True,
                "self_signed": True,
                "internal": True,
                "unpublish_event": False,
                "skip_proxy": False,
                "caching_enabled": False,
                "priority": 0,
            },
            headers={"Authorization": "Bearer " + auth_token},
        )
        data = response.json()

        assert response.status_code == 201
        assert data["id"] is not None
        assert data["name"] == "test"
        assert data["url"] == "http://localhost"
        assert data["org_id"] == organisation_1.id
        assert data["remote_org_id"] == 1
        assert data["push"] is False
        assert data["pull"] is True
        assert data["push_sightings"] is False
        assert data["push_galaxy_clusters"] is False
        assert data["pull_galaxy_clusters"] is False
        assert data["publish_without_email"] is True
        assert data["self_signed"] is True
        assert data["internal"] is True
        assert data["unpublish_event"] is False
        assert data["skip_proxy"] is False
        assert data["caching_enabled"] is False
        assert data["priority"] == 0

    @pytest.mark.parametrize("scopes", [["servers:read"]])
    def test_create_server_unauthorized(
        self, client: TestClient, auth_token: auth.Token
    ):
        response = client.post(
            "/servers/",
            json={
                "name": "test",
                "url": "http://localhost",
                "authkey": "JOvupq7Y96531wkWZBrIgbaxqaZIQqaYs9izZJ0g",
                "org_id": 1,
                "remote_org_id": 1,
                "push": False,
                "pull": True,
                "push_sightings": False,
                "push_galaxy_clusters": False,
                "pull_galaxy_clusters": False,
                "publish_without_email": True,
                "self_signed": True,
                "internal": True,
                "unpublish_event": False,
                "skip_proxy": False,
                "caching_enabled": False,
                "priority": 0,
            },
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert response.status_code == 401

    @pytest.mark.parametrize("scopes", [["servers:create"]])
    def test_create_server_incomplete(self, client: TestClient, auth_token: auth.Token):
        # missing value
        response = client.post(
            "/servers/",
            json={
                "name": "foobar",
            },
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert response.status_code == 422

    @pytest.mark.parametrize("scopes", [["servers:update"]])
    def test_update_server(
        self,
        client: TestClient,
        server_1: server_models.Server,
        auth_token: auth.Token,
    ):
        response = client.patch(
            f"/servers/{server_1.id}",
            json={
                "name": "updated via API",
            },
            headers={"Authorization": "Bearer " + auth_token},
        )
        data = response.json()

        assert response.status_code == 200
        assert data["name"] == "updated via API"
