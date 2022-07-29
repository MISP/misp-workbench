import pytest
from app.auth import auth
from app.models import attribute as attribute_models
from app.models import event as event_models
from app.models import organisation as organisation_models
from app.models import tag as tag_models
from app.models import user as user_models
from app.tests.api_tester import ApiTester
from fastapi import status
from fastapi.testclient import TestClient


class TestEventsResource(ApiTester):
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

        assert response.status_code == status.HTTP_200_OK

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

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.parametrize("scopes", [["events:create"]])
    def test_create_event(
        self,
        client: TestClient,
        organisation_1: organisation_models.Organisation,
        user_1: user_models.User,
        auth_token: auth.Token,
    ):
        response = client.post(
            "/events/",
            json={
                "info": "test create event",
                "user_id": user_1.id,
                "orgc_id": 1,
                "org_id": organisation_1.id,
                "date": "2020-01-01",
            },
            headers={"Authorization": "Bearer " + auth_token},
        )
        data = response.json()

        assert response.status_code == status.HTTP_201_CREATED
        assert data["id"] is not None
        assert data["info"] == "test create event"
        assert data["user_id"] == user_1.id
        assert data["org_id"] == organisation_1.id
        assert data["orgc_id"] == 1

    @pytest.mark.parametrize("scopes", [["events:read"]])
    def test_create_event_unauthorized(
        self,
        client: TestClient,
        organisation_1: organisation_models.Organisation,
        user_1: user_models.User,
        auth_token: auth.Token,
    ):
        response = client.post(
            "/events/",
            json={
                "info": "test create event",
                "user_id": user_1.id,
                "orgc_id": 1,
                "org_id": organisation_1.id,
                "date": "2020-01-01",
            },
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.parametrize("scopes", [["events:create"]])
    def test_create_event_incomplete(self, client: TestClient, auth_token: auth.Token):
        # missing info
        response = client.post(
            "/events/",
            json={"user_id": 1, "orgc_id": 1, "org_id": 1, "date": "2020-01-01"},
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

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

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert data["detail"] == "An event with this info already exists"

    @pytest.mark.parametrize("scopes", [["events:update"]])
    def test_update_event(
        self,
        client: TestClient,
        event_1: event_models.Event,
        auth_token: auth.Token,
    ):
        response = client.patch(
            f"/events/{event_1.id}",
            json={
                "info": "updated via API",
                "published": False,
            },
            headers={"Authorization": "Bearer " + auth_token},
        )
        data = response.json()

        assert response.status_code == status.HTTP_200_OK
        assert data["info"] == "updated via API"
        assert data["published"] is False

    @pytest.mark.parametrize("scopes", [["events:delete"]])
    def test_delete_event(
        self,
        client: TestClient,
        event_1: event_models.Event,
        auth_token: auth.Token,
    ):
        response = client.delete(
            f"/events/{event_1.id}",
            headers={"Authorization": "Bearer " + auth_token},
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT

    @pytest.mark.parametrize("scopes", [["events:update"]])
    def test_tag_event(
        self,
        client: TestClient,
        event_1: event_models.Event,
        tlp_white_tag: tag_models.Tag,
        auth_token: auth.Token,
    ):
        response = client.post(
            f"/events/{event_1.id}/tag/{tlp_white_tag.id}",
            headers={"Authorization": "Bearer " + auth_token},
        )

        assert response.status_code == status.HTTP_201_CREATED
