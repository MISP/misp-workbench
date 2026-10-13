import json
import threading
from datetime import datetime, timezone
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest
from fastapi import HTTPException, status
from fastapi.testclient import TestClient
from pydantic import ValidationError
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

FEED_EVENT = "d9f00000-0000-4000-8000-000000000001"
LOCAL_EVENT = "d9f00000-0000-4000-8000-000000000002"
RED_EVENT = "d9f00000-0000-4000-8000-000000000003"

GALAXY = 'misp-galaxy:threat-actor="Profile Bear"'
HASH = "d41d8cd98f00b204e9800998ecf8427e"

# value -> (event, type, to_ids, extra)
ATTRIBUTES = [
    ("45.33.32.1", FEED_EVENT, "ip-dst", True, {}),
    ("good.example", LOCAL_EVENT, "domain", True, {"tags": [{"name": GALAXY}]}),
    ("https://red.example/x", RED_EVENT, "url", True, {}),
    ("45.33.32.2", LOCAL_EVENT, "ip-src", False, {}),
    ("listed.example", LOCAL_EVENT, "domain", True, {"warninglist_hits": ["L"]}),
    # Normalisation flags it private-ip.
    ("10.1.1.1", LOCAL_EVENT, "ip-dst", True, {}),
    (HASH, FEED_EVENT, "md5", True, {}),
    (HASH, LOCAL_EVENT, "md5", True, {}),
    ("old.example", FEED_EVENT, "domain", True, {"timestamp": NOW - 200 * DAY}),
]

# Rule sets the query and the per-indicator check must agree on.
RULE_SETS = [
    {},
    {
        "to_ids": False,
        "exclude_warninglisted": False,
        "exclude_validation_issues": False,
    },
    {"types": ["domain", "url"]},
    {"categories": ["Payload delivery"]},
    {"tlp_ceiling": "tlp:amber"},
    {"tlp_ceiling": "tlp:clear", "to_ids": False},
    {"tags": ["misp-galaxy:*"]},
    {"exclude_tags": ["tlp:red"], "to_ids": False},
    {"min_score": 60},
    {"max_age_days": 30},
    {"sources": ["server:6"]},
    {"exclude_sources": ["feed:5"]},
    {"organisations": [902]},
    {"exclude_organisations": [901]},
    {"min_source_trust": 10},
    {"min_source_trust": -10},
]


def _reset_redis():
    get_redis_client().delete(
        indicators.LOCK_KEY,
        indicators.CURSOR_KEY,
        indicators.BUILT_AT_KEY,
        indicators.REBUILD_QUEUED_KEY,
        indicators.DIRTY_KEY,
        indicators.DIRTY_EVENTS_KEY,
    )


def _live_indicators():
    client = get_opensearch_client()
    client.indices.refresh(index=indicators.INDEX)
    return [
        h["_source"]
        for h in client.search(
            index=indicators.INDEX,
            body={"size": 1000, "query": {"term": {"deleted": False}}},
        )["hits"]["hits"]
    ]


def _selected(rules):
    ctx = detection_profiles.context()
    response = get_opensearch_client().search(
        index=indicators.INDEX,
        body={"size": 1000, "query": detection_profiles.to_query(rules, ctx)},
    )
    return {h["_source"]["value"] for h in response["hits"]["hits"]}


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


class TestProfileRules:
    def test_source_keys_are_checked(self):
        with pytest.raises(ValidationError):
            profile_schemas.ProfileRules(sources=["feed:abc"])
        profile_schemas.ProfileRules(sources=["feed:3", "server:2", "local"])

    def test_unknown_rules_are_refused(self):
        with pytest.raises(ValidationError):
            profile_schemas.ProfileRules(min_scor=50)


