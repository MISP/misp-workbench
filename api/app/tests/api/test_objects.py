import pytest
from app.auth import auth
from app.tests.api_tester import ApiTester
from fastapi import status
from fastapi.testclient import TestClient


class TestObjectsResource(ApiTester):
    @pytest.mark.parametrize("scopes", [["objects:read"]])
    def test_get_objects(
        self,
        client: TestClient,
        object_1,
        auth_token: auth.Token,
    ):
        response = client.get(
            "/objects/", headers={"Authorization": "Bearer " + auth_token}
        )
        data = response.json()

        assert response.status_code == status.HTTP_200_OK

        assert len(data['items']) == 1
        assert data['items'][0]["uuid"] == str(object_1.uuid)
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
        self, client: TestClient, event_1: object, auth_token: auth.Token
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
        assert data["uuid"] is not None
        assert data["event_uuid"] == str(event_1.uuid)
        assert data["template_version"] == 0
        assert data["timestamp"] == 1655283899
        assert data["deleted"] is False

    @pytest.mark.parametrize("scopes", [["objects:read"]])
    def test_create_object_unauthorized(
        self, client: TestClient, event_1: object, auth_token: auth.Token
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
        self, client: TestClient, event_1: object, auth_token: auth.Token
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
        object_1,
        auth_token: auth.Token,
    ):
        response = client.patch(
            f"/objects/{object_1.uuid}",
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
        object_1,
        auth_token: auth.Token,
    ):
        response = client.delete(
            f"/objects/{object_1.uuid}",
            headers={"Authorization": "Bearer " + auth_token},
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT
