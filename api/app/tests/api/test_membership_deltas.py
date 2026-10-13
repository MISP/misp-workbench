import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest
from fastapi import HTTPException, status
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.auth import auth
from app.models import detection_profile as profile_models
from app.models import export as export_models
from app.models import sink as sink_models
from app.repositories import detection_profiles, exports, indicators
from app.repositories import sinks as sinks_repository
from app.schemas import detection_profile as profile_schemas
from app.schemas import export as export_schemas
from app.schemas import sink as sink_schemas
from app.services import exports_storage
from app.services.opensearch import get_opensearch_client
from app.services.redis import get_redis_client
from app.tests.api_tester import ApiTester

DAY = 86400
NOW = int(time.time())
EVENT = "3e3b0000-0000-4000-8000-000000000001"

STAYS = ("3e3b0000-1000-4000-8000-000000000001", "stays.example")
LEAVES = ("3e3b0000-1000-4000-8000-000000000002", "leaves.example")
JOINS = ("3e3b0000-1000-4000-8000-000000000003", "joins.example")
AGES = ("3e3b0000-1000-4000-8000-000000000004", "ages.example")


def _attribute(key, to_ids=True, timestamp=None, tags=()):
    uuid, value = key
    return {
        "uuid": uuid,
        "event_uuid": EVENT,
        "type": "domain",
        "category": "Network activity",
        "value": value,
        "to_ids": to_ids,
        "deleted": False,
        "comment": "",
        "timestamp": timestamp or NOW - DAY,
        "tags": [{"name": t} for t in tags],
    }


def _write(*docs):
    client = get_opensearch_client()
    for doc in docs:
        client.index(index="misp-attributes", id=doc["uuid"], body=doc)
    client.indices.refresh(index="misp-attributes")
    indicators.refresh_values([d["value"] for d in docs])
    client.indices.refresh(index=indicators.INDEX)


def _past_this_second():
    # Cursors are whole seconds and deltas include their lower bound.
    time.sleep(1.1)


def _reset_redis():
    redis = get_redis_client()
    redis.delete(
        indicators.LOCK_KEY,
        indicators.CURSOR_KEY,
        indicators.BUILT_AT_KEY,
        indicators.REBUILD_QUEUED_KEY,
        indicators.DIRTY_KEY,
        indicators.DIRTY_EVENTS_KEY,
    )
    keys = list(redis.scan_iter("profile_membership:*"))
    if keys:
        redis.delete(*keys)


def _lines(storage_key):
    data = b"".join(exports_storage.open_export(storage_key)).decode()
    return [json.loads(line) for line in data.splitlines() if line.strip()]


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


class TestFailingRule:
    ctx = {"now": NOW, "trust": {"feed:1": 20}}

    @pytest.mark.parametrize(
        "rules,indicator,reason",
        [
            ({}, None, "deleted"),
            ({}, {"deleted": True}, "deleted"),
            ({"types": ["url"]}, {"type": "domain", "to_ids": True}, "type"),
            ({"tlp_ceiling": "tlp:amber"}, {"tlp": "tlp:red", "to_ids": True}, "tlp"),
            ({}, {"to_ids": False}, "no_longer_ids"),
            ({}, {"to_ids": True, "warninglist_hits": ["L"]}, "warninglisted"),
            ({}, {"to_ids": True, "validation_issues": ["private-ip"]}, "validation"),
            ({"min_score": 50}, {"to_ids": True, "score": 40}, "score"),
            (
                {"max_age_days": 30},
                {"to_ids": True, "last_seen": NOW - 31 * DAY},
                "expired",
            ),
            (
                {"exclude_sources": ["feed:1"]},
                {"to_ids": True, "source_keys": ["feed:1"]},
                "excluded_source",
            ),
            (
                {"min_source_trust": 30},
                {"to_ids": True, "source_keys": ["feed:1"]},
                "trust",
            ),
            (
                {"min_source_trust": 10},
                {"to_ids": True, "source_keys": ["feed:1"]},
                None,
            ),
        ],
    )
    def test_reasons(self, rules, indicator, reason):
        assert detection_profiles.failing_rule(rules, indicator, self.ctx) == reason


