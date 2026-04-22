from datetime import datetime, timedelta, timezone

import pytest
from app.auth import auth
from app.models import api_key as api_key_models
from app.models import user as user_models
from app.repositories import api_keys as api_keys_repository
from app.tests.api_tester import ApiTester
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session


class TestApiKeysResource(ApiTester):
    @pytest.fixture(scope="function", autouse=True)
    def _cleanup_keys(self, db: Session, api_tester_user: user_models.User):
        # Each test starts with no keys so counts/assertions stay predictable.
        db.query(api_key_models.ApiKey).filter(
            api_key_models.ApiKey.user_id == api_tester_user.id
        ).delete(synchronize_session=False)
        db.commit()
        yield
        db.query(api_key_models.ApiKey).filter(
            api_key_models.ApiKey.user_id == api_tester_user.id
        ).delete(synchronize_session=False)
        db.commit()

    @pytest.mark.parametrize("scopes", [["api_keys:read"]])
    def test_list_empty(self, client: TestClient, auth_token: auth.Token):
        response = client.get(
            "/api-keys/", headers={"Authorization": "Bearer " + auth_token}
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == []

    @pytest.mark.parametrize("scopes", [[]])
    def test_list_unauthorized(self, client: TestClient, auth_token: auth.Token):
        response = client.get(
            "/api-keys/", headers={"Authorization": "Bearer " + auth_token}
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.parametrize("scopes", [["api_keys:create"]])
    def test_create_returns_raw_token_once(
        self,
        client: TestClient,
        db: Session,
        api_tester_user: user_models.User,
        auth_token: auth.Token,
    ):
        response = client.post(
            "/api-keys/",
            headers={"Authorization": "Bearer " + auth_token},
            json={
                "name": "integration test",
                "scopes": ["events:read"],
            },
        )
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["name"] == "integration test"
        assert data["scopes"] == ["events:read"]
        assert data["user_id"] == api_tester_user.id
        assert data["disabled"] is False

        raw_token = data["token"]
        # MISP-style: 40 hex chars.
        assert len(raw_token) == 40
        assert all(c in "0123456789abcdef" for c in raw_token)

        # Stored only as hash, never in plaintext.
        db_key = db.query(api_key_models.ApiKey).filter_by(id=data["id"]).one()
        assert db_key.hashed_token != raw_token
        assert db_key.hashed_token == api_keys_repository.hash_token(raw_token)

    @pytest.mark.parametrize("scopes", [["api_keys:create"]])
    def test_create_rejects_empty_scopes(
        self, client: TestClient, auth_token: auth.Token
    ):
        response = client.post(
            "/api-keys/",
            headers={"Authorization": "Bearer " + auth_token},
            json={"name": "no scopes", "scopes": []},
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.parametrize("scopes", [["api_keys:create"]])
    def test_create_rejects_unknown_scope(
        self, client: TestClient, auth_token: auth.Token
    ):
        response = client.post(
            "/api-keys/",
            headers={"Authorization": "Bearer " + auth_token},
            json={"name": "bad scope", "scopes": ["not:a:real:scope"]},
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Unknown scopes" in response.json()["detail"]

    @pytest.mark.parametrize("scopes", [["api_keys:create"]])
    def test_create_rejects_scope_exceeding_role(
        self, client: TestClient, auth_token: auth.Token
    ):
        # api_tester_user has role_id=3 (User), which does not include users:create.
        response = client.post(
            "/api-keys/",
            headers={"Authorization": "Bearer " + auth_token},
            json={"name": "privilege escalation", "scopes": ["users:create"]},
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "exceed your role" in response.json()["detail"]

    @pytest.mark.parametrize("scopes", [[]])
    def test_create_unauthorized(self, client: TestClient, auth_token: auth.Token):
        response = client.post(
            "/api-keys/",
            headers={"Authorization": "Bearer " + auth_token},
            json={"name": "nope", "scopes": ["events:read"]},
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.parametrize("scopes", [["api_keys:read"]])
    def test_list_includes_created_key_without_token(
        self,
        client: TestClient,
        db: Session,
        api_tester_user: user_models.User,
        auth_token: auth.Token,
    ):
        db_key, _raw = api_keys_repository.create_key(
            db,
            user_id=api_tester_user.id,
            name="listed",
            scopes=["events:read"],
        )
        response = client.get(
            "/api-keys/", headers={"Authorization": "Bearer " + auth_token}
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 1
        assert data[0]["id"] == db_key.id
        assert data[0]["name"] == "listed"
        assert "token" not in data[0]
        assert "hashed_token" not in data[0]

    @pytest.mark.parametrize("scopes", [["api_keys:delete"]])
    def test_delete_own_key(
        self,
        client: TestClient,
        db: Session,
        api_tester_user: user_models.User,
        auth_token: auth.Token,
    ):
        db_key, _raw = api_keys_repository.create_key(
            db,
            user_id=api_tester_user.id,
            name="to delete",
            scopes=["events:read"],
        )
        response = client.delete(
            f"/api-keys/{db_key.id}",
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert db.query(api_key_models.ApiKey).filter_by(id=db_key.id).first() is None

    @pytest.mark.parametrize("scopes", [["api_keys:delete"]])
    def test_delete_nonexistent_key(
        self, client: TestClient, auth_token: auth.Token
    ):
        response = client.delete(
            "/api-keys/999999",
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.parametrize("scopes", [["api_keys:update"]])
    def test_disable_own_key(
        self,
        client: TestClient,
        db: Session,
        api_tester_user: user_models.User,
        auth_token: auth.Token,
    ):
        db_key, _raw = api_keys_repository.create_key(
            db,
            user_id=api_tester_user.id,
            name="to disable",
            scopes=["events:read"],
        )
        response = client.patch(
            f"/api-keys/{db_key.id}",
            headers={"Authorization": "Bearer " + auth_token},
            json={"disabled": True},
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["disabled"] is True

        db.refresh(db_key)
        assert db_key.disabled is True

    @pytest.mark.parametrize("scopes", [["api_keys:update"]])
    def test_reenable_own_key(
        self,
        client: TestClient,
        db: Session,
        api_tester_user: user_models.User,
        auth_token: auth.Token,
    ):
        db_key, _raw = api_keys_repository.create_key(
            db,
            user_id=api_tester_user.id,
            name="toggle",
            scopes=["events:read"],
        )
        api_keys_repository.set_disabled(db, db_key, True)

        response = client.patch(
            f"/api-keys/{db_key.id}",
            headers={"Authorization": "Bearer " + auth_token},
            json={"disabled": False},
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["disabled"] is False

    @pytest.mark.parametrize("scopes", [["api_keys:update"]])
    def test_update_nonexistent_key(
        self, client: TestClient, auth_token: auth.Token
    ):
        response = client.patch(
            "/api-keys/999999",
            headers={"Authorization": "Bearer " + auth_token},
            json={"disabled": True},
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.parametrize("scopes", [["api_keys:update"]])
    def test_cannot_update_other_users_key(
        self,
        client: TestClient,
        db: Session,
        user_1: user_models.User,
        auth_token: auth.Token,
    ):
        other_key, _raw = api_keys_repository.create_key(
            db, user_id=user_1.id, name="not mine", scopes=["events:read"]
        )
        response = client.patch(
            f"/api-keys/{other_key.id}",
            headers={"Authorization": "Bearer " + auth_token},
            json={"disabled": True},
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND
        db.refresh(other_key)
        assert other_key.disabled is False

    @pytest.mark.parametrize("scopes", [[]])
    def test_update_unauthorized(self, client: TestClient, auth_token: auth.Token):
        response = client.patch(
            "/api-keys/1",
            headers={"Authorization": "Bearer " + auth_token},
            json={"disabled": True},
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.parametrize("scopes", [["api_keys:delete"]])
    def test_cannot_delete_other_users_key(
        self,
        client: TestClient,
        db: Session,
        user_1: user_models.User,
        auth_token: auth.Token,
    ):
        # user_1 is a different user — its keys must be invisible to api_tester_user.
        other_key, _raw = api_keys_repository.create_key(
            db, user_id=user_1.id, name="not mine", scopes=["events:read"]
        )
        response = client.delete(
            f"/api-keys/{other_key.id}",
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert (
            db.query(api_key_models.ApiKey).filter_by(id=other_key.id).first()
            is not None
        )


class TestApiKeyAuthentication(ApiTester):
    """End-to-end checks: use a raw API key as the Authorization header."""

    @pytest.fixture(scope="function", autouse=True)
    def _cleanup_keys(self, db: Session, api_tester_user: user_models.User):
        db.query(api_key_models.ApiKey).filter(
            api_key_models.ApiKey.user_id == api_tester_user.id
        ).delete(synchronize_session=False)
        db.commit()
        yield
        db.query(api_key_models.ApiKey).filter(
            api_key_models.ApiKey.user_id == api_tester_user.id
        ).delete(synchronize_session=False)
        db.commit()

    def _make_key(
        self,
        db: Session,
        user: user_models.User,
        scopes: list[str],
        *,
        expires_at=None,
        disabled: bool = False,
    ) -> tuple[api_key_models.ApiKey, str]:
        db_key, raw = api_keys_repository.create_key(
            db,
            user_id=user.id,
            name="auth-test",
            scopes=scopes,
            expires_at=expires_at,
        )
        if disabled:
            db_key.disabled = True
            db.add(db_key)
            db.commit()
            db.refresh(db_key)
        return db_key, raw

    def test_raw_token_authenticates_without_bearer_prefix(
        self,
        client: TestClient,
        db: Session,
        api_tester_user: user_models.User,
    ):
        _db_key, raw = self._make_key(db, api_tester_user, ["api_keys:read"])
        response = client.get("/api-keys/", headers={"Authorization": raw})
        assert response.status_code == status.HTTP_200_OK

    def test_raw_token_also_accepts_bearer_prefix(
        self,
        client: TestClient,
        db: Session,
        api_tester_user: user_models.User,
    ):
        _db_key, raw = self._make_key(db, api_tester_user, ["api_keys:read"])
        response = client.get(
            "/api-keys/", headers={"Authorization": f"Bearer {raw}"}
        )
        assert response.status_code == status.HTTP_200_OK

    def test_invalid_token_rejected(self, client: TestClient):
        response = client.get(
            "/api-keys/", headers={"Authorization": "a" * 40}
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_missing_authorization_rejected(self, client: TestClient):
        response = client.get("/api-keys/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_non_bearer_scheme_rejected(
        self,
        client: TestClient,
        db: Session,
        api_tester_user: user_models.User,
    ):
        # Even if the credential portion happens to be a valid raw token,
        # a non-Bearer scheme must not be treated as an API key.
        _db_key, raw = self._make_key(db, api_tester_user, ["api_keys:read"])
        response = client.get(
            "/api-keys/", headers={"Authorization": f"Basic {raw}"}
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_raw_token_with_invalid_format_rejected(self, client: TestClient):
        # Not 40 hex chars — must not reach the hash lookup.
        response = client.get(
            "/api-keys/", headers={"Authorization": "not-a-real-token"}
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_disabled_key_rejected(
        self,
        client: TestClient,
        db: Session,
        api_tester_user: user_models.User,
    ):
        _db_key, raw = self._make_key(
            db, api_tester_user, ["api_keys:read"], disabled=True
        )
        response = client.get("/api-keys/", headers={"Authorization": raw})
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_expired_key_rejected(
        self,
        client: TestClient,
        db: Session,
        api_tester_user: user_models.User,
    ):
        expired = datetime.now(timezone.utc) - timedelta(hours=1)
        _db_key, raw = self._make_key(
            db, api_tester_user, ["api_keys:read"], expires_at=expired
        )
        response = client.get("/api-keys/", headers={"Authorization": raw})
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_key_without_scope_cannot_access_protected_endpoint(
        self,
        client: TestClient,
        db: Session,
        api_tester_user: user_models.User,
    ):
        # Key only grants events:read, so api_keys:read must be denied
        # even though the owner's role permits it.
        _db_key, raw = self._make_key(db, api_tester_user, ["events:read"])
        response = client.get("/api-keys/", headers={"Authorization": raw})
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_key_scope_intersected_with_role(
        self,
        client: TestClient,
        db: Session,
        api_tester_user: user_models.User,
    ):
        # Role 3 (api_tester_user) does NOT include users:read. Even if we
        # persist a key with that scope, the role check must still block it.
        db_key, raw = api_keys_repository.create_key(
            db, user_id=api_tester_user.id, name="k", scopes=["users:read"]
        )
        assert db_key.scopes == ["users:read"]

        response = client.get("/users/", headers={"Authorization": raw})
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_last_used_at_updated_on_request(
        self,
        client: TestClient,
        db: Session,
        api_tester_user: user_models.User,
    ):
        db_key, raw = self._make_key(db, api_tester_user, ["api_keys:read"])
        assert db_key.last_used_at is None

        response = client.get("/api-keys/", headers={"Authorization": raw})
        assert response.status_code == status.HTTP_200_OK

        db.refresh(db_key)
        assert db_key.last_used_at is not None
