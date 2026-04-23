from datetime import datetime, timedelta, timezone

import pytest
from app.auth import auth
from app.models import audit_log as audit_log_models
from app.models import user as user_models
from app.services import audit
from app.tests.api_tester import ApiTester
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session


def _seed(
    db: Session,
    *,
    action: str,
    resource_type: str = "test",
    resource_id: int | None = None,
    actor_user_id: int | None = None,
    actor_type: str = audit.ACTOR_USER,
    metadata: dict | None = None,
    created_at: datetime | None = None,
) -> audit_log_models.AuditLog:
    entry = audit_log_models.AuditLog(
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        actor_user_id=actor_user_id,
        actor_type=actor_type,
        metadata_=metadata,
    )
    if created_at is not None:
        entry.created_at = created_at
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


class TestAuditLogsAdminResource(ApiTester):
    @pytest.fixture(scope="function", autouse=True)
    def _cleanup_logs(self, db: Session):
        db.query(audit_log_models.AuditLog).delete(synchronize_session=False)
        db.commit()
        yield
        db.query(audit_log_models.AuditLog).delete(synchronize_session=False)
        db.commit()

    @pytest.mark.parametrize("scopes", [["audit_logs:admin"]])
    def test_list_empty(self, client: TestClient, auth_token: auth.Token):
        response = client.get(
            "/admin/audit-logs/",
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0

    @pytest.mark.parametrize("scopes", [[]])
    def test_list_unauthorized(self, client: TestClient, auth_token: auth.Token):
        response = client.get(
            "/admin/audit-logs/",
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.parametrize("scopes", [["api_keys:admin"]])
    def test_other_admin_scopes_cannot_reach_endpoint(
        self, client: TestClient, auth_token: auth.Token
    ):
        # Having a different admin scope must not grant access to audit logs.
        response = client.get(
            "/admin/audit-logs/",
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.parametrize("scopes", [["audit_logs:admin"]])
    def test_list_returns_entries_newest_first(
        self,
        client: TestClient,
        db: Session,
        api_tester_user: user_models.User,
        auth_token: auth.Token,
    ):
        older = _seed(
            db,
            action="api_key.created",
            resource_type="api_key",
            resource_id=1,
            actor_user_id=api_tester_user.id,
            created_at=datetime.now(timezone.utc) - timedelta(hours=1),
        )
        newer = _seed(
            db,
            action="api_key.deleted",
            resource_type="api_key",
            resource_id=1,
            actor_user_id=api_tester_user.id,
        )

        response = client.get(
            "/admin/audit-logs/",
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 2
        assert [row["id"] for row in data["items"]] == [newer.id, older.id]
        # Actor email is surfaced from the relationship for convenience.
        assert data["items"][0]["actor_email"] == api_tester_user.email

    @pytest.mark.parametrize("scopes", [["audit_logs:admin"]])
    def test_filter_by_action_prefix(
        self,
        client: TestClient,
        db: Session,
        api_tester_user: user_models.User,
        auth_token: auth.Token,
    ):
        _seed(db, action="api_key.created", resource_type="api_key", resource_id=1)
        _seed(db, action="api_key.deleted", resource_type="api_key", resource_id=1)
        _seed(db, action="user.login", resource_type="user", resource_id=api_tester_user.id)

        response = client.get(
            "/admin/audit-logs/?action=api_key.",
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 2
        assert {row["action"] for row in data["items"]} == {
            "api_key.created",
            "api_key.deleted",
        }

    @pytest.mark.parametrize("scopes", [["audit_logs:admin"]])
    def test_filter_by_resource(
        self,
        client: TestClient,
        db: Session,
        auth_token: auth.Token,
    ):
        _seed(db, action="api_key.created", resource_type="api_key", resource_id=1)
        _seed(db, action="api_key.created", resource_type="api_key", resource_id=2)
        _seed(db, action="user.login", resource_type="user", resource_id=1)

        response = client.get(
            "/admin/audit-logs/?resource_type=api_key&resource_id=2",
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["resource_id"] == 2

    @pytest.mark.parametrize("scopes", [["audit_logs:admin"]])
    def test_filter_by_actor_user(
        self,
        client: TestClient,
        db: Session,
        api_tester_user: user_models.User,
        user_1: user_models.User,
        auth_token: auth.Token,
    ):
        _seed(db, action="user.login", actor_user_id=api_tester_user.id)
        _seed(db, action="user.login", actor_user_id=user_1.id)

        response = client.get(
            f"/admin/audit-logs/?actor_user_id={user_1.id}",
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["actor_user_id"] == user_1.id
        assert data["items"][0]["actor_email"] == user_1.email

    @pytest.mark.parametrize("scopes", [["audit_logs:admin"]])
    def test_filter_by_actor_type(
        self,
        client: TestClient,
        db: Session,
        auth_token: auth.Token,
    ):
        _seed(db, action="feed.fetched", actor_type=audit.ACTOR_SYSTEM)
        _seed(db, action="api_key.authenticated", actor_type=audit.ACTOR_API_KEY)
        _seed(db, action="user.login", actor_type=audit.ACTOR_USER)

        response = client.get(
            "/admin/audit-logs/?actor_type=system",
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["action"] == "feed.fetched"

    @pytest.mark.parametrize("scopes", [["audit_logs:admin"]])
    def test_filter_by_date_range(
        self,
        client: TestClient,
        db: Session,
        auth_token: auth.Token,
    ):
        now = datetime.now(timezone.utc)
        _seed(db, action="old", created_at=now - timedelta(days=3))
        _seed(db, action="recent", created_at=now - timedelta(hours=1))
        _seed(db, action="future", created_at=now + timedelta(days=1))

        # Window excludes "old" and "future".
        response = client.get(
            "/admin/audit-logs/",
            params={
                "date_from": (now - timedelta(days=1)).isoformat(),
                "date_to": now.isoformat(),
            },
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["action"] == "recent"

    @pytest.mark.parametrize("scopes", [["audit_logs:admin"]])
    def test_pagination(
        self,
        client: TestClient,
        db: Session,
        auth_token: auth.Token,
    ):
        for i in range(5):
            _seed(db, action=f"test.{i}", resource_id=i)

        response = client.get(
            "/admin/audit-logs/?page=1&size=2",
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 5
        assert data["size"] == 2
        assert len(data["items"]) == 2

    @pytest.mark.parametrize("scopes", [["audit_logs:admin"]])
    def test_entry_serializes_all_fields(
        self,
        client: TestClient,
        db: Session,
        api_tester_user: user_models.User,
        auth_token: auth.Token,
    ):
        _seed(
            db,
            action="api_key.created",
            resource_type="api_key",
            resource_id=42,
            actor_user_id=api_tester_user.id,
            metadata={"name": "test"},
        )
        response = client.get(
            "/admin/audit-logs/",
            headers={"Authorization": "Bearer " + auth_token},
        )
        entry = response.json()["items"][0]
        assert entry["action"] == "api_key.created"
        assert entry["resource_type"] == "api_key"
        assert entry["resource_id"] == 42
        assert entry["actor_user_id"] == api_tester_user.id
        assert entry["actor_email"] == api_tester_user.email
        assert entry["actor_type"] == "user"
        assert entry["metadata"] == {"name": "test"}
        assert "created_at" in entry


class TestAuthEndpointAuditing(ApiTester):
    """Login/logout must emit audit entries capturing who, when, and from where."""

    @pytest.fixture(scope="class")
    def login_user(
        self,
        db: Session,
        organisation_1,
    ):
        # The shared api_tester_user has a non-bcrypt hashed_password, so we
        # create a dedicated user with a real password hash for these tests.
        user = user_models.User(
            org_id=organisation_1.id,
            role_id=3,
            email="login@tester.local",
            hashed_password=auth.get_password_hash("correct horse"),
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        yield user
        db.delete(user)
        db.commit()

    @pytest.fixture(scope="function", autouse=True)
    def _cleanup_logs(self, db: Session):
        db.query(audit_log_models.AuditLog).delete(synchronize_session=False)
        db.commit()
        yield
        db.query(audit_log_models.AuditLog).delete(synchronize_session=False)
        db.commit()

    def test_successful_login_emits_audit_entry(
        self,
        client: TestClient,
        db: Session,
        login_user: user_models.User,
    ):
        response = client.post(
            "/auth/token",
            data={"username": login_user.email, "password": "correct horse"},
        )
        assert response.status_code == status.HTTP_200_OK

        log = (
            db.query(audit_log_models.AuditLog)
            .filter_by(action="user.login", resource_id=login_user.id)
            .one()
        )
        assert log.actor_user_id == login_user.id
        assert log.actor_type == "user"
        assert log.metadata_ == {"email": login_user.email}

    def test_failed_login_emits_audit_entry(
        self,
        client: TestClient,
        db: Session,
        login_user: user_models.User,
    ):
        response = client.post(
            "/auth/token",
            data={"username": login_user.email, "password": "wrong"},
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

        log = (
            db.query(audit_log_models.AuditLog)
            .filter_by(action="user.login_failed")
            .one()
        )
        # No actor_user_id on failure — we don't want to confirm the account
        # exists just because authentication was attempted with that email.
        assert log.actor_user_id is None
        assert log.actor_type == "user"
        assert log.metadata_ == {"email": login_user.email}

    def test_failed_login_for_unknown_email_still_records(
        self,
        client: TestClient,
        db: Session,
    ):
        response = client.post(
            "/auth/token",
            data={"username": "ghost@example.com", "password": "anything"},
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

        log = (
            db.query(audit_log_models.AuditLog)
            .filter_by(action="user.login_failed")
            .one()
        )
        assert log.metadata_ == {"email": "ghost@example.com"}

    def test_logout_emits_audit_entry(
        self,
        client: TestClient,
        db: Session,
        login_user: user_models.User,
    ):
        # Issue a fresh token for login_user and call /auth/logout.
        token = auth.create_access_token(
            data={"sub": login_user.email, "scopes": []},
            expires_delta=timedelta(minutes=5),
        )
        response = client.post(
            "/auth/logout",
            headers={"Authorization": "Bearer " + token},
        )
        assert response.status_code == status.HTTP_204_NO_CONTENT

        log = (
            db.query(audit_log_models.AuditLog)
            .filter_by(action="user.logout", resource_id=login_user.id)
            .one()
        )
        assert log.actor_user_id == login_user.id
        assert log.metadata_ == {"email": login_user.email}
