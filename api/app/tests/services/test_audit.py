from types import SimpleNamespace

import pytest
from app.models import audit_log as audit_log_models
from app.models import user as user_models
from app.services import audit
from app.tests.api_tester import ApiTester
from sqlalchemy.orm import Session


class TestAuditService(ApiTester):
    @pytest.fixture(scope="function", autouse=True)
    def _cleanup_logs(self, db: Session):
        db.query(audit_log_models.AuditLog).delete(synchronize_session=False)
        db.commit()
        yield
        db.query(audit_log_models.AuditLog).delete(synchronize_session=False)
        db.commit()

    def test_record_writes_row(self, db: Session, api_tester_user: user_models.User):
        entry = audit.record(
            db,
            action="api_key.created",
            resource_type="api_key",
            resource_id=42,
            actor_user_id=api_tester_user.id,
            metadata={"name": "test"},
        )
        db.commit()
        db.refresh(entry)

        assert entry.id is not None
        assert entry.action == "api_key.created"
        assert entry.resource_type == "api_key"
        assert entry.resource_id == 42
        assert entry.actor_user_id == api_tester_user.id
        assert entry.actor_type == audit.ACTOR_USER
        assert entry.metadata_ == {"name": "test"}
        assert entry.created_at is not None

    def test_record_rolls_back_with_session(
        self, db: Session, api_tester_user: user_models.User
    ):
        # Caller owns the transaction: if they rollback, the audit entry vanishes.
        audit.record(
            db,
            action="api_key.deleted",
            resource_type="api_key",
            resource_id=99,
            actor_user_id=api_tester_user.id,
        )
        db.rollback()
        assert (
            db.query(audit_log_models.AuditLog)
            .filter_by(resource_id=99)
            .count()
            == 0
        )

    def test_request_context_extracts_ip_and_ua(self):
        req = SimpleNamespace(
            client=SimpleNamespace(host="10.0.0.1"),
            headers={"user-agent": "curl/8.0"},
        )
        ctx = audit.request_context(req)
        assert ctx == {"ip_address": "10.0.0.1", "user_agent": "curl/8.0"}

    def test_request_context_prefers_forwarded_for(self):
        req = SimpleNamespace(
            client=SimpleNamespace(host="10.0.0.1"),
            headers={
                "x-forwarded-for": "203.0.113.5, 10.0.0.1",
                "user-agent": "curl/8.0",
            },
        )
        ctx = audit.request_context(req)
        assert ctx["ip_address"] == "203.0.113.5"

    def test_request_context_handles_none(self):
        assert audit.request_context(None) == {}

    def test_request_context_drops_invalid_ip(self):
        # FastAPI's TestClient sets client.host to the literal "testclient",
        # which PostgreSQL INET rejects. Invalid values must be dropped.
        req = SimpleNamespace(
            client=SimpleNamespace(host="testclient"),
            headers={"user-agent": "pytest"},
        )
        ctx = audit.request_context(req)
        assert ctx["ip_address"] is None
        assert ctx["user_agent"] == "pytest"

    def test_record_supports_system_actor(self, db: Session):
        entry = audit.record(
            db,
            action="feed.fetched",
            resource_type="feed",
            resource_id=1,
            actor_type=audit.ACTOR_SYSTEM,
        )
        db.commit()
        db.refresh(entry)
        assert entry.actor_user_id is None
        assert entry.actor_type == audit.ACTOR_SYSTEM
