import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest.mock import patch

import pytest
from celery.exceptions import Retry
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.auth import auth
from app.models import sink as sink_models
from app.repositories import sinks as sinks_repository
from app.schemas import sink as sink_schemas
from app.services.opensearch import get_opensearch_client
from app.services.sinks.transports import SinkDeliveryError
from app.tests.api_tester import ApiTester
from app.worker import tasks

EVENT = "77777777-7777-4777-8777-777777777777"
IDS = "dddddddd-0000-4000-8000-000000000001"
NOT_IDS = "dddddddd-0000-4000-8000-000000000002"
RED = "dddddddd-0000-4000-8000-000000000003"
DELETED = "dddddddd-0000-4000-8000-000000000004"
DOMAIN = "dddddddd-0000-4000-8000-000000000005"

_TAG = {
    "exportable": True,
    "hide_tag": False,
    "is_galaxy": False,
    "is_custom_galaxy": False,
    "local_only": False,
    "colour": "#000000",
}


def _attribute(uuid, value, type_="ip-dst", to_ids=True, tags=(), deleted=False):
    return {
        "uuid": uuid,
        "event_uuid": EVENT,
        "type": type_,
        "category": "Network activity",
        "value": value,
        "to_ids": to_ids,
        "timestamp": 1700000000,
        "comment": "",
        "deleted": deleted,
        "tags": [{"id": i + 1, "name": t, **_TAG} for i, t in enumerate(tags)],
    }


@pytest.fixture
def receiver():
    """A local HTTP endpoint standing in for a SIEM; records what it gets."""
    received = []

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            body = self.rfile.read(int(self.headers["Content-Length"]))
            received.append(json.loads(body))
            self.send_response(200)
            self.end_headers()

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{server.server_port}/hook", received
    server.shutdown()
    server.server_close()