class TestMembershipDeltas(ApiTester):
    @pytest.fixture(autouse=True)
    def dataset(self, cleanup, db: Session):
        client = get_opensearch_client()
        _reset_redis()
        client.delete_by_query(
            index="misp-attributes,misp-indicators",
            body={"query": {"match_all": {}}},
            refresh=True,
            ignore=[404],
        )
        db.query(sink_models.Sink).delete()
        db.query(export_models.Export).delete()
        db.query(profile_models.DetectionProfile).delete()
        db.commit()
        client.index(
            index="misp-events",
            id=EVENT,
            body={
                "uuid": EVENT,
                "info": "membership",
                "deleted": False,
                "organisation": {"id": 1, "name": "Org"},
                "source": {"type": "local", "id": None, "name": None},
                "tags": [],
            },
            refresh=True,
        )
        _write(
            _attribute(STAYS),
            _attribute(LEAVES),
            _attribute(JOINS, to_ids=False),
        )
        self.profile = detection_profiles.create_profile(
            db,
            profile_schemas.DetectionProfileCreate(
                name="Domains", rules={"types": ["domain"]}
            ),
        )
        yield
        _reset_redis()

    def _changes(self):
        """Joins gains IDS, leaves loses it, stays gets a tag (a change)."""
        _past_this_second()
        _write(
            _attribute(STAYS, tags=["tlp:green"]),
            _attribute(LEAVES, to_ids=False),
            _attribute(JOINS),
        )

    def test_feed_deltas_carry_removals(self, db: Session, api_tester_user):
        db_export = exports.create_export(
            db,
            export_schemas.ExportCreate(
                name="feed",
                query="*",
                format="ndjson",
                incremental=True,
                profile_id=self.profile.id,
            ),
            api_tester_user.id,
        )
        exports.run_export(db, db_export.id)
        db.refresh(db_export)
        assert db_export.status == "completed", db_export.error
        assert {r["value"] for r in _lines(db_export.storage_key)} == {
            STAYS[1],
            LEAVES[1],
        }
        # The first run is the base: no delta.
        assert exports._deltas(db, db_export.id) == []
        first_cursor = db_export.cursor

        self._changes()
        # Writes in the same second as a run's cursor show up in the next
        # delta too (deltas include their lower bound; repeats are harmless):
        # keep this test's deltas exact.
        _past_this_second()
        exports.run_export(db, db_export.id)
        db.refresh(db_export)
        assert db_export.status == "completed", db_export.error
        # What a consumer at the first run's cursor downloads next.
        [delta] = exports.get_feed_deltas(db, db_export, first_cursor)
        records = {r["value"]: r for r in _lines(delta.storage_key)}
        assert records[LEAVES[1]]["action"] == "remove"
        assert records[LEAVES[1]]["reason"] == "no_longer_ids"
        assert records[JOINS[1]]["action"] == "add"
        assert records[JOINS[1]]["score"] is not None
        assert records[STAYS[1]]["action"] == "update"
        assert "tlp:green" in records[STAYS[1]]["tags"]
        assert delta.record_count == 3

        # A purged indicator is still removed, described from the last artifact.
        _past_this_second()
        get_opensearch_client().delete(
            index=indicators.INDEX,
            id=indicators.indicator_uuid("domain", JOINS[1]),
            refresh=True,
        )
        exports.run_export(db, db_export.id)
        db.refresh(db_export)
        last = exports._deltas(db, db_export.id)[-1]
        assert _lines(last.storage_key) == [
            {
                "uuid": indicators.indicator_uuid("domain", JOINS[1]),
                "type": "domain",
                "value": JOINS[1],
                "action": "remove",
                "reason": "deleted",
            }
        ]

    @pytest.mark.parametrize("scopes", [["attributes:read"]])
    def test_streaming_delta(self, client: TestClient, auth_token: auth.Token, db):
        headers = {"Authorization": "Bearer " + auth_token}
        # Two days ago: an indicator last seen 31 days ago crossed the 30-day
        # limit since then.
        since = int(time.time()) - 2 * DAY
        aged = detection_profiles.create_profile(
            db,
            profile_schemas.DetectionProfileCreate(
                name="Recent domains",
                rules={"types": ["domain"], "max_age_days": 30},
            ),
        )
        # Seen 31 days ago, written long before since: it aged out of the
        # profile in the meantime, without any write.
        _write(_attribute(AGES, timestamp=NOW - 31 * DAY))
        get_opensearch_client().update_by_query(
            index=indicators.INDEX,
            body={
                "query": {"term": {"value.keyword": AGES[1]}},
                "script": {"source": f"ctx._source.updated_at = {since - 10 * DAY}"},
            },
            refresh=True,
        )
        self._changes()

        response = client.get(
            "/indicators/export",
            params={"profile": aged.name, "format": "ndjson", "since": since},
            headers=headers,
        )
        assert response.status_code == status.HTTP_200_OK, response.text
        # Removals are the uuid alone: the stream can't know the consumer
        # had the indicator, so it never discloses what the profile withholds.
        records = {r["uuid"]: r for r in map(json.loads, response.text.splitlines())}

        def record(value):
            return records[indicators.indicator_uuid("domain", value)]

        assert record(LEAVES[1]) == {
            "uuid": indicators.indicator_uuid("domain", LEAVES[1]),
            "action": "remove",
            "reason": "no_longer_ids",
        }
        assert record(JOINS[1])["action"] == "upsert"
        assert record(STAYS[1])["action"] == "upsert"
        assert record(AGES[1]) == {
            "uuid": indicators.indicator_uuid("domain", AGES[1]),
            "action": "remove",
            "reason": "expired",
        }

        csv = client.get(
            "/indicators/export",
            params={"profile": aged.name, "format": "csv", "since": since},
            headers=headers,
        )
        assert csv.status_code == status.HTTP_400_BAD_REQUEST

    def test_sink_membership_sync(self, db: Session, receiver):
        url, received = receiver
        with pytest.raises(HTTPException):
            sinks_repository.create_sink(
                db,
                sink_schemas.SinkCreate(
                    name="no profile",
                    type="webhook",
                    config={"url": url},
                    filters={"sync_membership": True},
                ),
            )
        # A first sync that can't reach the sink keeps nothing: the next one
        # sends everything again.
        sink = sinks_repository.create_sink(
            db,
            sink_schemas.SinkCreate(
                name="synced",
                type="webhook",
                config={"url": "http://127.0.0.1:9/unreachable"},
                filters={"profile_id": self.profile.id, "sync_membership": True},
            ),
        )
        assert sinks_repository.membership_sinks(db) == [sink.id]
        with pytest.raises(sinks_repository.SinkDeliveryError):
            sinks_repository.deliver_membership(sink)
        sink.config = {"url": url}
        db.commit()

        sent = sinks_repository.deliver_membership(sink)
        assert sent == 2
        first = received[0]["attributes"]
        assert {(r["value"], r["action"]) for r in first} == {
            (STAYS[1], "add"),
            (LEAVES[1], "add"),
        }
        assert first[0]["indicator"]["uuid"]

        self._changes()
        sent = sinks_repository.deliver_membership(sink)
        assert sent == 2
        second = {r["value"]: r for batch in received[1:] for r in batch["attributes"]}
        assert second[LEAVES[1]]["action"] == "remove"
        assert second[LEAVES[1]]["reason"] == "no_longer_ids"
        assert second[JOINS[1]]["action"] == "add"

        # Nothing changed since: nothing to send.
        sent = sinks_repository.deliver_membership(sink)
        assert sent == 0

        # Synced sinks aren't pushed event by event.
        assert sinks_repository.dispatch_published_event(db, EVENT) == 0

    def test_sink_membership_checks_attributes_as_they_are_now(
        self, db: Session, receiver
    ):
        url, received = receiver
        sink = sinks_repository.create_sink(
            db,
            sink_schemas.SinkCreate(
                name="careful",
                type="webhook",
                config={"url": url},
                # The sink's default exclusions: tlp:red never leaves.
                filters={"profile_id": self.profile.id, "sync_membership": True},
            ),
        )
        # Tagged tlp:red a moment ago: its indicator hasn't caught up.
        client = get_opensearch_client()
        client.index(
            index="misp-attributes",
            id=LEAVES[0],
            body=_attribute(LEAVES, tags=["tlp:red"]),
            refresh=True,
        )
        sent = sinks_repository.deliver_membership(sink)
        assert sent == 1
        assert [r["value"] for r in received[0]["attributes"]] == [STAYS[1]]

        # Withheld, not counted as delivered: once the tag is gone, it goes out.
        client.index(
            index="misp-attributes",
            id=LEAVES[0],
            body=_attribute(LEAVES),
            refresh=True,
        )
        sent = sinks_repository.deliver_membership(sink)
        assert sent == 1
        assert [r["value"] for r in received[1]["attributes"]] == [LEAVES[1]]
