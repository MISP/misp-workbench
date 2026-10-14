import time
from types import SimpleNamespace

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.auth import auth
from app.models import alert_receiver as alert_receiver_models
from app.models import audit_log as audit_log_models
from app.repositories import alert_receivers as receivers
from app.routers.alert_receivers import RedactTokens
from app.schemas import alert_receiver as receiver_schemas
from app.services.opensearch import get_opensearch_client
from app.tests.api_tester import ApiTester

NOW = 1_792_000_100.0
# 2026-10-14T09:12:00Z
NINE_TWELVE = 1_791_969_120.0
EVENT = "a1e40000-0000-4000-8000-000000000001"
ATTRIBUTE = "a1e40000-1000-4000-8000-000000000000"
KNOWN = ["185.220.101.42", "http://invoice-portal.test/download/48812"]
MANAGE = ["alert_receivers:read", "alert_receivers:manage", "sightings:create"]


def _map(preset: str, payload=None):
    preset_ = receivers.PRESETS[preset]
    return receivers.map_payload(
        preset_["sample"] if payload is None else payload,
        preset_["mapping"],
        "receiver",
        now=NOW,
    )


def _values(sightings: list[dict]) -> list[str]:
    return [s["value"] for s in sightings]


class TestPresets:
    def test_each_reads_its_sample(self):
        expected = {
            "generic": ["185.220.101.42", "invoice-portal.test", "evil.example"],
            "splunk": ["10.1.2.3", "185.220.101.42"],
            "elastic": [
                "10.1.2.3",
                "185.220.101.42",
                "http://invoice-portal.test/download/48812",
            ],
            "graylog": ["10.1.2.3", "185.220.101.42"],
            "wazuh": ["10.1.2.3", "185.220.101.42"],
            "sentinel": [
                "185.220.101.42",
                "http://invoice-portal.test/download/48812",
            ],
        }
        assert set(expected) == set(receivers.PRESETS)
        for preset, values in expected.items():
            _, sightings = _map(preset)
            assert _values(sightings) == values, preset

    def test_mappings_are_valid(self):
        for preset in receivers.presets():
            receiver_schemas.AlertPreset(**preset)

    def test_sources_and_times(self):
        _, splunk = _map("splunk")
        assert {s["source"] for s in splunk} == {"Outbound to known C2"}
        assert splunk[0]["timestamp"] == NINE_TWELVE
        # Read from the body around the records, with root().
        _, elastic = _map("elastic")
        assert {s["source"] for s in elastic} == {"Connection to known C2"}
        assert [s["timestamp"] for s in elastic] == [
            NINE_TWELVE,
            NINE_TWELVE,
            NINE_TWELVE + 90,
        ]
        _, wazuh = _map("wazuh")
        assert wazuh[0]["source"] == "Connection to a known C2 address"
        # Wazuh writes its offset without a colon.
        assert wazuh[0]["timestamp"] == pytest.approx(NINE_TWELVE + 0.123)

    def test_wazuh_alerts_posted_unwrapped(self):
        alert = receivers.PRESETS["wazuh"]["sample"]["all_fields"]
        _, sightings = _map("wazuh", alert)
        assert _values(sightings) == ["10.1.2.3", "185.220.101.42"]

    def test_sentinel_false_positives(self):
        sample = {**receivers.PRESETS["sentinel"]["sample"]}
        _, sightings = _map("sentinel", sample)
        assert {s["type"] for s in sightings} == {"positive"}
        sample["classification"] = "FalsePositive"
        _, sightings = _map("sentinel", sample)
        assert {s["type"] for s in sightings} == {"false-positive"}

    def test_generic_types(self):
        _, sightings = _map("generic")
        assert [s["type"] for s in sightings] == [
            "positive",
            "positive",
            "false-positive",
        ]
        assert sightings[0]["source"] == "proxy-01"
        assert sightings[0]["timestamp"] == NINE_TWELVE


