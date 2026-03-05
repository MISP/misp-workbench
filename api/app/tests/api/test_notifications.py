import pytest
from app.auth import auth
from app.models import notification as notification_models
from app.tests.api_tester import ApiTester
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session


class TestNotificationsResource(ApiTester):
    @pytest.mark.parametrize("scopes", [["notifications:read"]])
    def test_get_notifications(
        self,
        client: TestClient,
        notification_1: notification_models.Notification,
        auth_token: auth.Token,
    ):
        response = client.get(
            "/notifications", headers={"Authorization": "Bearer " + auth_token}
        )
        data = response.json()

        assert response.status_code == status.HTTP_200_OK
        assert len(data["items"]) == 1
        assert data["items"][0]["id"] == notification_1.id
        assert data["items"][0]["type"] == notification_1.type
        assert data["items"][0]["entity_type"] == notification_1.entity_type
        assert data["items"][0]["read"] == notification_1.read

    @pytest.mark.parametrize("scopes", [[]])
    def test_get_notifications_unauthorized(
        self, client: TestClient, auth_token: auth.Token
    ):
        response = client.get(
            "/notifications", headers={"Authorization": "Bearer " + auth_token}
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.parametrize("scopes", [["notifications:read"]])
    def test_get_notifications_filter_by_type(
        self,
        client: TestClient,
        notification_1: notification_models.Notification,
        auth_token: auth.Token,
    ):
        response = client.get(
            "/notifications",
            params={"type": "event.created"},
            headers={"Authorization": "Bearer " + auth_token},
        )
        data = response.json()

        assert response.status_code == status.HTTP_200_OK
        assert len(data["items"]) == 1
        assert data["items"][0]["type"] == "event.created"

    @pytest.mark.parametrize("scopes", [["notifications:read"]])
    def test_get_notifications_filter_by_type_no_match(
        self,
        client: TestClient,
        notification_1: notification_models.Notification,
        auth_token: auth.Token,
    ):
        response = client.get(
            "/notifications",
            params={"type": "hunt.result"},
            headers={"Authorization": "Bearer " + auth_token},
        )
        data = response.json()

        assert response.status_code == status.HTTP_200_OK
        assert len(data["items"]) == 0

    @pytest.mark.parametrize("scopes", [["notifications:read"]])
    def test_get_notifications_filter_by_read_false(
        self,
        client: TestClient,
        notification_1: notification_models.Notification,
        auth_token: auth.Token,
    ):
        response = client.get(
            "/notifications",
            params={"read": False},
            headers={"Authorization": "Bearer " + auth_token},
        )
        data = response.json()

        assert response.status_code == status.HTTP_200_OK
        assert len(data["items"]) == 1

    @pytest.mark.parametrize("scopes", [["notifications:read"]])
    def test_get_notifications_filter_by_read_true(
        self,
        client: TestClient,
        notification_1: notification_models.Notification,
        auth_token: auth.Token,
    ):
        response = client.get(
            "/notifications",
            params={"read": True},
            headers={"Authorization": "Bearer " + auth_token},
        )
        data = response.json()

        assert response.status_code == status.HTTP_200_OK
        assert len(data["items"]) == 0

    @pytest.mark.parametrize("scopes", [["notifications:update"]])
    def test_mark_notification_as_read(
        self,
        client: TestClient,
        notification_1: notification_models.Notification,
        auth_token: auth.Token,
        db: Session,
    ):
        response = client.patch(
            f"/notifications/{notification_1.id}/read",
            headers={"Authorization": "Bearer " + auth_token},
        )
        data = response.json()

        assert response.status_code == status.HTTP_200_OK
        assert data["status"] == "success"

        db.refresh(notification_1)
        assert notification_1.read is True

    @pytest.mark.parametrize("scopes", [[]])
    def test_mark_notification_as_read_unauthorized(
        self,
        client: TestClient,
        notification_1: notification_models.Notification,
        auth_token: auth.Token,
    ):
        response = client.patch(
            f"/notifications/{notification_1.id}/read",
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.parametrize("scopes", [["notifications:update"]])
    def test_mark_notification_as_read_not_found(
        self,
        client: TestClient,
        auth_token: auth.Token,
    ):
        response = client.patch(
            "/notifications/999999/read",
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.parametrize("scopes", [["notifications:update"]])
    def test_mark_all_notifications_as_read(
        self,
        client: TestClient,
        notification_1: notification_models.Notification,
        auth_token: auth.Token,
        db: Session,
    ):
        response = client.patch(
            "/notifications/all/read",
            headers={"Authorization": "Bearer " + auth_token},
        )
        data = response.json()

        assert response.status_code == status.HTTP_200_OK
        assert data["status"] == "success"

        db.refresh(notification_1)
        assert notification_1.read is True

    @pytest.mark.parametrize("scopes", [["notifications:update"]])
    def test_unfollow_notification_not_found(
        self,
        client: TestClient,
        auth_token: auth.Token,
    ):
        response = client.patch(
            "/notifications/999999/unfollow",
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.parametrize("scopes", [[]])
    def test_unfollow_notification_unauthorized(
        self,
        client: TestClient,
        notification_1: notification_models.Notification,
        auth_token: auth.Token,
    ):
        response = client.patch(
            f"/notifications/{notification_1.id}/unfollow",
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.parametrize("scopes", [["notifications:update"]])
    def test_delete_notification(
        self,
        client: TestClient,
        notification_1: notification_models.Notification,
        auth_token: auth.Token,
        db: Session,
    ):
        response = client.delete(
            f"/notifications/{notification_1.id}",
            headers={"Authorization": "Bearer " + auth_token},
        )
        data = response.json()

        assert response.status_code == status.HTTP_200_OK
        assert data["status"] == "success"

        deleted = (
            db.query(notification_models.Notification)
            .filter(notification_models.Notification.id == notification_1.id)
            .first()
        )
        assert deleted is None

    @pytest.mark.parametrize("scopes", [[]])
    def test_delete_notification_unauthorized(
        self,
        client: TestClient,
        notification_1: notification_models.Notification,
        auth_token: auth.Token,
    ):
        response = client.delete(
            f"/notifications/{notification_1.id}",
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.parametrize("scopes", [["notifications:update"]])
    def test_delete_notification_not_found(
        self,
        client: TestClient,
        auth_token: auth.Token,
    ):
        response = client.delete(
            "/notifications/999999",
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.parametrize("scopes", [["notifications:update"]])
    def test_delete_all_notifications(
        self,
        client: TestClient,
        notification_1: notification_models.Notification,
        auth_token: auth.Token,
        db: Session,
    ):
        response = client.delete(
            "/notifications/all",
            headers={"Authorization": "Bearer " + auth_token},
        )
        data = response.json()

        assert response.status_code == status.HTTP_200_OK
        assert data["status"] == "success"

        remaining = (
            db.query(notification_models.Notification)
            .filter(notification_models.Notification.user_id == notification_1.user_id)
            .all()
        )
        assert remaining == []

    @pytest.mark.parametrize("scopes", [[]])
    def test_delete_all_notifications_unauthorized(
        self, client: TestClient, auth_token: auth.Token
    ):
        response = client.delete(
            "/notifications/all",
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
