import pytest
from fastapi.testclient import TestClient

from ...auth import auth
from ...models import event as event_models
from ...models import object as object_models
from ...models import user as user_models
from .api_test import ApiTest


class TestObjectsResource(ApiTest):
    @pytest.mark.parametrize("scopes", [["objects:read"]])
    def test_get_objects(
        self,
        client: TestClient,
        user_1: user_models.User,
        event_1: event_models.Event,
        object_1: object_models.Object,
        auth_token: auth.Token,
    ):
        response = client.get(
            "/objects/", headers={"Authorization": "Bearer " + auth_token}
        )
        data = response.json()

        assert response.status_code == 200

        assert len(data) == 1
        assert data[0]["id"] == object_1.id
        assert data[0]["name"] == object_1.name
        assert data[0]["template_version"] == object_1.template_version
        assert data[0]["timestamp"] == object_1.timestamp
        assert data[0]["deleted"] == object_1.deleted

    @pytest.mark.parametrize("scopes", [[]])
    def test_get_objects_unauthorized(self, client: TestClient, auth_token: auth.Token):
        response = client.get(
            "/objects/", headers={"Authorization": "Bearer " + auth_token}
        )

        assert response.status_code == 401

    @pytest.mark.parametrize("scopes", [["objects:create"]])
    def test_create_object(
        self, client: TestClient, event_1: event_models.Event, auth_token: auth.Token
    ):
        response = client.post(
            "/objects/",
            json={
                "event_id": event_1.id,
                "name": "test object",
                "template_version": 0,
                "timestamp": 1655283899,
                "deleted": False,
            },
            headers={"Authorization": "Bearer " + auth_token},
        )
        data = response.json()

        assert response.status_code == 200
        assert data["id"] is not None
        assert data["event_id"] == event_1.id
        assert data["template_version"] == 0
        assert data["timestamp"] == 1655283899
        assert data["deleted"] is False

    @pytest.mark.parametrize("scopes", [["objects:read"]])
    def test_create_object_unauthorized(
        self, client: TestClient, event_1: event_models.Event, auth_token: auth.Token
    ):
        response = client.post(
            "/objects/",
            json={
                "event_id": event_1.id,
                "name": "test object",
                "template_version": 0,
                "timestamp": 1655283899,
                "deleted": False,
            },
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert response.status_code == 401

    @pytest.mark.parametrize("scopes", [["objects:create"]])
    def test_create_object_incomplete(
        self, client: TestClient, event_1: event_models.Event, auth_token: auth.Token
    ):
        # missing value
        response = client.post(
            "/objects/",
            json={
                "event_id": event_1.id,
            },
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert response.status_code == 422