class TestMapping:
    def test_records(self):
        mapping = {"records": "alerts", "values": "ip"}
        count, sightings = receivers.map_payload(
            {"alerts": [{"ip": "a"}, {"ip": "b"}, {}]}, mapping, "r", now=NOW
        )
        assert count == 3
        assert _values(sightings) == ["a", "b"]
        # An object is one record; nothing found, none.
        assert receivers.map_payload({"alerts": {"ip": "a"}}, mapping, "r")[0] == 1
        assert receivers.map_payload({}, mapping, "r") == (0, [])
        # The body itself, or each of its elements.
        default = {"values": "ip"}
        assert receivers.map_payload([{"ip": "a"}, {"ip": "b"}], default, "r")[0] == 2

    def test_values_are_flattened_deduplicated_and_stringified(self):
        _, sightings = receivers.map_payload(
            {"a": ["x", ["y", None, ["x"]], 42, 4.0, True, {"k": "v"}, "  ", "z"]},
            {"values": "a"},
            "r",
            now=NOW,
        )
        assert _values(sightings) == ["x", "y", "42", "4", "z"]
        long = "a" * (receivers.MAX_VALUE_LENGTH + 1)
        assert receivers.map_payload({"a": long}, {"values": "a"}, "r")[1] == []

    def test_defaults(self):
        _, sightings = receivers.map_payload(
            {"v": "x"}, {"values": "v"}, "my receiver", now=NOW
        )
        assert sightings == [
            {
                "type": "positive",
                "source": "my receiver",
                "timestamp": NOW,
                "value": "x",
                "attribute_uuid": None,
            }
        ]

    @pytest.mark.parametrize(
        "value,expected",
        [
            (None, "positive"),
            (0, "positive"),
            ("1", "false-positive"),
            (2, "expiration"),
            ("False Positive", "false-positive"),
            ("false_positive", "false-positive"),
            ("FP", "false-positive"),
            ("sighting", "positive"),
        ],
    )
    def test_types(self, value, expected):
        assert receivers.sighting_type(value) == expected

    def test_an_unknown_type_refuses_the_request(self):
        with pytest.raises(receivers.MappingError, match="record 2: type 'benign'"):
            receivers.map_payload(
                [{"v": "a"}, {"v": "b", "t": "benign"}],
                {"values": "v", "type": "t"},
                "r",
            )

    @pytest.mark.parametrize(
        "value,expected",
        [
            (1_792_000_000, 1_792_000_000),
            ("1792000000.5", 1_792_000_000.5),
            (1_792_000_000_000, 1_792_000_000),
            (1_792_000_000_000_000, 1_792_000_000),
            ("2026-10-14T09:12:00Z", NINE_TWELVE),
            (None, NOW),
            ("", NOW),
        ],
    )
    def test_timestamps(self, value, expected):
        assert receivers.timestamp_of(value, NOW) == pytest.approx(expected)

    def test_iso_offsets(self):
        assert receivers.timestamp_of(
            "2026-10-14T09:12:00.000+0000", NOW
        ) == receivers.timestamp_of("2026-10-14T09:12:00Z", NOW)
        assert receivers.timestamp_of(
            "2026-10-14T11:12:00+02:00", NOW
        ) == receivers.timestamp_of("2026-10-14T09:12:00Z", NOW)
        # No offset: UTC.
        assert receivers.timestamp_of(
            "2026-10-14T09:12:00", NOW
        ) == receivers.timestamp_of("2026-10-14T09:12:00Z", NOW)

    def test_the_future_is_now(self):
        # A wrong clock can't keep an indicator alive past its expiry.
        assert receivers.timestamp_of(NOW + 86400, NOW) == NOW + 300
        assert receivers.timestamp_of(NOW + 60, NOW) == NOW + 60

    @pytest.mark.parametrize("value", ["yesterday", -5, float("nan"), "inf"])
    def test_bad_timestamps(self, value):
        with pytest.raises(receivers.MappingError):
            receivers.timestamp_of(value, NOW)

    def test_an_attribute_uuid_sights_that_attribute(self):
        _, sightings = receivers.map_payload(
            {"uuid": ATTRIBUTE, "values": ["ignored"]},
            {"values": "values", "attribute_uuid": "uuid"},
            "r",
            now=NOW,
        )
        assert sightings == [
            {
                "type": "positive",
                "source": "r",
                "timestamp": NOW,
                "value": None,
                "attribute_uuid": ATTRIBUTE,
            }
        ]

    def test_expressions_are_checked(self):
        with pytest.raises(ValidationError, match="no JMESPath expression"):
            receiver_schemas.AlertMapping(values="result.[")
        with pytest.raises(ValidationError, match="values can't be empty"):
            receiver_schemas.AlertMapping(values="  ")
        mapping = receiver_schemas.AlertMapping(values=" a ", type="")
        assert (mapping.values, mapping.type, mapping.records) == ("a", None, "@")

    def test_runtime_errors_name_the_field(self):
        with pytest.raises(receivers.MappingError, match="the alert: values: "):
            receivers.map_payload({"a": 1}, {"values": "keys(a)"}, "r")

    def test_bodies(self):
        assert receivers.parse_body(b'{"a": 1}') == {"a": 1}
        with pytest.raises(receivers.MappingError, match="no JSON"):
            receivers.parse_body(b"a=1&b=2")
        with pytest.raises(receivers.MappingError, match="no JSON"):
            receivers.parse_body(b"\xff\xfe")


class TestResolve:
    @pytest.fixture(autouse=True)
    def _attributes(self, monkeypatch):
        from app.repositories import sightings

        monkeypatch.setattr(
            sightings,
            "find_sighted_attributes",
            lambda values: {v: [{}] for v in values if v in KNOWN},
        )
        monkeypatch.setattr(
            sightings,
            "_resolve_attribute",
            lambda ref: (
                {"uuid": ATTRIBUTE, "value": KNOWN[0], "event_uuid": EVENT}
                if ref == ATTRIBUTE
                else None
            ),
        )

    def _sightings(self, *values, uuid=None):
        base = {"type": "positive", "source": "r", "timestamp": NOW}
        return [{**base, "value": v, "attribute_uuid": None} for v in values] + (
            [{**base, "value": None, "attribute_uuid": uuid}] if uuid else []
        )

    def test_only_known_values(self):
        kept, skipped = receivers.resolve(
            self._sightings("10.1.2.3", KNOWN[0]), only_known=True
        )
        assert _values(kept) == [KNOWN[0]]
        assert kept[0]["known"] is True
        assert skipped == 1

    def test_every_value(self):
        kept, skipped = receivers.resolve(
            self._sightings("10.1.2.3", KNOWN[0]), only_known=False
        )
        assert [(s["value"], s["known"]) for s in kept] == [
            ("10.1.2.3", False),
            (KNOWN[0], True),
        ]
        assert skipped == 0

    def test_attributes(self):
        kept, skipped = receivers.resolve(
            self._sightings(uuid=ATTRIBUTE) + self._sightings(uuid="nope"),
            only_known=True,
        )
        assert [(s["value"], s["attribute_uuid"], s["event_uuid"]) for s in kept] == [
            (KNOWN[0], ATTRIBUTE, EVENT)
        ]
        assert skipped == 1


