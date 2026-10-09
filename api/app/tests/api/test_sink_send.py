import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from sqlalchemy.orm import Session

from app.models import audit_log as audit_log_models
from app.models import role as role_models
from app.models import sink as sink_models
from app.models import user as user_models
from app.repositories import runtime_settings as runtime_settings_repository
from app.repositories import sinks as sinks_repository
from app.schemas import sink as sink_schemas
from app.services.opensearch import get_opensearch_client
from app.services.redis import get_redis_client
from app.services.sinks import send
from app.services.tech_lab.reactor.context import ReactorContext
from app.tests.api_tester import ApiTester
from app.worker import tasks
from mwctipy import MwLab

EVENT = "cdcdcdcd-cdcd-4dcd-8dcd-cdcdcdcdcdcd"
IDS = "cdcdcdcd-0000-4000-8000-000000000001"
NOT_IDS = "cdcdcdcd-0000-4000-8000-000000000002"
RED = "cdcdcdcd-0000-4000-8000-000000000003"

_TAG = {
    "exportable": True,
    "hide_tag": False,
    "is_galaxy": False,
    "is_custom_galaxy": False,
    "local_only": False,
    "colour": "#000000",
}


def _attribute(uuid, value, to_ids=True, tags=()):
    return {
        "uuid": uuid,
        "event_uuid": EVENT,
        "type": "ip-dst",
        "category": "Network activity",
        "value": value,
        "to_ids": to_ids,
        "deleted": False,
        "comment": "",
        "timestamp": 1700000000,
        "tags": [{"id": i + 1, "name": t, **_TAG} for i, t in enumerate(tags)],
    }


@pytest.fixture
def receiver():
    received = []

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            received.append(
                json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            )
            self.send_response(200)
            self.end_headers()

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{server.server_port}/hook", received
    server.shutdown()
    server.server_close()


