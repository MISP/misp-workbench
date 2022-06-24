import pytest
from app.auth import auth
from app.models import attribute as attribute_models
from app.models import event as event_models
from app.tests.api_tester import ApiTester
from fastapi.testclient import TestClient


class TestAttributesResource(ApiTester):
    @pytest.mark.parametrize("scopes", [["attributes:read"]])
    def test_get_attributes(
        self,
        client: TestClient,
        attribute_1: attribute_models.Attribute,
        auth_token: auth.Token,
    ):
        response = client.get(
            "/attributes/", headers={"Authorization": "Bearer " + auth_token}
        )
        data = response.json()

        assert response.status_code == 200

        assert len(data) == 1
        assert data[0]["id"] == attribute_1.id
        assert data[0]["category"] == attribute_1.category
        assert data[0]["type"] == attribute_1.type
        assert data[0]["value"] == attribute_1.value

    @pytest.mark.parametrize("scopes", [[]])
    def test_get_attributes_unauthorized(
        self, client: TestClient, auth_token: auth.Token
    ):
        response = client.get(
            "/attributes/", headers={"Authorization": "Bearer " + auth_token}
        )

        assert response.status_code == 401

    @pytest.mark.parametrize("scopes", [["attributes:create"]])
    def test_create_attribute(
        self, client: TestClient, event_1: event_models.Event, auth_token: auth.Token
    ):
        response = client.post(
            "/attributes/",
            json={
                "event_id": event_1.id,
                "category": "Network activity",
                "type": "ip-dst",
                "value": "127.0.0.1",
            },
            headers={"Authorization": "Bearer " + auth_token},
        )
        data = response.json()

        assert response.status_code == 201
        assert data["id"] is not None
        assert data["event_id"] == event_1.id
        assert data["category"] == "Network activity"
        assert data["type"] == "ip-dst"
        assert data["value"] == "127.0.0.1"

    @pytest.mark.parametrize("scopes", [["attributes:read"]])
    def test_create_attribute_unauthorized(
        self, client: TestClient, event_1: event_models.Event, auth_token: auth.Token
    ):
        response = client.post(
            "/attributes/",
            json={
                "event_id": event_1.id,
                "category": "Network activity",
                "type": "ip-dst",
                "value": "127.0.0.1",
            },
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert response.status_code == 401

    @pytest.mark.parametrize("scopes", [["attributes:create"]])
    def test_create_attribute_incomplete(
        self, client: TestClient, event_1: event_models.Event, auth_token: auth.Token
    ):
        # missing value
        response = client.post(
            "/attributes/",
            json={
                "event_id": event_1.id,
                "category": "Network activity",
                "type": "ip-dst",
            },
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert response.status_code == 422

    @pytest.mark.parametrize("scopes", [["attributes:update"]])
    def test_update_attribute(
        self,
        client: TestClient,
        event_1: event_models.Event,
        attribute_1: attribute_models.Attribute,
        auth_token: auth.Token,
    ):
        response = client.patch(
            f"/attributes/{attribute_1.id}",
            json={
                "type": "ip-src",
                "value": "8.8.8.8",
            },
            headers={"Authorization": "Bearer " + auth_token},
        )
        data = response.json()

        assert response.status_code == 200
        assert data["type"] == "ip-src"
        assert data["value"] == "8.8.8.8"
