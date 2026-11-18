from datetime import datetime, timezone

import pytest
from app.auth import auth
from app.models import api_key as api_key_models
from app.models import notification as notification_models
from app.models import organisation as organisation_models
from app.models import sharing_groups as sharing_groups_models
from app.models import tag as tag_models
from app.models import user as user_models
from app.models import user_setting as user_setting_models
from app.tests.api_tester import ApiTester
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session


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

    @pytest.mark.parametrize("scopes", [["users:update"]])
    def test_reset_password(
        self,
        client: TestClient,
        db,
        user_1: user_models.User,
        auth_token: auth.Token,
    ):
        response = client.post(
            f"/users/{user_1.id}/reset-password",
            json={"password": "newpassword123"},
            headers={"Authorization": "Bearer " + auth_token},
        )

        assert response.status_code == status.HTTP_200_OK
        db.refresh(user_1)
        assert auth.verify_password("newpassword123", user_1.hashed_password)

    @pytest.mark.parametrize("scopes", [["users:update"]])
    def test_reset_password_random(
        self,
        client: TestClient,
        db,
        user_1: user_models.User,
        auth_token: auth.Token,
    ):
        old_hash = user_1.hashed_password

        response = client.post(
            f"/users/{user_1.id}/reset-password",
            json={},
            headers={"Authorization": "Bearer " + auth_token},
        )

        assert response.status_code == status.HTTP_200_OK
        db.refresh(user_1)
        assert user_1.hashed_password != old_hash

    @pytest.mark.parametrize("scopes", [[]])
    def test_reset_password_unauthorized(
        self,
        client: TestClient,
        user_1: user_models.User,
        auth_token: auth.Token,
    ):
        response = client.post(
            f"/users/{user_1.id}/reset-password",
            json={"password": "newpassword123"},
            headers={"Authorization": "Bearer " + auth_token},
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

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

    @pytest.mark.parametrize("scopes", [["users:delete"]])
    def test_delete_user_with_dependent_rows(
        self,
        client: TestClient,
        db: Session,
        organisation_1: organisation_models.Organisation,
        auth_token: auth.Token,
    ):
        owner = user_models.User(
            org_id=organisation_1.id,
            role_id=1,
            email="owner@bar.com",
            hashed_password="secret",
        )
        db.add(owner)
        db.flush()
        now = datetime.now(timezone.utc)
        tag = tag_models.Tag(
            name="created-by-a-deleted-user",
            colour="#ffffff",
            org_id=organisation_1.id,
            user_id=owner.id,
        )
        sharing_group = sharing_groups_models.SharingGroup(
            name="synced by the deleted user",
            org_id=organisation_1.id,
            sync_user_id=owner.id,
            created=now,
            modified=now,
        )
        db.add_all(
            [
                tag,
                sharing_group,
                user_setting_models.UserSetting(
                    user_id=owner.id, namespace="owner-delete-test", value={}
                ),
                notification_models.Notification(
                    user_id=owner.id, type="event.created", payload={}, created_at=now
                ),
                api_key_models.ApiKey(
                    user_id=owner.id, hashed_token="0" * 64, name="owner key"
                ),
            ]
        )
        db.commit()
        owner_id, tag_id, sharing_group_id = owner.id, tag.id, sharing_group.id
        db.expunge_all()

        response = client.delete(
            f"/users/{owner_id}",
            headers={"Authorization": "Bearer " + auth_token},
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert db.get(user_models.User, owner_id) is None
        for model in (
            user_setting_models.UserSetting,
            notification_models.Notification,
            api_key_models.ApiKey,
        ):
            assert db.query(model).filter_by(user_id=owner_id).count() == 0
        # Tags are shared vocabulary and a sharing group only names its sync
        # user: both outlive them.
        kept_tag = db.get(tag_models.Tag, tag_id)
        assert kept_tag is not None and kept_tag.user_id is None
        kept_group = db.get(sharing_groups_models.SharingGroup, sharing_group_id)
        assert kept_group is not None and kept_group.sync_user_id is None
