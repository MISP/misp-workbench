import pytest
from app.auth import auth
from app.models import organisation as organisation_models
from app.models import server as server_models
from app.models import sharing_groups as sharing_groups_models
from app.tests.api_tester import ApiTester
from fastapi import status
from fastapi.testclient import TestClient


class TestSharingGroupsResource(ApiTester):
    @pytest.mark.parametrize("scopes", [["sharing_groups:read"]])
    def test_get_sharing_groups(
        self,
        client: TestClient,
        sharing_group_1: sharing_groups_models.SharingGroup,
        auth_token: auth.Token,
    ):
        response = client.get(
            "/sharing_groups/", headers={"Authorization": "Bearer " + auth_token}
        )
        data = response.json()

        assert response.status_code == status.HTTP_200_OK

        assert len(data) == 1
        assert data[0]["id"] == sharing_group_1.id
        assert data[0]["name"] == sharing_group_1.name
        assert data[0]["releasability"] == sharing_group_1.releasability
        assert data[0]["description"] == sharing_group_1.description
        assert data[0]["uuid"] == str(sharing_group_1.uuid)
        assert data[0]["organisation_uuid"] == str(sharing_group_1.organisation_uuid)
        assert data[0]["org_id"] == sharing_group_1.org_id
        assert data[0]["sync_user_id"] == sharing_group_1.sync_user_id
        assert data[0]["active"] == sharing_group_1.active
        assert data[0]["local"] == sharing_group_1.local
        assert data[0]["roaming"] == sharing_group_1.roaming
        assert data[0]["created"] == sharing_group_1.created.isoformat()
        assert data[0]["modified"] == sharing_group_1.modified.isoformat()

    @pytest.mark.parametrize("scopes", [[]])
    def test_get_sharing_groups_unauthorized(
        self, client: TestClient, auth_token: auth.Token
    ):
        response = client.get(
            "/sharing_groups/", headers={"Authorization": "Bearer " + auth_token}
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.parametrize("scopes", [["sharing_groups:create"]])
    def test_create_sharing_group(
        self,
        client: TestClient,
        organisation_1: organisation_models.Organisation,
        auth_token: auth.Token,
    ):
        response = client.post(
            "/sharing_groups/",
            json={
                "name": "test create sharing group",
                "releasability": "releasability",
                "description": "description",
                "org_id": organisation_1.id,
                "active": True,
                "local": False,
                "roaming": False,
                "created": "2020-01-01 01:01:01",
                "modified": "2020-01-01 01:01:01",
            },
            headers={"Authorization": "Bearer " + auth_token},
        )
        data = response.json()

        assert response.status_code == status.HTTP_201_CREATED
        assert data["name"] == "test create sharing group"
        assert data["releasability"] == "releasability"
        assert data["description"] == "description"
        assert data["org_id"] == organisation_1.id
        assert data["active"] is True
        assert data["local"] is False
        assert data["roaming"] is False

    @pytest.mark.parametrize("scopes", [["sharing_groups:read"]])
    def test_create_sharing_group_unauthorized(
        self,
        client: TestClient,
        organisation_1: organisation_models.Organisation,
        auth_token: auth.Token,
    ):
        response = client.post(
            "/sharing_groups/",
            json={
                "name": "test create sharing group",
                "releasability": "releasability",
                "description": "description",
                "org_id": organisation_1.id,
                "active": True,
                "local": False,
                "roaming": False,
                "created": "2020-01-01 01:01:01",
                "modified": "2020-01-01 01:01:01",
            },
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.parametrize("scopes", [["sharing_groups:create"]])
    def test_create_sharing_group_incomplete(
        self, client: TestClient, auth_token: auth.Token
    ):
        # missing value
        response = client.post(
            "/sharing_groups/",
            json={
                "name": "foobar",
            },
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.parametrize("scopes", [["sharing_groups:update"]])
    def test_add_server_to_sharing_group(
        self,
        client: TestClient,
        sharing_group_1: sharing_groups_models.SharingGroup,
        server_1: server_models.Server,
        auth_token: auth.Token,
    ):
        response = client.post(
            f"/sharing_groups/{sharing_group_1.id}/servers",
            json={"server_id": server_1.id, "all_orgs": False},
            headers={"Authorization": "Bearer " + auth_token},
        )
        data = response.json()

        assert response.status_code == status.HTTP_201_CREATED
        assert data["server_id"] == server_1.id
        assert data["all_orgs"] is False

    @pytest.mark.parametrize("scopes", [[]])
    def test_add_server_to_sharing_group_unauthorized(
        self,
        client: TestClient,
        sharing_group_1: sharing_groups_models.SharingGroup,
        server_1: server_models.Server,
        auth_token: auth.Token,
    ):
        response = client.post(
            f"/sharing_groups/{sharing_group_1.id}/servers",
            json={"server_id": server_1.id, "all_orgs": False},
            headers={"Authorization": "Bearer " + auth_token},
        )
        response.json()

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.parametrize("scopes", [["sharing_groups:update"]])
    def test_add_organisation_to_sharing_group(
        self,
        client: TestClient,
        sharing_group_1: sharing_groups_models.SharingGroup,
        organisation_1: organisation_models.Organisation,
        auth_token: auth.Token,
    ):
        response = client.post(
            f"/sharing_groups/{sharing_group_1.id}/organisations",
            json={"org_id": organisation_1.id, "extend": False},
            headers={"Authorization": "Bearer " + auth_token},
        )
        data = response.json()

        assert response.status_code == status.HTTP_201_CREATED
        assert data["org_id"] == organisation_1.id
        assert data["extend"] is False

    @pytest.mark.parametrize("scopes", [[]])
    def test_add_organisation_to_sharing_group_unauthorized(
        self,
        client: TestClient,
        sharing_group_1: sharing_groups_models.SharingGroup,
        organisation_1: organisation_models.Organisation,
        auth_token: auth.Token,
    ):
        response = client.post(
            f"/sharing_groups/{sharing_group_1.id}/organisations",
            json={"org_id": organisation_1.id, "extend": False},
            headers={"Authorization": "Bearer " + auth_token},
        )
        response.json()

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.parametrize("scopes", [["sharing_groups:update"]])
    def test_update_sharing_group(
        self,
        client: TestClient,
        sharing_group_1: sharing_groups_models.SharingGroup,
        auth_token: auth.Token,
    ):
        response = client.patch(
            f"/sharing_groups/{sharing_group_1.id}",
            json={
                "name": "updated via API",
            },
            headers={"Authorization": "Bearer " + auth_token},
        )
        data = response.json()

        assert response.status_code == status.HTTP_200_OK
        assert data["name"] == "updated via API"

    @pytest.mark.parametrize("scopes", [["sharing_groups:delete"]])
    def test_delete_sharing_group(
        self,
        client: TestClient,
        sharing_group_2: sharing_groups_models.SharingGroup,
        auth_token: auth.Token,
    ):
        response = client.delete(
            f"/sharing_groups/{sharing_group_2.id}",
            headers={"Authorization": "Bearer " + auth_token},
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT
