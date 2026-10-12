import csv
import io
import json
import threading
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.auth import auth
from app.models import export as export_models
from app.models import sink as sink_models
from app.repositories import exports as exports_repository
from app.repositories import indicators
from app.repositories import sinks as sinks_repository
from app.repositories import stream_exports
from app.schemas import export as export_schemas
from app.schemas import sink as sink_schemas
from app.services import exports_storage
from app.services.opensearch import get_opensearch_client
from app.services.redis import get_redis_client
from app.tests.api_tester import ApiTester

FEED_EVENT = "abababab-0000-4000-8000-000000000001"
LOCAL_EVENT = "abababab-0000-4000-8000-000000000002"
DELETED_EVENT = "abababab-0000-4000-8000-000000000003"

IP = "198.51.100.7"
DOMAIN = "consolidated.example.org"
LONG_URL = "https://consolidated.example.org/" + "p" * 300

IP_IN_FEED = "abababab-1000-4000-8000-000000000001"
IP_IN_LOCAL = "abababab-1000-4000-8000-000000000002"
IP_IN_DELETED = "abababab-1000-4000-8000-000000000003"
DOMAIN_IN_FEED = "abababab-1000-4000-8000-000000000004"
TEXT_IN_FEED = "abababab-1000-4000-8000-000000000005"
URL_IN_FEED = "abababab-1000-4000-8000-000000000006"
IP_SRC_IN_LOCAL = "abababab-1000-4000-8000-000000000007"

_TAG = {
    "exportable": True,
    "hide_tag": False,
    "is_galaxy": False,
    "is_custom_galaxy": False,
    "local_only": False,
    "colour": "#000000",
}
GALAXY = 'misp-galaxy:threat-actor="Consolidated Bear"'


def _tags(*names):
    return [{"id": i + 1, "name": n, **_TAG} for i, n in enumerate(names)]


def _attribute(
    uuid, event_uuid, type_, value, to_ids=True, timestamp=1700000000, **extra
):
    return {
        "uuid": uuid,
        "event_uuid": event_uuid,
        "type": type_,
        "category": "Network activity",
        "value": value,
        "to_ids": to_ids,
        "deleted": False,
        "comment": "",
        "timestamp": timestamp,
        "tags": [],
        **extra,
    }


def _event(uuid, source=None, organisation=None, tags=(), deleted=False):
    return {
        "uuid": uuid,
        "info": f"event {uuid[-1]}",
        "deleted": deleted,
        "published": True,
        "threat_level": 2,
        "orgc_id": None,
        "organisation": organisation,
        "source": source,
        "tags": _tags(*tags),
    }


def _refresh(*indices):
    get_opensearch_client().indices.refresh(index=",".join(indices))


def _reset_redis():
    redis = get_redis_client()
    redis.delete(
        indicators.LOCK_KEY,
        indicators.CURSOR_KEY,
        indicators.BUILT_AT_KEY,
        indicators.REBUILD_QUEUED_KEY,
        indicators.DIRTY_KEY,
    )


def _indicator(type_, value):
    _refresh(indicators.INDEX)
    response = get_opensearch_client().get(
        index=indicators.INDEX, id=indicators.indicator_uuid(type_, value), ignore=[404]
    )
    return response["_source"] if response.get("found") else None


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