class TestReceiving:
    def _receiver(self, **fields):
        return SimpleNamespace(
            **{"id": 1, "enabled": True, "allowed_ips": [], "rate_limit": 2, **fields}
        )

    def test_refused(self):
        assert receivers.refused(self._receiver(), "192.0.2.1") is None
        assert receivers.refused(self._receiver(enabled=False), None) == "disabled"
        limited = self._receiver(allowed_ips=["192.0.2.0/24"])
        assert receivers.refused(limited, "192.0.2.9") is None
        assert receivers.refused(limited, "198.51.100.1") == "address"
        assert receivers.refused(limited, "testclient") == "address"
        assert receivers.refused(limited, None) == "address"

    def test_rate_limit(self, monkeypatch):
        counts: dict = {}

        class Redis:
            def incr(self, key):
                counts[key] = counts.get(key, 0) + 1
                return counts[key]

            def expire(self, key, seconds):
                pass

        from app.services import redis

        monkeypatch.setattr(redis, "get_redis_client", lambda: Redis())
        receiver = self._receiver(rate_limit=2)
        # 20 seconds into a minute.
        at = 1_792_000_040.0
        assert receivers.rate_limited(receiver, at) is None
        assert receivers.rate_limited(receiver, at) is None
        assert receivers.rate_limited(receiver, at) == 40
        # A new minute, a new count.
        assert receivers.rate_limited(receiver, at + 60) is None

    def test_tokens_are_kept_out_of_access_logs(self):
        import logging

        record = logging.LogRecord(
            "uvicorn.access",
            logging.INFO,
            __file__,
            1,
            '%s - "%s %s HTTP/%s" %d',
            ("192.0.2.1:5000", "POST", "/webhooks/alerts/awh_secret-Value", "1.1", 202),
            None,
        )
        RedactTokens().filter(record)
        assert "secret" not in record.getMessage()
        assert "/webhooks/alerts/<token>" in record.getMessage()

    def test_settings_are_checked(self):
        with pytest.raises(ValidationError):
            receiver_schemas.AlertReceiverCreate(name="x", allowed_ips=["nope"])
        with pytest.raises(ValidationError):
            receiver_schemas.AlertReceiverCreate(name="x", rate_limit=0)
        created = receiver_schemas.AlertReceiverCreate(
            name="x", allowed_ips=["192.0.2.9/24"]
        )
        assert created.allowed_ips == ["192.0.2.0/24"]
        with pytest.raises(ValueError, match="unknown preset"):
            receivers.preset_mapping("qradar")


class TestAlertReceivers(ApiTester):
    @pytest.fixture(scope="class", autouse=True)
    def dataset(self, cleanup):
        client = get_opensearch_client()
        for i, value in enumerate(KNOWN):
            uuid = f"a1e40000-1000-4000-8000-{i:012d}"
            client.index(
                index="misp-attributes",
                id=uuid,
                body={
                    "uuid": uuid,
                    "event_uuid": EVENT,
                    "type": "ip-dst" if i == 0 else "url",
                    "category": "Network activity",
                    "value": value,
                    "to_ids": True,
                    "deleted": False,
                    "comment": "",
                    "timestamp": int(time.time()),
                    "tags": [],
                },
            )
        client.indices.refresh(index="misp-attributes")
        yield

    @pytest.fixture(autouse=True)
    def _clean(self, db: Session):
        def clean():
            db.query(alert_receiver_models.AlertReceiver).delete()
            db.commit()
            client = get_opensearch_client()
            client.delete_by_query(
                index="misp-sightings",
                body={"query": {"match_all": {}}},
                refresh=True,
                ignore=[404],
            )

        clean()
        yield
        clean()

    def _sightings(self) -> list[dict]:
        client = get_opensearch_client()
        client.indices.refresh(index="misp-sightings")
        hits = client.search(
            index="misp-sightings", body={"size": 100, "query": {"match_all": {}}}
        )["hits"]["hits"]
        return sorted((h["_source"] for h in hits), key=lambda s: (s["value"], s["type"]))

    @pytest.mark.parametrize("scopes", [MANAGE])
    def test_a_splunk_alert_end_to_end(
        self, client: TestClient, auth_token: auth.Token, db: Session
    ):
        headers = {"Authorization": "Bearer " + auth_token}
        presets = client.get("/alert-receivers/presets", headers=headers)
        assert {p["preset"] for p in presets.json()} == set(receivers.PRESETS)

        created = client.post(
            "/alert-receivers",
            json={"name": "Splunk", "preset": "splunk"},
            headers=headers,
        )
        assert created.status_code == status.HTTP_201_CREATED, created.text
        body = created.json()
        assert body["mapping"]["source"] == "search_name"
        path = body["path"]
        assert path == f"/webhooks/alerts/{body['token']}"
        stored = db.get(alert_receiver_models.AlertReceiver, body["id"])
        assert body["token"] not in (stored.token_hash, stored.token_prefix)
        assert "token" not in client.get("/alert-receivers", headers=headers).json()[0]
        duplicate = client.post(
            "/alert-receivers", json={"name": "Splunk"}, headers=headers
        )
        assert duplicate.status_code == status.HTTP_409_CONFLICT

        # A sender posts with the URL alone; the internal address is no
        # indicator and is left out.
        sample = receivers.PRESETS["splunk"]["sample"]
        posted = client.post(path, json=sample)
        assert posted.status_code == status.HTTP_202_ACCEPTED, posted.text
        assert posted.json() == {"records": 1, "sightings": 1, "skipped": 1}
        sightings = self._sightings()
        assert [s["value"] for s in sightings] == ["185.220.101.42"]
        assert sightings[0]["observer"]["source"] == "Outbound to known C2"
        assert sightings[0]["observer"]["organisation"]
        assert sightings[0]["metadata"]["sensor_type"] == "splunk"

        receiver = client.get(f"/alert-receivers/{body['id']}", headers=headers).json()
        assert receiver["received_count"] == 1
        assert receiver["sightings_count"] == 1
        assert receiver["last_error"] is None
        last = client.get(
            f"/alert-receivers/{body['id']}/last-payload", headers=headers
        ).json()
        assert "Outbound to known C2" in last["payload"]

        # All or nothing: a body the mapping can't read reports nothing.
        bad = client.post(path, json={"result": {"_time": "yesterday"}})
        assert bad.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert "timestamp" in bad.json()["detail"]
        not_json = client.post(path, content=b"a=1")
        assert not_json.status_code == status.HTTP_400_BAD_REQUEST
        receiver = client.get(f"/alert-receivers/{body['id']}", headers=headers).json()
        assert receiver["received_count"] == 3
        assert receiver["sightings_count"] == 1
        assert "no JSON" in receiver["last_error"]
        too_big = client.post(path, content=b" " * (receivers.MAX_BODY + 1))
        assert too_big.status_code == status.HTTP_413_REQUEST_ENTITY_TOO_LARGE

        # The token opens the webhook and nothing else.
        as_bearer = {"Authorization": "Bearer " + body["token"]}
        assert client.get("/alert-receivers", headers=as_bearer).status_code == 401
        assert client.post("/webhooks/alerts/awh_nope", json={}).status_code == 404

        # Rotated: the old token stops at once.
        rotated = client.post(
            f"/alert-receivers/{body['id']}/token", headers=headers
        ).json()
        assert client.post(path, json=sample).status_code == 404
        assert client.post(rotated["path"], json=sample).status_code == 202

        # Disabled, or limited to addresses the test client isn't at.
        client.patch(
            f"/alert-receivers/{body['id']}", json={"enabled": False}, headers=headers
        )
        assert client.post(rotated["path"], json=sample).status_code == 403
        client.patch(
            f"/alert-receivers/{body['id']}",
            json={"enabled": True, "allowed_ips": ["192.0.2.0/24"]},
            headers=headers,
        )
        assert client.post(rotated["path"], json=sample).status_code == 403

        actions = {
            row.action
            for row in db.query(audit_log_models.AuditLog).filter(
                audit_log_models.AuditLog.resource_type == "alert_receiver"
            )
        }
        assert actions == {
            "alert_receiver.created",
            "alert_receiver.token_rotated",
            "alert_receiver.updated",
        }
        deleted = client.delete(f"/alert-receivers/{body['id']}", headers=headers)
        assert deleted.status_code == status.HTTP_204_NO_CONTENT
        assert client.post(rotated["path"], json=sample).status_code == 404

    @pytest.mark.parametrize("scopes", [MANAGE])
    def test_batches_attributes_and_false_positives(
        self, client: TestClient, auth_token: auth.Token
    ):
        headers = {"Authorization": "Bearer " + auth_token}
        created = client.post(
            "/alert-receivers",
            json={"name": "SOAR", "preset": "generic", "only_known": False},
            headers=headers,
        ).json()
        posted = client.post(
            created["path"],
            json=[
                {"values": [KNOWN[1], "10.9.9.9"], "source": "proxy"},
                {"value": KNOWN[0], "type": 1},
                {"uuid": "a1e40000-1000-4000-8000-000000000000"},
                {"uuid": "a1e40000-1000-4000-8000-999999999999"},
            ],
        )
        assert posted.json() == {"records": 4, "sightings": 4, "skipped": 1}
        sightings = self._sightings()
        assert [(s["value"], s["type"]) for s in sightings] == [
            ("10.9.9.9", "positive"),
            (KNOWN[0], "false-positive"),
            (KNOWN[0], "positive"),
            (KNOWN[1], "positive"),
        ]
        by_attribute = [s for s in sightings if s.get("attribute_uuid")]
        assert by_attribute[0]["event_uuid"] == EVENT

    @pytest.mark.parametrize("scopes", [MANAGE])
    def test_rate_limit(self, client: TestClient, auth_token: auth.Token):
        headers = {"Authorization": "Bearer " + auth_token}
        created = client.post(
            "/alert-receivers",
            json={"name": "Chatty", "rate_limit": 2},
            headers=headers,
        ).json()
        responses = [
            client.post(created["path"], json={"value": "x"}) for _ in range(3)
        ]
        statuses = [r.status_code for r in responses]
        # The minute may turn between requests; then all three pass.
        assert statuses in ([202, 202, 429], [202, 202, 202], [202, 429, 202])
        if 429 in statuses:
            limited = responses[statuses.index(429)]
            assert 1 <= int(limited.headers["Retry-After"]) <= 60

    @pytest.mark.parametrize("scopes", [["alert_receivers:read"]])
    def test_reading_isnt_managing(self, client: TestClient, auth_token: auth.Token):
        headers = {"Authorization": "Bearer " + auth_token}
        assert client.get("/alert-receivers", headers=headers).status_code == 200
        tried = client.post(
            "/alert-receivers/test",
            json={
                "mapping": receivers.PRESETS["splunk"]["mapping"],
                "payload": receivers.PRESETS["splunk"]["sample"],
            },
            headers=headers,
        )
        assert tried.status_code == 200, tried.text
        result = tried.json()
        assert [s["value"] for s in result["sightings"]] == ["185.220.101.42"]
        assert result["skipped"] == 1
        broken = client.post(
            "/alert-receivers/test",
            json={"mapping": {"values": "keys(a)"}, "payload": {"a": 1}},
            headers=headers,
        ).json()
        assert "values" in broken["error"]
        created = client.post("/alert-receivers", json={"name": "x"}, headers=headers)
        assert created.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.parametrize(
        "scopes", [["alert_receivers:read", "alert_receivers:manage"]]
    )
    def test_managing_takes_reporting_sightings(
        self, client: TestClient, auth_token: auth.Token
    ):
        headers = {"Authorization": "Bearer " + auth_token}
        created = client.post("/alert-receivers", json={"name": "x"}, headers=headers)
        assert created.status_code == status.HTTP_401_UNAUTHORIZED

    def test_other_organisations_dont_see_it(self, db: Session, api_tester_user):
        receiver, _ = receivers.create_receiver(
            db, receiver_schemas.AlertReceiverCreate(name="mine"), api_tester_user
        )
        org_id = api_tester_user.org_id + 1000
        other = SimpleNamespace(org_id=org_id, role=SimpleNamespace(scopes=[]))
        assert receivers.visible(db, other) == []
        with pytest.raises(receivers.ReceiverNotFound):
            receivers.get_receiver(db, other, receiver.id)
        admin = SimpleNamespace(org_id=org_id, role=SimpleNamespace(scopes=["*"]))
        assert receivers.get_receiver(db, admin, receiver.id).id == receiver.id