class TestDetectionProfiles(ApiTester):
    @pytest.fixture(scope="class", autouse=True)
    def dataset(self, cleanup):
        client = get_opensearch_client()
        _reset_redis()
        for uuid, source, org, tags in (
            (FEED_EVENT, {"type": "feed", "id": 5, "name": "Feed Five"}, 901, []),
            (
                LOCAL_EVENT,
                {"type": "local", "id": None, "name": None},
                902,
                ["tlp:green"],
            ),
            (
                RED_EVENT,
                {"type": "server", "id": 6, "name": "Server Six"},
                901,
                ["tlp:red"],
            ),
        ):
            client.index(
                index="misp-events",
                id=uuid,
                body={
                    "uuid": uuid,
                    "info": "profiles",
                    "deleted": False,
                    "published": True,
                    "organisation": {"id": org, "name": f"Org {org}"},
                    "source": source,
                    "tags": [{"name": t} for t in tags],
                },
            )
        for i, (value, event, type_, to_ids, extra) in enumerate(ATTRIBUTES):
            uuid = f"d9f00000-1000-4000-8000-{i:012d}"
            category = "Payload delivery" if type_ == "md5" else "Network activity"
            client.index(
                index="misp-attributes",
                id=uuid,
                body={
                    "uuid": uuid,
                    "event_uuid": event,
                    "type": type_,
                    "category": category,
                    "value": value,
                    "to_ids": to_ids,
                    "deleted": False,
                    "comment": "",
                    "timestamp": NOW - DAY,
                    "tags": [],
                    **extra,
                },
            )
        client.indices.refresh(index="misp-events,misp-attributes")
        indicators.rebuild()
        client.indices.refresh(index=indicators.INDEX)
        yield
        _reset_redis()

    @pytest.fixture(autouse=True)
    def _clean(self, db: Session):
        db.query(sink_models.Sink).delete()
        db.query(export_models.Export).delete()
        db.query(profile_models.DetectionProfile).delete()
        db.commit()
        yield
        db.query(sink_models.Sink).delete()
        db.query(export_models.Export).delete()
        db.query(profile_models.DetectionProfile).delete()
        db.commit()

    def _profile(self, db, name="Test profile", granularity="indicators", **rules):
        return detection_profiles.create_profile(
            db,
            profile_schemas.DetectionProfileCreate(
                name=name,
                granularity=granularity,
                rules=profile_schemas.ProfileRules(**rules),
            ),
        )

    @pytest.mark.parametrize("rules", RULE_SETS, ids=[json.dumps(r) for r in RULE_SETS])
    def test_query_and_check_agree(self, rules):
        ctx = detection_profiles.context()
        by_check = {
            d["value"]
            for d in _live_indicators()
            if detection_profiles.matches(rules, d, ctx)
        }
        assert _selected(rules) == by_check

    def test_rules(self):
        # The defaults: IDS, no warninglisted, no validation issues.
        assert _selected({}) == {
            "45.33.32.1",
            "good.example",
            "https://red.example/x",
            HASH,
            "old.example",
        }
        assert "https://red.example/x" not in _selected({"tlp_ceiling": "tlp:amber"})
        assert _selected({"tags": ["misp-galaxy:*"]}) == {"good.example"}
        assert "old.example" not in _selected({"max_age_days": 30})
        # Only from feed 5 is out; the hash the local event reports too stays.
        assert _selected({"exclude_sources": ["feed:5"]}) == {
            "good.example",
            "https://red.example/x",
            HASH,
        }
        assert _selected({"sources": ["server:6"]}) == {"https://red.example/x"}
        # No source has a modifier of 10 or more.
        assert _selected({"min_source_trust": 10}) == set()

    @pytest.mark.parametrize(
        "scopes",
        [
            [
                "detection_profiles:read",
                "detection_profiles:create",
                "detection_profiles:update",
                "detection_profiles:delete",
            ]
        ],
    )
    def test_api(
        self, client: TestClient, auth_token: auth.Token, db: Session, api_tester_user
    ):
        headers = {"Authorization": "Bearer " + auth_token}
        body = {
            "name": "Hashes",
            "rules": {"types": ["md5"], "min_score": 10},
        }
        created = client.post("/detection-profiles", json=body, headers=headers)
        assert created.status_code == status.HTTP_201_CREATED, created.text
        profile_id = created.json()["id"]
        assert created.json()["granularity"] == "indicators"
        assert (
            client.post("/detection-profiles", json=body, headers=headers).status_code
            == status.HTTP_409_CONFLICT
        )
        bad = client.post(
            "/detection-profiles",
            json={"name": "Bad", "rules": {"sources": ["nope"]}},
            headers=headers,
        )
        assert bad.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        count = client.get(f"/detection-profiles/{profile_id}/count", headers=headers)
        assert count.json()["count"] == 1
        assert count.json()["sample"][0]["value"] == HASH
        preview = client.post(
            "/detection-profiles/preview",
            json={"rules": {"types": ["domain"]}},
            headers=headers,
        )
        assert preview.json()["count"] == 2

        updated = client.patch(
            f"/detection-profiles/{profile_id}",
            json={"granularity": "attributes"},
            headers=headers,
        )
        assert updated.json()["granularity"] == "attributes"
        assert [
            p["name"] for p in client.get("/detection-profiles", headers=headers).json()
        ] == ["Hashes"]

        # In use: deleting it would leave an export sending everything.
        db.add(
            export_models.Export(
                user_id=api_tester_user.id,
                name="uses it",
                query="*",
                index_target="indicators",
                format="ndjson",
                status="queued",
                profile_id=profile_id,
                created_at=datetime.now(timezone.utc),
            )
        )
        db.commit()
        in_use = client.delete(f"/detection-profiles/{profile_id}", headers=headers)
        assert in_use.status_code == status.HTTP_409_CONFLICT
        assert "uses it" in in_use.json()["detail"]
        db.query(export_models.Export).delete()
        db.commit()
        assert (
            client.delete(
                f"/detection-profiles/{profile_id}", headers=headers
            ).status_code
            == status.HTTP_204_NO_CONTENT
        )

    @pytest.mark.parametrize("scopes", [["attributes:read"]])
    def test_indicator_search_and_exports(
        self, client: TestClient, auth_token: auth.Token, db: Session
    ):
        headers = {"Authorization": "Bearer " + auth_token}
        self._profile(db, name="Hashes", types=["md5"])
        found = client.get(
            "/indicators", params={"profile": "Hashes"}, headers=headers
        ).json()
        assert [i["value"] for i in found["items"]] == [HASH]
        missing = client.get("/indicators", params={"profile": "Nope"}, headers=headers)
        assert missing.status_code == status.HTTP_404_NOT_FOUND

        text = client.get(
            "/indicators/export",
            params={"profile": "Hashes", "format": "text"},
            headers=headers,
        )
        assert text.text.splitlines() == [HASH]
        # The attributes behind the indicator: both events'.
        attributes = client.get(
            "/attributes/export",
            params={"profile": "Hashes", "format": "ndjson"},
            headers=headers,
        )
        events = sorted(
            json.loads(line)["event_uuid"] for line in attributes.text.splitlines()
        )
        assert events == sorted([FEED_EVENT, LOCAL_EVENT])
        delta = client.get(
            "/attributes/export",
            params={"profile": "Hashes", "format": "ndjson", "since": "1d"},
            headers=headers,
        )
        assert delta.status_code == status.HTTP_400_BAD_REQUEST

    def test_scheduled_export(self, db: Session, api_tester_user):
        profile = self._profile(db, name="Domains", types=["domain"])
        attributes_profile = self._profile(
            db, name="Domain attributes", granularity="attributes", types=["domain"]
        )
        with pytest.raises(HTTPException) as refused:
            exports.create_export(
                db,
                export_schemas.ExportCreate(
                    name="x",
                    query="*",
                    format="ndjson",
                    incremental=True,
                    profile_id=attributes_profile.id,
                ),
                api_tester_user.id,
            )
        assert refused.value.status_code == status.HTTP_400_BAD_REQUEST
        with pytest.raises(ValidationError):
            export_schemas.ExportCreate(
                name="x", query="*", format="csv", profile_id=profile.id
            )

        db_export = exports.create_export(
            db,
            export_schemas.ExportCreate(
                name="domains", query="*", format="text", profile_id=profile.id
            ),
            api_tester_user.id,
        )
        exports.run_export(db, db_export.id)
        db.refresh(db_export)
        assert db_export.status == "completed", db_export.error
        artifact = b"".join(exports_storage.open_export(db_export.storage_key))
        assert sorted(artifact.decode().splitlines()) == ["good.example", "old.example"]

    def test_sink(self, db: Session, receiver):
        url, received = receiver
        profile = self._profile(
            db, name="Galaxy", granularity="attributes", tags=["misp-galaxy:*"]
        )
        sink = sinks_repository.create_sink(
            db,
            sink_schemas.SinkCreate(
                name="profiled",
                type="webhook",
                config={"url": url},
                # The sink's own filters would send everything flagged for IDS.
                filters={"profile_id": profile.id, "exclude_tags": []},
            ),
        )
        assert sinks_repository.deliver_event(sink, LOCAL_EVENT) == 1
        [record] = received[0]["attributes"]
        assert record["value"] == "good.example"
        assert "indicator" not in record

        # A profile of indicators sends them consolidated.
        profile.granularity = "indicators"
        db.commit()
        assert sinks_repository.deliver_event(sink, LOCAL_EVENT) == 1
        assert received[1]["attributes"][0]["indicator"]["uuid"]

        with pytest.raises(HTTPException):
            sinks_repository.create_sink(
                db,
                sink_schemas.SinkCreate(
                    name="dangling",
                    type="webhook",
                    config={"url": url},
                    filters={"profile_id": 99999},
                ),
            )

    @pytest.mark.parametrize("scopes", [["attributes:read"]])
    def test_lookup_and_rest_search(
        self, client: TestClient, auth_token: auth.Token, db: Session
    ):
        headers = {"Authorization": "Bearer " + auth_token}
        self._profile(db, name="Clean", tlp_ceiling="tlp:amber")
        response = client.post(
            "/lookup",
            json={
                "values": ["45.33.32.1", "https://red.example/x", "10.1.1.1"],
                "to_ids_only": False,
                "include_warninglisted": True,
                "profile": "Clean",
            },
            headers=headers,
        )
        assert [m["value"] for m in response.json()["matches"]] == ["45.33.32.1"]

        search = client.post(
            "/attributes/restSearch",
            json={"profile": "Clean", "eventid": LOCAL_EVENT},
            headers=headers,
        )
        assert search.status_code == status.HTTP_200_OK, search.text
        values = sorted(a["value"] for a in search.json()["response"]["Attribute"])
        assert values == sorted(["good.example", HASH])
        unknown = client.post(
            "/attributes/restSearch", json={"profile": "Nope"}, headers=headers
        )
        assert unknown.status_code == status.HTTP_400_BAD_REQUEST


