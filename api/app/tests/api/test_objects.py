import pytest
from app.auth import auth
from app.models import event as event_models
from app.models import object as object_models
from app.tests.api_tester import ApiTester
from fastapi import status
from fastapi.testclient import TestClient


class TestObjectsResource(ApiTester):
    @pytest.mark.parametrize("scopes", [["objects:read"]])
    def test_get_objects(
        self,
        client: TestClient,
        object_1: object_models.Object,
        auth_token: auth.Token,
    ):
        response = client.get(
            "/objects/", headers={"Authorization": "Bearer " + auth_token}
        )
        data = response.json()

        assert response.status_code == status.HTTP_200_OK

        assert len(data['items']) == 1
        assert data['items'][0]["id"] == object_1.id
        assert data['items'][0]["name"] == object_1.name
        assert data['items'][0]["template_version"] == object_1.template_version
        assert data['items'][0]["timestamp"] == object_1.timestamp
        assert data['items'][0]["deleted"] == object_1.deleted

    @pytest.mark.parametrize("scopes", [[]])
    def test_get_objects_unauthorized(self, client: TestClient, auth_token: auth.Token):
        response = client.get(
            "/objects/", headers={"Authorization": "Bearer " + auth_token}
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.parametrize("scopes", [["objects:create"]])
    def test_create_object(
        self, client: TestClient, event_1: event_models.Event, auth_token: auth.Token
    ):
        response = client.post(
            "/objects/",
            json={
                "event_uuid": str(event_1.uuid),
                "name": "test object",
                "template_version": 0,
                "timestamp": 1655283899,
                "deleted": False,
            },
            headers={"Authorization": "Bearer " + auth_token},
        )
        data = response.json()

        assert response.status_code == status.HTTP_201_CREATED
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
                "event_uuid": str(event_1.uuid),
                "name": "test object",
                "template_version": 0,
                "timestamp": 1655283899,
                "deleted": False,
            },
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.parametrize("scopes", [["objects:create"]])
    def test_create_object_incomplete(
        self, client: TestClient, event_1: event_models.Event, auth_token: auth.Token
    ):
        # missing value
        response = client.post(
            "/objects/",
            json={
                "event_uuid": str(event_1.uuid),
            },
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.parametrize("scopes", [["objects:update"]])
    def test_update_object(
        self,
        client: TestClient,
        object_1: object_models.Object,
        auth_token: auth.Token,
    ):
        response = client.patch(
            f"/objects/{object_1.id}",
            json={
                "name": "updated via API",
                "comment": "test comment",
            },
            headers={"Authorization": "Bearer " + auth_token},
        )
        data = response.json()

        assert response.status_code == status.HTTP_200_OK
        assert data["name"] == "updated via API"
        assert data["comment"] == "test comment"

    @pytest.mark.parametrize("scopes", [["objects:delete"]])
    def test_delete_object(
        self,
        client: TestClient,
        object_1: object_models.Object,
        auth_token: auth.Token,
    ):
        response = client.delete(
            f"/objects/{object_1.id}",
            headers={"Authorization": "Bearer " + auth_token},
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT
