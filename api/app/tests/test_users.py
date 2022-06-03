from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from ..models import user as user_models
from .api_test import ApiTest


class TestUsersResource(ApiTest):

    def test_get_users(self, client: TestClient, user_1: user_models.User):
        response = client.get("/users/")
        data = response.json()

        assert response.status_code == 200

        assert len(data) == 1
        assert data[0]["email"] == user_1.email
        assert data[0]["id"] == user_1.id

    def test_create_user(self, client: TestClient):
        response = client.post(
            "/users/", json={"email": "foobar@example.local", "password": "secret"}
        )
        data = response.json()

        assert response.status_code == 200
        assert data["email"] == "foobar@example.local"
        assert data["id"] is not None

    def test_create_user_incomplete(self, client: TestClient):
        # missing password
        response = client.post(
            "/users/", json={"email": "nopass@example.local"})
        assert response.status_code == 422

    def test_create_user_invalid_exists(self, client: TestClient):
        # user with this email already exists
        response = client.post(
            "/users/",
            json={
                "email": "foo@bar.com",
                "password": "secret"
            },
        )
        data = response.json()

        assert response.status_code == 400
        assert data["detail"] == "Email already registered"