class TestIndicators(ApiTester):
    @pytest.fixture(scope="class", autouse=True)
    def dataset(self, cleanup):
        client = get_opensearch_client()
        client.delete_by_query(
            index="misp-sightings",
            body={"query": {"terms": {"value.keyword": [IP, DOMAIN]}}},
            refresh=True,
            ignore=[404],
        )
        _reset_redis()
        for event in (
            _event(
                FEED_EVENT,
                source={"type": "feed", "id": 7, "name": "Feed A"},
                organisation={"name": "Feed Org"},
                tags=["tlp:green"],
            ),
            _event(
                LOCAL_EVENT,
                source={"type": "local", "id": None, "name": None},
                organisation={"name": "Local Org"},
                tags=["tlp:amber"],
            ),
            _event(DELETED_EVENT, deleted=True, tags=["tlp:red"]),
        ):
            client.index(index="misp-events", id=event["uuid"], body=event)
        for doc in (
            _attribute(IP_IN_FEED, FEED_EVENT, "ip-dst", IP, tags=_tags(GALAXY)),
            _attribute(
                IP_IN_LOCAL,
                LOCAL_EVENT,
                "ip-dst",
                IP,
                to_ids=False,
                timestamp=1700000100,
                first_seen=1600000000,
            ),
            # In a deleted event: neither counted nor its tlp:red applied.
            _attribute(
                IP_IN_DELETED, DELETED_EVENT, "ip-dst", IP, timestamp=1800000000
            ),
            _attribute(DOMAIN_IN_FEED, FEED_EVENT, "domain", DOMAIN),
            _attribute(TEXT_IN_FEED, FEED_EVENT, "text", "just some context"),
            _attribute(URL_IN_FEED, FEED_EVENT, "url", LONG_URL),
            _attribute(IP_SRC_IN_LOCAL, LOCAL_EVENT, "ip-src", IP),
        ):
            client.index(index="misp-attributes", id=doc["uuid"], body=doc)
        for type_, at in (
            ("positive", "2024-01-01T00:00:00"),
            ("positive", "2025-06-01T00:00:00"),
            ("false-positive", "2025-01-01T00:00:00"),
        ):
            client.index(
                index="misp-sightings",
                body={"value": IP, "type": type_, "@timestamp": at},
            )
        _refresh("misp-events", "misp-attributes", "misp-sightings")
        yield
        _reset_redis()

    @pytest.fixture(autouse=True)
    def _sinks(self, db: Session):
        db.query(sink_models.Sink).delete()
        db.commit()
        yield
        db.query(sink_models.Sink).delete()
        db.commit()

    def test_rebuild_consolidates_attributes(self):
        result = indicators.rebuild()
        assert result["written"] == 4
        assert result["removed"] == 0

        ip = _indicator("ip-dst", IP)
        assert ip["uuid"] == indicators.indicator_uuid("ip-dst", IP)
        assert ip["attribute_count"] == 2
        assert ip["ids_attribute_count"] == 1
        assert ip["to_ids"] is True
        assert ip["event_count"] == 2
        # Newest attribute's event first.
        assert ip["events"] == [LOCAL_EVENT, FEED_EVENT]
        assert {(s["type"], s["name"], s["event_count"]) for s in ip["sources"]} == {
            ("feed", "Feed A", 1),
            ("local", "local", 1),
        }
        assert {o["name"] for o in ip["organisations"]} == {"Feed Org", "Local Org"}
        # The most restrictive TLP wins; the deleted event's tlp:red doesn't count.
        assert ip["tlp"] == "tlp:amber"
        assert "tlp:green" not in ip["tags"]
        assert ip["galaxies"] == [GALAXY]
        assert ip["sightings"]["positive"] == 2
        assert ip["sightings"]["false_positive"] == 1
        # Seen dates span attributes and sightings.
        assert ip["first_seen"] == 1600000000
        assert ip["last_seen"] == int(
            datetime(2025, 6, 1, tzinfo=timezone.utc).timestamp()
        )

        # Same value, other type: its own indicator.
        assert _indicator("ip-src", IP)["attribute_count"] == 1
        # Long values (past the keyword's ignore_above) are consolidated too.
        assert _indicator("url", LONG_URL)["event_count"] == 1
        # Context types are not indicators.
        assert _indicator("text", "just some context") is None

    def test_rebuild_writes_only_changes(self):
        assert indicators.rebuild()["written"] == 0

    def test_sync_follows_writes_and_sightings(self):
        client = get_opensearch_client()
        time.sleep(1.1)
        client.update(
            index="misp-attributes", id=DOMAIN_IN_FEED, body={"doc": {"deleted": True}}
        )
        client.index(
            index="misp-sightings",
            body={
                "value": IP,
                "type": "expiration",
                "@timestamp": "2025-02-01T00:00:00",
            },
        )
        _refresh("misp-attributes", "misp-sightings")
        indicators.mark_sighted([IP])

        result = indicators.sync()
        assert result["removed"] == 1
        domain = _indicator("domain", DOMAIN)
        assert domain["deleted"] is True
        assert _indicator("ip-dst", IP)["sightings"]["expiration"] == 1
        assert get_redis_client().scard(indicators.DIRTY_KEY) == 0

    def test_rebuild_tombstones_hard_deletes(self):
        client = get_opensearch_client()
        client.delete(index="misp-attributes", id=IP_SRC_IN_LOCAL, refresh=True)
        result = indicators.rebuild()
        assert result["removed"] == 1
        assert _indicator("ip-src", IP)["deleted"] is True

    @pytest.mark.parametrize("scopes", [["attributes:read"]])
    def test_api(self, client: TestClient, auth_token: auth.Token):
        headers = {"Authorization": "Bearer " + auth_token}
        _refresh(indicators.INDEX)

        response = client.get("/indicators", params={"q": f'"{IP}"'}, headers=headers)
        assert response.status_code == status.HTTP_200_OK
        page = response.json()
        assert [(i["type"], i["value"]) for i in page["items"]] == [("ip-dst", IP)]
        assert "checksum" not in page["items"][0]

        tombstones = client.get(
            "/indicators",
            params={"q": f'"{IP}"', "include_deleted": True},
            headers=headers,
        ).json()
        assert tombstones["total"] == 2

        uuid = indicators.indicator_uuid("ip-dst", IP)
        response = client.get(f"/indicators/{uuid}", headers=headers)
        assert response.json()["event_count"] == 2
        missing = client.get(
            "/indicators/00000000-0000-4000-8000-000000000000", headers=headers
        )
        assert missing.status_code == status.HTTP_404_NOT_FOUND

        status_ = client.get("/indicators/status", headers=headers).json()
        assert status_["built"] is True
        assert status_["indicators"] == 2
        assert status_["tombstones"] == 2

    @pytest.mark.parametrize("scopes", [["attributes:read"]])
    def test_export(self, client: TestClient, auth_token: auth.Token):
        headers = {"Authorization": "Bearer " + auth_token}
        response = client.get(
            "/indicators/export", params={"format": "csv"}, headers=headers
        )
        assert response.status_code == status.HTTP_200_OK
        rows = list(csv.reader(io.StringIO(response.text)))
        assert rows[0] == stream_exports.INDICATOR_CSV_COLUMNS
        by_value = {row[2]: dict(zip(rows[0], row)) for row in rows[1:]}
        assert set(by_value) == {IP, LONG_URL}
        assert by_value[IP]["event_count"] == "2"
        assert by_value[IP]["tlp"] == "tlp:amber"

        delta = client.get(
            "/indicators/export",
            params={"format": "ndjson", "since": "1d"},
            headers=headers,
        )
        records = [json.loads(line) for line in delta.text.splitlines()]
        assert {(r["type"], r["deleted"]) for r in records} >= {
            ("domain", True),
            ("ip-src", True),
        }

    @pytest.mark.parametrize("scopes", [["attributes:read"]])
    def test_lookup_includes_indicators(
        self, client: TestClient, auth_token: auth.Token
    ):
        response = client.post(
            "/lookup",
            json={"values": [IP], "to_ids_only": False, "include_indicators": True},
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert response.status_code == status.HTTP_200_OK
        [match] = response.json()["matches"]
        assert [i["type"] for i in match["indicators"]] == ["ip-dst"]
        assert match["indicators"][0]["sources"][0]["event_count"] == 1

    def test_scheduled_export_target(self, db: Session, api_tester_user):
        with pytest.raises(ValueError, match="indicator exports"):
            export_schemas.ExportCreate(
                name="x", query="*", index_target="indicators", format="csv"
            )
        export_schemas.ExportCreate(
            name="x",
            query="*",
            index_target="indicators",
            format="ndjson",
            incremental=True,
        )

        db_export = export_models.Export(
            user_id=api_tester_user.id,
            name="indicators",
            query="*",
            index_target="indicators",
            format="text",
            status="queued",
            created_at=datetime.now(timezone.utc),
        )
        db.add(db_export)
        db.commit()
        exports_repository.run_export(db, db_export.id)
        db.refresh(db_export)
        assert db_export.status == "completed", db_export.error
        assert db_export.record_count == 2
        artifact = b"".join(exports_storage.open_export(db_export.storage_key))
        assert sorted(artifact.decode().splitlines()) == sorted([IP, LONG_URL])

    def test_sink_indicator_mode(self, db: Session, receiver):
        url, received = receiver
        sink = sinks_repository.create_sink(
            db,
            sink_schemas.SinkCreate(
                name="indicators",
                type="webhook",
                config={"url": url},
                filters={
                    "to_ids_only": False,
                    "exclude_tags": ["tlp:amber"],
                    "indicator_mode": True,
                },
            ),
        )
        # The feed event is tlp:green, but the IP is tlp:amber through the
        # local event: in indicator mode the exclusion sees the merged TLP.
        # The text attribute is context, not an indicator, and isn't sent.
        sent = sinks_repository.deliver_event(sink, FEED_EVENT)
        assert sent == 1
        [record] = received[0]["attributes"]
        assert record["value"] == LONG_URL
        assert record["indicator"]["sources"] == ["Feed A"]
        assert record["indicator"]["event_count"] == 1

        # Attribute mode judges the attribute and its event alone.
        sink.filters = {**sink.filters, "indicator_mode": False}
        db.commit()
        assert sinks_repository.deliver_event(sink, FEED_EVENT) == 3
        assert all("indicator" not in r for r in received[1]["attributes"])
