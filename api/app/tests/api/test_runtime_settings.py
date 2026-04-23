import pytest
from app.auth import auth
from app.models import audit_log as audit_log_models
from app.models import setting as setting_models
from app.models import user as user_models
from app.repositories import runtime_settings as runtime_settings_repository
from app.tests.api_tester import ApiTester
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session


class TestRuntimeSettingsResource(ApiTester):
    @pytest.fixture(scope="function", autouse=True)
    def _cleanup(self, db: Session):
        db.query(setting_models.Setting).delete(synchronize_session=False)
        db.query(audit_log_models.AuditLog).delete(synchronize_session=False)
        db.commit()
        yield
        db.query(setting_models.Setting).delete(synchronize_session=False)
        db.query(audit_log_models.AuditLog).delete(synchronize_session=False)
        db.commit()

    @pytest.mark.parametrize("scopes", [["settings:update"]])
    def test_update_new_namespace_records_full_value_as_added(
        self,
        client: TestClient,
        db: Session,
        api_tester_user: user_models.User,
        auth_token: auth.Token,
    ):
        # Namespace 'notifications' has a default, so "previous" is the default.
        # Use a namespace without defaults to exercise the `previous is None` branch.
        response = client.post(
            "/settings/runtime/custom",
            headers={"Authorization": "Bearer " + auth_token},
            json={"foo": 1, "bar": "baz"},
        )
        assert response.status_code == status.HTTP_200_OK

        log = (
            db.query(audit_log_models.AuditLog)
            .filter_by(action="runtime_setting.updated")
            .one()
        )
        assert log.actor_user_id == api_tester_user.id
        assert log.metadata_["namespace"] == "custom"
        # No previous value → whole payload is surfaced as added.
        assert log.metadata_["diff"] == {"added": {"foo": 1, "bar": "baz"}}

    @pytest.mark.parametrize("scopes", [["settings:update"]])
    def test_update_existing_setting_emits_shallow_diff(
        self,
        client: TestClient,
        db: Session,
        api_tester_user: user_models.User,
        auth_token: auth.Token,
    ):
        runtime_settings_repository.set_setting(
            db, "custom", {"a": 1, "b": 2, "c": 3}
        )
        response = client.post(
            "/settings/runtime/custom",
            headers={"Authorization": "Bearer " + auth_token},
            json={"a": 1, "b": 99, "d": 4},
        )
        assert response.status_code == status.HTTP_200_OK

        log = (
            db.query(audit_log_models.AuditLog)
            .filter_by(action="runtime_setting.updated")
            .one()
        )
        diff = log.metadata_["diff"]
        assert diff == {
            "added": {"d": 4},
            "removed": {"c": 3},
            "changed": {"b": {"before": 2, "after": 99}},
        }

    @pytest.mark.parametrize("scopes", [["settings:update"]])
    def test_update_without_changes_emits_empty_diff(
        self,
        client: TestClient,
        db: Session,
        auth_token: auth.Token,
    ):
        runtime_settings_repository.set_setting(db, "custom", {"a": 1})
        response = client.post(
            "/settings/runtime/custom",
            headers={"Authorization": "Bearer " + auth_token},
            json={"a": 1},
        )
        assert response.status_code == status.HTTP_200_OK

        log = (
            db.query(audit_log_models.AuditLog)
            .filter_by(action="runtime_setting.updated")
            .one()
        )
        # Empty diff is still useful for forensics: an admin *saved* the
        # namespace even though nothing changed.
        assert log.metadata_["diff"] == {}

    @pytest.mark.parametrize("scopes", [["settings:delete"]])
    def test_delete_records_previous_value(
        self,
        client: TestClient,
        db: Session,
        api_tester_user: user_models.User,
        auth_token: auth.Token,
    ):
        runtime_settings_repository.set_setting(
            db, "custom", {"token": "keep me for forensics"}
        )
        response = client.delete(
            "/settings/runtime/custom",
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert response.status_code == status.HTTP_200_OK

        log = (
            db.query(audit_log_models.AuditLog)
            .filter_by(action="runtime_setting.deleted")
            .one()
        )
        assert log.actor_user_id == api_tester_user.id
        assert log.metadata_ == {
            "namespace": "custom",
            "previous": {"token": "keep me for forensics"},
        }
        assert (
            db.query(setting_models.Setting).filter_by(namespace="custom").first()
            is None
        )

    @pytest.mark.parametrize("scopes", [[]])
    def test_update_unauthorized(self, client: TestClient, auth_token: auth.Token):
        response = client.post(
            "/settings/runtime/custom",
            headers={"Authorization": "Bearer " + auth_token},
            json={"a": 1},
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.parametrize("scopes", [[]])
    def test_delete_unauthorized(self, client: TestClient, auth_token: auth.Token):
        response = client.delete(
            "/settings/runtime/custom",
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
