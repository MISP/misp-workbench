import pytest
from app.auth import auth
from app.models import organisations as organisation_models
from app.models import user as user_models
from app.tests.api_tester import ApiTester
from fastapi import status
from fastapi.testclient import TestClient


class TestUsersResource(ApiTester):
    @pytest.mark.parametrize("scopes", [["users:read"]])
    def test_get_users(
        self, client: TestClient, user_1: user_models.User, auth_token: auth.Token
    ):
        response = client.get(
            "/users/", headers={"Authorization": "Bearer " + auth_token}
        )
        data = response.json()

        assert response.status_code == status.HTTP_200_OK

        assert data not in [None, []]
        assert data[0]["email"] == user_1.email
        assert data[0]["id"] == user_1.id

    @pytest.mark.parametrize("scopes", [[]])
    def test_get_users_unauthorized(self, client: TestClient, auth_token: auth.Token):
        response = client.get(
            "/users/", headers={"Authorization": "Bearer " + auth_token}
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.parametrize("scopes", [["users:create"]])
    def test_create_user(
        self,
        client: TestClient,
        organisation_1: organisation_models.Organisation,
        auth_token: auth.Token,
    ):
        response = client.post(
            "/users/",
            headers={"Authorization": "Bearer " + auth_token},
            json={
                "org_id": organisation_1.id,
                "role_id": 1,
                "email": "foobar@example.local",
                "password": "secret",
            },
        )
        data = response.json()

        assert response.status_code == status.HTTP_201_CREATED
        assert data["email"] == "foobar@example.local"
        assert data["id"] is not None

    @pytest.mark.parametrize("scopes", [[]])
    def test_create_user_unauthorized(
        self,
        client: TestClient,
        organisation_1: organisation_models.Organisation,
        auth_token: auth.Token,
    ):
        response = client.post(
            "/users/",
            headers={"Authorization": "Bearer " + auth_token},
            json={
                "org_id": organisation_1.id,
                "role_id": 1,
                "email": "foobar@example.local",
                "password": "secret",
            },
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.parametrize("scopes", [["users:create"]])
    def test_create_user_incomplete(self, client: TestClient, auth_token: auth.Token):
        # missing password
        response = client.post(
            "/users/",
            json={"email": "nopass@example.local"},
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.parametrize("scopes", [["users:create"]])
    def test_create_user_invalid_exists(
        self,
        client: TestClient,
        organisation_1: organisation_models.Organisation,
        auth_token: auth.Token,
    ):
        # user with this email already exists
        response = client.post(
            "/users/",
            headers={"Authorization": "Bearer " + auth_token},
            json={
                "org_id": organisation_1.id,
                "role_id": 1,
                "email": "foo@bar.com",
                "password": "secret",
            },
        )
        data = response.json()

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert data["detail"] == "Email already registered"

    @pytest.mark.parametrize("scopes", [["users:update"]])
    def test_update_user(
        self,
        client: TestClient,
        user_1: user_models.User,
        auth_token: auth.Token,
    ):
        response = client.patch(
            f"/users/{user_1.id}",
            json={
                "email": "updated_via_api@foo.local",
            },
            headers={"Authorization": "Bearer " + auth_token},
        )
        data = response.json()

        assert response.status_code == status.HTTP_200_OK
        assert data["email"] == "updated_via_api@foo.local"

    @pytest.mark.parametrize("scopes", [["users:delete"]])
    def test_delete_user(
        self,
        client: TestClient,
        user_1: user_models.User,
        auth_token: auth.Token,
    ):
        response = client.delete(
            f"/users/{user_1.id}",
            headers={"Authorization": "Bearer " + auth_token},
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT
