import pytest
from fastapi.testclient import TestClient

from ..auth import auth
from ..models import user as user_models
from .api_test import ApiTest


class TestUsersResource(ApiTest):
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

    # TODO: add auth token to this test
    def test_create_user(self, client: TestClient):
        response = client.post(
            "/users/",
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

    def test_create_user_incomplete(self, client: TestClient):
        # missing password
        response = client.post("/users/", json={"email": "nopass@example.local"})
        assert response.status_code == 422

    def test_create_user_invalid_exists(self, client: TestClient):
        # user with this email already exists
        response = client.post(
            "/users/",
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
