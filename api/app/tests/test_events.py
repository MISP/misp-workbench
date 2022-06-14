import pytest
from fastapi.testclient import TestClient

from ..auth import auth
from ..models import attribute as attribute_models
from ..models import event as event_models
from ..models import user as user_models
from .api_test import ApiTest


class TestEventsResource(ApiTest):
    @pytest.mark.parametrize("scopes", [["events:read"]])
    def test_get_events(
        self,
        client: TestClient,
        user_1: user_models.User,
        event_1: event_models.Event,
        attribute_1: attribute_models.Attribute,
        auth_token: auth.Token,
    ):
        response = client.get(
            "/events/", headers={"Authorization": "Bearer " + auth_token}
        )
        data = response.json()

        assert response.status_code == 200

        assert len(data) == 1
        assert data[0]["id"] == event_1.id
        assert data[0]["info"] == event_1.info
        assert data[0]["org_id"] == event_1.org_id
        assert data[0]["orgc_id"] == event_1.orgc_id
        assert data[0]["user_id"] == user_1.id
        assert data[0]["attributes"][0]["event_id"] == attribute_1.event_id
        assert data[0]["attributes"][0]["value"] == attribute_1.value
        assert data[0]["attributes"][0]["category"] == attribute_1.category
        assert data[0]["attributes"][0]["type"] == attribute_1.type

    @pytest.mark.parametrize("scopes", [[]])
    def test_get_events_unauthorized(
        self, client: TestClient, user_1: user_models.User, auth_token: auth.Token
    ):
        response = client.get(
            "/events/", headers={"Authorization": "Bearer " + auth_token}
        )
        response.json()

        assert response.status_code == 401

    @pytest.mark.parametrize("scopes", [["events:create"]])
    def test_create_event(
        self, client: TestClient, user_1: user_models.User, auth_token: auth.Token
    ):
        response = client.post(
            "/events/",
            json={
                "info": "test create event",
                "user_id": user_1.id,
                "orgc_id": 1,
                "org_id": 1,
                "date": "2020-01-01",
            },
            headers={"Authorization": "Bearer " + auth_token},
        )
        data = response.json()

        assert response.status_code == 200
        assert data["id"] is not None
        assert data["info"] == "test create event"
        assert data["user_id"] == user_1.id
        assert data["org_id"] == 1
        assert data["orgc_id"] == 1

    @pytest.mark.parametrize("scopes", [["events:read"]])
    def test_create_event_unauthorized(
        self, client: TestClient, user_1: user_models.User, auth_token: auth.Token
    ):
        response = client.post(
            "/events/",
            json={
                "info": "test create event",
                "user_id": user_1.id,
                "orgc_id": 1,
                "org_id": 1,
                "date": "2020-01-01",
            },
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert response.status_code == 401

    @pytest.mark.parametrize("scopes", [["events:create"]])
    def test_create_event_incomplete(self, client: TestClient, auth_token: auth.Token):
        # missing info
        response = client.post(
            "/events/",
            json={"user_id": 1, "orgc_id": 1, "org_id": 1, "date": "2020-01-01"},
            headers={"Authorization": "Bearer " + auth_token},
        )
        response.json()
        assert response.status_code == 422

    @pytest.mark.parametrize("scopes", [["events:create"]])
    def test_create_event_invalid_exists(
        self, client: TestClient, event_1: event_models.Event, auth_token: auth.Token
    ):
        # event with duplicated info
        response = client.post(
            "/events/",
            json={
                "info": event_1.info,
                "user_id": event_1.user_id,
                "org_id": event_1.org_id,
                "orgc_id": event_1.orgc_id,
                "date": "2020-01-01",
            },
            headers={"Authorization": "Bearer " + auth_token},
        )
        data = response.json()

        assert response.status_code == 400
        assert data["detail"] == "An event with this info already exists"