class TestSinks(ApiTester):
    @pytest.fixture(scope="class", autouse=True)
    def dataset(self, cleanup):
        client = get_opensearch_client()
        client.index(
            index="misp-events",
            id=EVENT,
            body={
                "uuid": EVENT,
                "info": "sink delivery test",
                "published": True,
                "deleted": False,
                "threat_level": 2,
                "tags": [],
            },
        )
        for doc in (
            _attribute(IDS, "198.51.100.1"),
            _attribute(NOT_IDS, "198.51.100.2", to_ids=False),
            _attribute(RED, "198.51.100.3", tags=["tlp:red"]),
            _attribute(DELETED, "198.51.100.4", deleted=True),
            _attribute(DOMAIN, "sink.example.com", type_="domain"),
        ):
            client.index(index="misp-attributes", id=doc["uuid"], body=doc)
        client.indices.refresh(index="misp-events")
        client.indices.refresh(index="misp-attributes")
        yield

    @pytest.fixture(autouse=True)
    def _no_sinks(self, db: Session):
        db.query(sink_models.Sink).delete()
        db.commit()
        yield
        db.query(sink_models.Sink).delete()
        db.commit()

    def _create(self, db: Session, **fields) -> sink_models.Sink:
        payload = {"name": "sink", "type": "webhook", "config": {"url": "http://x"}}
        payload.update(fields)
        return sinks_repository.create_sink(db, sink_schemas.SinkCreate(**payload))

    def _headers(self, token):
        return {"Authorization": "Bearer " + token}

    # ── CRUD ─────────────────────────────────────────────────────────────

    @pytest.mark.parametrize(
        "scopes", [["sinks:read", "sinks:create", "sinks:update", "sinks:delete"]]
    )
    def test_crud_masks_and_keeps_secrets(
        self, client: TestClient, auth_token: auth.Token, db: Session
    ):
        created = client.post(
            "/sinks/",
            json={
                "name": "splunk",
                "type": "splunk_hec",
                "config": {
                    "url": "https://splunk:8088/services/collector/event",
                    "token": "t0k",
                },
            },
            headers=self._headers(auth_token),
        )
        assert created.status_code == status.HTTP_201_CREATED, created.text
        sink = created.json()
        assert sink["config"]["token"] == sink_schemas.SECRET_MASK
        assert sink["filters"]["exclude_tags"] == ["tlp:red"]
        assert sink["enabled"] is True

        # Sending the masked config back (what an edit form does) keeps the token.
        updated = client.patch(
            f"/sinks/{sink['id']}",
            json={"name": "splunk prod", "config": sink["config"]},
            headers=self._headers(auth_token),
        )
        assert updated.status_code == status.HTTP_200_OK, updated.text
        assert updated.json()["name"] == "splunk prod"
        db.expire_all()
        assert sinks_repository.get_sink(db, sink["id"]).config["token"] == "t0k"

        rotated = client.patch(
            f"/sinks/{sink['id']}",
            json={"config": {**sink["config"], "token": "n3w"}},
            headers=self._headers(auth_token),
        )
        assert rotated.status_code == status.HTTP_200_OK
        db.expire_all()
        assert sinks_repository.get_sink(db, sink["id"]).config["token"] == "n3w"

        listed = client.get("/sinks/", headers=self._headers(auth_token)).json()
        assert [s["name"] for s in listed] == ["splunk prod"]

        assert (
            client.delete(
                f"/sinks/{sink['id']}", headers=self._headers(auth_token)
            ).status_code
            == status.HTTP_204_NO_CONTENT
        )
        assert (
            client.get(
                f"/sinks/{sink['id']}", headers=self._headers(auth_token)
            ).status_code
            == status.HTTP_404_NOT_FOUND
        )

    @pytest.mark.parametrize("scopes", [["sinks:update"]])
    def test_secret_stays_with_its_destination(
        self, client: TestClient, auth_token: auth.Token, db: Session
    ):
        sink = self._create(
            db,
            type="splunk_hec",
            config={
                "url": "https://splunk.internal:8088/services/collector",
                "token": "t0k",
            },
        )
        masked = {"token": sink_schemas.SECRET_MASK}

        # Repointing with the masked token would hand the stored one to the
        # new host: the token has to be re-entered.
        moved = client.patch(
            f"/sinks/{sink.id}",
            json={"config": {"url": "https://attacker.example/collect", **masked}},
            headers=self._headers(auth_token),
        )
        assert moved.status_code == 422
        assert "re-enter token" in moved.json()["detail"]

        # Same for weakening how the connection is authenticated.
        url = "https://splunk.internal:8088/services/collector"
        for weakened in (
            {"verify_tls": False},
            {"ca_cert": "-----BEGIN CERTIFICATE-----"},
        ):
            response = client.patch(
                f"/sinks/{sink.id}",
                json={"config": {"url": url, **masked, **weakened}},
                headers=self._headers(auth_token),
            )
            assert response.status_code == 422, weakened

        # Omitted settings count as their defaults, not as a change.
        kept = client.patch(
            f"/sinks/{sink.id}",
            json={"config": {"url": url, "index": "intel", **masked}},
            headers=self._headers(auth_token),
        )
        assert kept.status_code == 200, kept.text
        db.expire_all()
        assert (
            sinks_repository.get_sink(db, sink.id)
            .config["url"]
            .startswith("https://splunk.internal")
        )

        # An invalid config never echoes the merged-in secret.
        invalid = client.patch(
            f"/sinks/{sink.id}",
            json={
                "config": {
                    "url": "https://splunk.internal:8088/services/collector",
                    "index": {"not": "a string"},
                    **masked,
                }
            },
            headers=self._headers(auth_token),
        )
        assert invalid.status_code == 422
        assert "t0k" not in invalid.text

        reentered = client.patch(
            f"/sinks/{sink.id}",
            json={
                "config": {"url": "https://splunk2.internal/collector", "token": "n3w"}
            },
            headers=self._headers(auth_token),
        )
        assert reentered.status_code == 200
        db.expire_all()
        assert sinks_repository.get_sink(db, sink.id).config["token"] == "n3w"

    @pytest.mark.parametrize("scopes", [["sinks:create", "sinks:update"]])
    def test_config_validation(
        self, client: TestClient, auth_token: auth.Token, db: Session
    ):
        def create(sink_type, config):
            return client.post(
                "/sinks/",
                json={"name": "x", "type": sink_type, "config": config},
                headers=self._headers(auth_token),
            ).status_code

        assert create("webhook", {"url": "ftp://nope"}) == 422
        assert create("splunk_hec", {"url": "https://s"}) == 422  # no token
        assert create("syslog", {"host": "h", "protocol": "udp", "tls": True}) == 422
        assert create("gelf", {"host": "h", "port": 70000}) == 422
        assert create("carrier_pigeon", {}) == 422

        sink = self._create(db)
        response = client.patch(
            f"/sinks/{sink.id}",
            json={"config": {"url": "not a url"}},
            headers=self._headers(auth_token),
        )
        assert response.status_code == 422

    @pytest.mark.parametrize("scopes", [["sinks:read"]])
    def test_write_scopes_required(self, client: TestClient, auth_token: auth.Token):
        response = client.post(
            "/sinks/",
            json={"name": "x", "type": "webhook", "config": {"url": "http://x"}},
            headers=self._headers(auth_token),
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    # ── Test message ─────────────────────────────────────────────────────

    @pytest.mark.parametrize("scopes", [["sinks:test"]])
    def test_send_test_message(
        self, client: TestClient, auth_token: auth.Token, db: Session, receiver
    ):
        url, received = receiver
        ok = client.post(
            f"/sinks/{self._create(db, config={'url': url}).id}/test",
            headers=self._headers(auth_token),
        )
        assert ok.json() == {"ok": True, "error": None}
        assert received[0]["attributes"][0]["value"] == "192.0.2.1"

        down = self._create(db, type="gelf", config={"host": "127.0.0.1", "port": 9})
        failed = client.post(
            f"/sinks/{down.id}/test", headers=self._headers(auth_token)
        )
        assert failed.json()["ok"] is False
        assert "cannot connect" in failed.json()["error"]

    # ── Delivery ─────────────────────────────────────────────────────────

    def test_delivery_applies_filters(self, db: Session, receiver):
        url, received = receiver
        sink = self._create(db, config={"url": url})
        assert tasks.deliver_to_sink.run(sink.id, EVENT) == 2

        sent = sorted(a["uuid"] for batch in received for a in batch["attributes"])
        # Not sent: not to_ids, tlp:red, soft-deleted.
        assert sent == sorted([IDS, DOMAIN])
        assert received[0]["event"]["info"] == "sink delivery test"

        db.expire_all()
        sink = sinks_repository.get_sink(db, sink.id)
        assert sink.delivered_count == 2
        assert sink.last_success_at is not None
        assert sink.last_error is None

        received.clear()
        typed = self._create(
            db,
            config={"url": url},
            filters={"to_ids_only": False, "types": ["ip-dst"], "exclude_tags": []},
        )
        tasks.deliver_to_sink.run(typed.id, EVENT)
        sent = sorted(a["uuid"] for batch in received for a in batch["attributes"])
        assert sent == sorted([IDS, NOT_IDS, RED])

    def test_failed_delivery_retries_then_gives_up(self, db: Session):
        sink = self._create(db, type="gelf", config={"host": "127.0.0.1", "port": 9})

        # Celery raises Retry from a worker; called directly, the original error.
        with pytest.raises((Retry, SinkDeliveryError)):
            tasks.deliver_to_sink.run(sink.id, EVENT)
        db.expire_all()
        sink = sinks_repository.get_sink(db, sink.id)
        assert "cannot connect" in sink.last_error
        assert sink.failed_count == 0

        # The last attempt records the failure for good instead of retrying.
        tasks.deliver_to_sink.push_request(retries=tasks.SINK_MAX_RETRIES)
        try:
            assert tasks.deliver_to_sink.run(sink.id, EVENT) == 0
        finally:
            tasks.deliver_to_sink.pop_request()
        db.expire_all()
        assert sinks_repository.get_sink(db, sink.id).failed_count == 1

    def test_disabled_sink_is_skipped(self, db: Session, receiver):
        url, received = receiver
        sink = self._create(db, config={"url": url}, enabled=False)
        assert tasks.deliver_to_sink.run(sink.id, EVENT) == 0
        assert received == []

    def test_publish_dispatches_to_enabled_sinks(self, db: Session):
        enabled = self._create(db, name="on")
        self._create(db, name="off", enabled=False)
        with patch.object(tasks.deliver_to_sink, "apply_async") as apply_async:
            assert sinks_repository.dispatch_published_event(db, EVENT) == 1
        apply_async.assert_called_once_with((enabled.id, EVENT), queue="sinks")

    @pytest.mark.parametrize("scopes", [["sinks:test"]])
    def test_replay_endpoint(
        self, client: TestClient, auth_token: auth.Token, db: Session
    ):
        sink = self._create(db)
        with patch.object(tasks.deliver_to_sink, "apply_async") as apply_async:
            apply_async.return_value.id = "task-1"
            response = client.post(
                f"/sinks/{sink.id}/deliver/{EVENT}", headers=self._headers(auth_token)
            )
            missing = client.post(
                f"/sinks/{sink.id}/deliver/00000000-0000-4000-8000-0000000000ff",
                headers=self._headers(auth_token),
            )
        assert response.status_code == status.HTTP_202_ACCEPTED
        assert response.json() == {"task_id": "task-1"}
        apply_async.assert_called_once_with((sink.id, EVENT), queue="sinks")
        assert missing.status_code == status.HTTP_404_NOT_FOUND
