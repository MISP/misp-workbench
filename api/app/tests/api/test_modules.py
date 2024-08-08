import pytest
from app.auth import auth
from app.models import module as module_models
from app.tests.api_tester import ApiTester
from fastapi import status
from fastapi.testclient import TestClient


class TestModulesResource(ApiTester):
    @pytest.mark.parametrize("scopes", [["modules:read"]])
    def test_get_modules(
        self,
        client: TestClient,
        module_1_settings: module_models.ModuleSettings,
        auth_token: auth.Token,
    ):
        response = client.get(
            "/modules/", headers={"Authorization": "Bearer " + auth_token}
        )
        data = response.json()

        assert response.status_code == status.HTTP_200_OK

        for module in data:
            if module["name"] == module_1_settings.module_name:
                assert module["enabled"] == module_1_settings.enabled
                assert module["config"] == module_1_settings.config

    @pytest.mark.parametrize("scopes", [[]])
    def test_get_modules_unauthorized(self, client: TestClient, auth_token: auth.Token):
        response = client.get(
            "/modules/", headers={"Authorization": "Bearer " + auth_token}
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.parametrize("scopes", [["modules:update"]])
    def test_update_module_settings(
        self,
        client: TestClient,
        module_1_settings: module_models.ModuleSettings,
        auth_token: auth.Token,
    ):
        response = client.patch(
            f"/modules/{module_1_settings.module_name}",
            json={"enabled": False, "config": {"test": "test"}},
            headers={"Authorization": "Bearer " + auth_token},
        )

        assert response.status_code == status.HTTP_200_OK

    @pytest.mark.parametrize("scopes", [["modules:read"]])
    def test_update_module_settings_unauthorized(
        self,
        client: TestClient,
        auth_token: auth.Token,
        module_1_settings: module_models.ModuleSettings,
    ):
        response = client.patch(
            f"/modules/{module_1_settings.module_name}",
            json={"enabled": False},
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.parametrize("scopes", [["modules:query"]])
    def test_query_module(
        self,
        client: TestClient,
        module_1_settings: module_models.ModuleSettings,
        auth_token: auth.Token,
    ):
        response = client.post(
            "/modules/query",
            headers={"Authorization": "Bearer " + auth_token},
            json={
                "module": module_1_settings.module_name,
                "attribute": {"type": "ip-dst", "uuid": "", "value": "8.8.8.8"},
            },
        )
        data = response.json()

        assert response.status_code == status.HTTP_200_OK
        assert data["results"]["Attribute"][0]["value"] == "8.8.8.8"
        assert data["results"]["Object"][0]["name"] == "geolocation"
        assert data["results"]["Object"][1]["name"] == "geolocation"
        assert data["results"]["Object"][2]["name"] == "asn"

    @pytest.mark.parametrize("scopes", [["modules:query"]])
    def test_query_modules_unauthorized(
        self,
        client: TestClient,
        auth_token: auth.Token,
        module_1_settings: module_models.ModuleSettings,
    ):
        response = client.patch(
            "/modules/query",
            json={
                "module": module_1_settings.module_name,
                "attribute": {"type": "ip-dst", "uuid": "", "value": "8.8.8.8"},
            },
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