class TestSinkSend(ApiTester):
    @pytest.fixture(scope="class", autouse=True)
    def dataset(self, cleanup):
        client = get_opensearch_client()
        client.index(
            index="misp-events",
            id=EVENT,
            body={"uuid": EVENT, "info": "send test", "deleted": False, "tags": []},
        )
        for doc in (
            _attribute(IDS, "198.51.100.1"),
            _attribute(NOT_IDS, "198.51.100.2", to_ids=False),
            _attribute(RED, "198.51.100.3", tags=["tlp:red"]),
        ):
            client.index(index="misp-attributes", id=doc["uuid"], body=doc)
        client.indices.refresh(index="misp-events")
        client.indices.refresh(index="misp-attributes")
        yield

    @pytest.fixture(scope="class")
    def sender(self, db: Session, organisation_1):
        role = role_models.Role(
            id=31, name="sink sender", scopes=["sinks:send"], default_role=False
        )
        db.add(role)
        db.commit()
        user = user_models.User(
            org_id=organisation_1.id,
            role_id=role.id,
            email="sender@tester.local",
            hashed_password="secret",
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        yield user

    @pytest.fixture(autouse=True)
    def _sinks(self, db: Session):
        db.query(sink_models.Sink).delete()
        db.commit()
        # Rate-limit counters from earlier tests would carry over.
        redis = get_redis_client()
        keys = list(redis.scan_iter("sinks:send:rate:*"))
        if keys:
            redis.delete(*keys)
        yield
        db.query(sink_models.Sink).delete()
        db.commit()

    def _sink(self, db, url="http://x", **fields):
        payload = {"name": "SIEM", "type": "webhook", "config": {"url": url}}
        payload.update(fields)
        return sinks_repository.create_sink(db, sink_schemas.SinkCreate(**payload))

    def _send(self, db, user, **kwargs):
        return send.send_to_sink(db, user_id=user.id, actor_type="test", **kwargs)

    def test_scope_required(self, db: Session, api_tester_user):
        self._sink(db)
        with pytest.raises(send.SinkSendPermissionDenied):
            self._send(
                db,
                api_tester_user,
                sink="SIEM",
                records=[{"value": "x", "type": "ip-dst"}],
            )
        with pytest.raises(send.SinkSendPermissionDenied):
            send.visible_sinks(db, api_tester_user.id)

    def test_listing_never_exposes_config(self, db: Session, sender):
        self._sink(
            db,
            type="splunk_hec",
            config={"url": "https://splunk/services/collector", "token": "t0k"},
        )
        [listed] = send.visible_sinks(db, sender.id)
        assert listed == {
            "id": listed["id"],
            "name": "SIEM",
            "type": "splunk_hec",
            "enabled": True,
        }

    def test_resolution_and_validation(self, db: Session, sender):
        self._sink(db, enabled=False)
        with pytest.raises(send.SinkSendError, match="disabled"):
            self._send(db, sender, sink="SIEM", event_uuid=EVENT)
        with pytest.raises(send.SinkSendError, match="no sink"):
            self._send(db, sender, sink="nope", event_uuid=EVENT)
        with pytest.raises(send.SinkSendError, match="exactly one"):
            self._send(db, sender, sink="SIEM", event_uuid=EVENT, attributes=[IDS])

    def test_queues_in_chunks_and_audits(self, db: Session, sender):
        sink = self._sink(db)
        records = [
            {"value": f"203.0.113.{i % 250}", "type": "ip-dst"} for i in range(2500)
        ]
        with patch.object(tasks.deliver_items_to_sink, "apply_async") as apply_async:
            apply_async.return_value = SimpleNamespace(id="t")
            result = self._send(
                db, sender, sink=sink.id, records=records, apply_filters=False
            )
        assert result == {
            "sink": "SIEM",
            "mode": "records",
            "queued": 2500,
            "task_ids": ["t", "t", "t"],
        }
        sizes = [len(call.args[0][2]) for call in apply_async.call_args_list]
        assert sizes == [1000, 1000, 500]
        assert apply_async.call_args.args[1] == {"apply_filters": False}
        assert apply_async.call_args.kwargs["queue"] == "sinks"

        entry = (
            db.query(audit_log_models.AuditLog)
            .filter(audit_log_models.AuditLog.action == "sink.send")
            .order_by(audit_log_models.AuditLog.id.desc())
            .first()
        )
        assert entry.actor_user_id == sender.id
        assert entry.metadata_["items"] == 2500
        assert entry.metadata_["sink"] == "SIEM"

    def test_size_and_rate_limits(self, db: Session, sender):
        self._sink(db)
        too_many = [{"value": "x", "type": "ip-dst"}] * (send.MAX_ITEMS_PER_SEND + 1)
        with pytest.raises(send.SinkSendError, match="at most"):
            self._send(db, sender, sink="SIEM", records=too_many)

        runtime_settings_repository.set_setting(db, "sinks", {"sends_per_minute": 2})
        try:
            with patch.object(tasks.deliver_to_sink, "apply_async"):
                self._send(db, sender, sink="SIEM", event_uuid=EVENT)
                self._send(db, sender, sink="SIEM", event_uuid=EVENT)
                with pytest.raises(send.SinkSendRateLimited):
                    self._send(db, sender, sink="SIEM", event_uuid=EVENT)
        finally:
            runtime_settings_repository.delete_setting(db, "sinks")

    def test_attribute_delivery_respects_exclusions(self, db: Session, receiver):
        url, received = receiver
        sink = self._sink(db, url=url)

        # Selection applies: only the IDS attribute, never the tlp:red one.
        selected = tasks.deliver_items_to_sink.run(
            sink.id, "attributes", [IDS, NOT_IDS, RED]
        )
        assert selected == 1
        # Selection skipped: the non-IDS one too, tlp:red still excluded.
        unselected = tasks.deliver_items_to_sink.run(
            sink.id, "attributes", [IDS, NOT_IDS, RED], apply_filters=False
        )
        assert unselected == 2
        sent = [a["uuid"] for batch in received for a in batch["attributes"]]
        assert sent == [IDS] + sorted([IDS, NOT_IDS])
        assert received[0]["event"]["info"] == "send test"

    def test_mwlab_and_ctx(self, db: Session, sender):
        self._sink(db)
        lab = MwLab(user_id=sender.id, notebook_id=7)
        assert [s["name"] for s in lab.sinks()] == ["SIEM"]
        with patch.object(tasks.deliver_items_to_sink, "apply_async") as apply_async:
            apply_async.return_value = SimpleNamespace(id="t")
            result = lab.send_to_sink("SIEM", attributes=[{"uuid": IDS}])
        assert result["queued"] == 1

        script = SimpleNamespace(id=5, user_id=sender.id, name="s", max_writes=1)
        run = SimpleNamespace(id=9)
        ctx = ReactorContext(db, script, run)
        with patch.object(tasks.deliver_to_sink, "apply_async") as apply_async:
            apply_async.return_value = SimpleNamespace(id="t")
            result = ctx.send_to_sink("SIEM", event_uuid=EVENT)
            assert result["mode"] == "event"
            # Sends count against the script's write quota.
            with pytest.raises(Exception, match="max_writes"):
                ctx.send_to_sink("SIEM", event_uuid=EVENT)
