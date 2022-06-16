import pytest
from fastapi.testclient import TestClient

from ...auth import auth
from ...models import user as user_models
from ..api_tester import ApiTester


class TestUsersResource(ApiTester):
    @pytest.mark.parametrize("scopes", [["users:read"]])
    def test_get_users(
        self, client: TestClient, user_1: user_models.User, auth_token: auth.Token
    ):
        response = client.get(
            "/users/", headers={"Authorization": "Bearer " + auth_token}
        )
        data = response.json()

        assert response.status_code == 200

        assert data not in [None, []]
        assert data[0]["email"] == user_1.email
        assert data[0]["id"] == user_1.id

    @pytest.mark.parametrize("scopes", [[]])
    def test_get_users_unauthorized(self, client: TestClient, auth_token: auth.Token):
        response = client.get(
            "/users/", headers={"Authorization": "Bearer " + auth_token}
        )

        assert response.status_code == 401

    @pytest.mark.parametrize("scopes", [["users:create"]])
    def test_create_user(self, client: TestClient, auth_token: auth.Token):
        response = client.post(
            "/users/",
            headers={"Authorization": "Bearer " + auth_token},
            json={
                "org_id": 1,
                "role_id": 1,
                "email": "foobar@example.local",
                "password": "secret",
            },
        )
        data = response.json()

        assert response.status_code == 200
        assert data["email"] == "foobar@example.local"
        assert data["id"] is not None

    @pytest.mark.parametrize("scopes", [[]])
    def test_create_user_unauthorized(self, client: TestClient, auth_token: auth.Token):
        response = client.post(
            "/users/",
            headers={"Authorization": "Bearer " + auth_token},
            json={
                "org_id": 1,
                "role_id": 1,
                "email": "foobar@example.local",
                "password": "secret",
            },
        )

        assert response.status_code == 401

    @pytest.mark.parametrize("scopes", [["users:create"]])
    def test_create_user_incomplete(self, client: TestClient, auth_token: auth.Token):
        # missing password
        response = client.post(
            "/users/",
            json={"email": "nopass@example.local"},
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert response.status_code == 422

    @pytest.mark.parametrize("scopes", [["users:create"]])
    def test_create_user_invalid_exists(
        self, client: TestClient, auth_token: auth.Token
    ):
        # user with this email already exists
        response = client.post(
            "/users/",
            headers={"Authorization": "Bearer " + auth_token},
            json={
                "org_id": 1,
                "role_id": 1,
                "email": "foo@bar.com",
                "password": "secret",
            },
        )
        data = response.json()

        assert response.status_code == 400
        assert data["detail"] == "Email already registered"