class TestProfilesFailClosed(ApiTester):
    """Fresh values are judged on every rule; stale indicators don't let
    newly excluded values through; a sink's own exclusions hold."""

    @pytest.fixture(scope="class", autouse=True)
    def dataset(self, cleanup):
        client = get_opensearch_client()
        _reset_redis()
        client.index(
            index="misp-events",
            id=FEED_EVENT,
            body={
                "uuid": FEED_EVENT,
                "info": "fail closed",
                "deleted": False,
                "organisation": {"id": 901, "name": "Org 901"},
                "source": {"type": "feed", "id": 5, "name": "Feed Five"},
                "tags": [],
            },
        )
        for uuid, value, tags in (
            ("d9f00000-2000-4000-8000-000000000001", "tagged.example", [GALAXY]),
            ("d9f00000-2000-4000-8000-000000000002", "plain.example", []),
        ):
            client.index(
                index="misp-attributes",
                id=uuid,
                body={
                    "uuid": uuid,
                    "event_uuid": FEED_EVENT,
                    "type": "domain",
                    "category": "Network activity",
                    "value": value,
                    "to_ids": True,
                    "deleted": False,
                    "timestamp": NOW - DAY,
                    "tags": [{"name": t} for t in tags],
                },
            )
        client.indices.refresh(index="misp-events,misp-attributes")
        indicators.rebuild()
        client.indices.refresh(index=indicators.INDEX)
        yield
        _reset_redis()

    @pytest.fixture(autouse=True)
    def _clean(self, db: Session):
        db.query(sink_models.Sink).delete()
        db.query(profile_models.DetectionProfile).delete()
        db.commit()
        yield
        db.query(sink_models.Sink).delete()
        db.query(profile_models.DetectionProfile).delete()
        db.commit()

    def test_fresh_values_are_judged_on_every_rule(self):
        event = get_opensearch_client().get(index="misp-events", id=FEED_EVENT)[
            "_source"
        ]
        fresh = {
            "type": "domain",
            "category": "Network activity",
            "value": "fresh.example",
            "to_ids": True,
            "timestamp": NOW,
            "tags": [],
        }
        ctx = detection_profiles.context()

        def passes(**rules):
            return detection_profiles.attribute_matches(rules, fresh, {}, ctx, event)

        assert passes()
        # Its source comes from its event: a feed the profile leaves out.
        assert not passes(exclude_sources=["feed:5"])
        assert not passes(sources=["server:6"])
        # Its score is computed (feed: 50), not skipped.
        assert passes(min_score=50)
        assert not passes(min_score=60)
        assert not passes(min_source_trust=10)
        # Without an event, its source is unknown: source rules fail closed.
        assert not detection_profiles.attribute_matches(
            {"sources": ["feed:5"]}, fresh, {}, ctx
        )

    def test_stale_indicators_dont_let_exclusions_through(self, db: Session):
        client = get_opensearch_client()
        uuid = "d9f00000-2000-4000-8000-000000000001"
        source = client.get(index="misp-attributes", id=uuid)["_source"]
        found = detection_profiles.indicators_for([source])
        ctx = detection_profiles.context()
        rules = {"tags": ["misp-galaxy:*"], "tlp_ceiling": "tlp:amber"}
        assert detection_profiles.attribute_matches(rules, source, found, ctx)
        # Tagged tlp:red a moment ago: the indicator hasn't caught up yet.
        red = {**source, "tags": source["tags"] + [{"name": "tlp:red"}]}
        assert not detection_profiles.attribute_matches(rules, red, found, ctx)

    def test_sink_exclusions_hold_with_a_profile(self, db: Session, receiver):
        url, received = receiver
        profile = detection_profiles.create_profile(
            db,
            profile_schemas.DetectionProfileCreate(
                name="Anything", granularity="attributes", rules={}
            ),
        )
        sink = sinks_repository.create_sink(
            db,
            sink_schemas.SinkCreate(
                name="careful",
                type="webhook",
                config={"url": url},
                filters={"profile_id": profile.id, "exclude_tags": ["misp-galaxy:*"]},
            ),
        )
        assert sinks_repository.deliver_event(sink, FEED_EVENT) == 1
        assert [a["value"] for a in received[0]["attributes"]] == ["plain.example"]
