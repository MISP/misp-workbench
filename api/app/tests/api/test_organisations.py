import pytest
from app.auth import auth
from app.models import organisations as organisation_models
from app.tests.api_tester import ApiTester
from fastapi.testclient import TestClient


class TestOrganisationsResource(ApiTester):
    @pytest.mark.parametrize("scopes", [["organisations:read"]])
    def test_get_organisations(
        self,
        client: TestClient,
        organisation_1: organisation_models.Organisation,
        auth_token: auth.Token,
    ):
        response = client.get(
            "/organisations/", headers={"Authorization": "Bearer " + auth_token}
        )
        data = response.json()

        assert response.status_code == 200

        assert len(data) == 1
        assert data[0]["id"] == organisation_1.id
        assert data[0]["name"] == organisation_1.name
        assert data[0]["uuid"] == str(organisation_1.uuid)

    @pytest.mark.parametrize("scopes", [[]])
    def test_get_organisations_unauthorized(
        self, client: TestClient, auth_token: auth.Token
    ):
        response = client.get(
            "/organisations/", headers={"Authorization": "Bearer " + auth_token}
        )

        assert response.status_code == 401

    @pytest.mark.parametrize("scopes", [["organisations:create"]])
    def test_create_organisation(self, client: TestClient, auth_token: auth.Token):
        response = client.post(
            "/organisations/",
            json={
                "name": "test organisation 2",
                "uuid": "fb738155-80c6-481b-bdba-c5b030b7bb5c",
                "date_created": "2020-01-01 01:01:01",
                "date_modified": "2020-01-01 01:01:01",
                "type": "test2",
                "sector": "test2",
                "nationality": "test2",
                "created_by": 1,
                "local": False,
            },
            headers={"Authorization": "Bearer " + auth_token},
        )
        data = response.json()

        assert response.status_code == 200
        assert data["id"] is not None
        assert data["name"] == "test organisation 2"
        assert data["type"] == "test2"
        assert data["sector"] == "test2"
        assert data["nationality"] == "test2"
        assert data["created_by"] == 1
        assert data["local"] is False

    @pytest.mark.parametrize("scopes", [["organisations:read"]])
    def test_create_organisation_unauthorized(
        self, client: TestClient, auth_token: auth.Token
    ):
        response = client.post(
            "/organisations/",
            json={
                "name": "test organisation 2",
                "uuid": "fb738155-80c6-481b-bdba-c5b030b7bb5c",
                "date_created": "2020-01-01 01:01:01",
                "date_modified": "2020-01-01 01:01:01",
                "type": "test2",
                "sector": "test2",
                "nationality": "test2",
                "created_by": 1,
                "local": False,
            },
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert response.status_code == 401

    @pytest.mark.parametrize("scopes", [["organisations:create"]])
    def test_create_organisation_incomplete(
        self, client: TestClient, auth_token: auth.Token
    ):
        # missing value
        response = client.post(
            "/organisations/",
            json={
                "name": "foobar",
            },
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert response.status_code == 422
