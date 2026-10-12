import json
import threading
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest.mock import patch

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.auth import auth
from app.models import sink as sink_models
from app.repositories import indicators
from app.repositories import organisations as organisations_repository
from app.repositories import runtime_settings as runtime_settings_repository
from app.repositories import sinks as sinks_repository
from app.schemas import organisations as organisation_schemas
from app.schemas import sink as sink_schemas
from app.services import scoring
from app.services.opensearch import get_opensearch_client
from app.services.redis import get_redis_client
from app.tests.api_tester import ApiTester
from app.worker import tasks

DAY = 86400
NOW = int(time.time())
TRUST_ORG = "Scoring Trust Org"

FEED_EVENT = "5c0e0000-0000-4000-8000-000000000001"
LOCAL_EVENT = "5c0e0000-0000-4000-8000-000000000002"

OLD_IP = ("5c0e0000-1000-4000-8000-000000000001", "ip-dst", "192.0.2.10")
FRESH_IP = ("5c0e0000-1000-4000-8000-000000000002", "ip-dst", "192.0.2.20")
OLD_HASH = (
    "5c0e0000-1000-4000-8000-000000000003",
    "sha256",
    "a" * 64,
)
LISTED = ("5c0e0000-1000-4000-8000-000000000004", "domain", "listed.example.com")
EXPIRED = (
    "5c0e0000-1000-4000-8000-000000000005",
    "url",
    "https://expired.example.com/x",
)


def _attribute(key, event_uuid, timestamp, **extra):
    uuid, type_, value = key
    return {
        "uuid": uuid,
        "event_uuid": event_uuid,
        "type": type_,
        "category": "Network activity",
        "value": value,
        "to_ids": True,
        "deleted": False,
        "comment": "",
        "timestamp": timestamp,
        "tags": [],
        **extra,
    }


def _iso(ts):
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")


def _indicator(key):
    get_opensearch_client().indices.refresh(index=indicators.INDEX)
    return indicators.get_indicator(indicators.indicator_uuid(key[1], key[2]))


def _factors(indicator):
    return {c["factor"]: c["points"] for c in indicator["score_breakdown"]}


def _reset_redis():
    get_redis_client().delete(
        indicators.LOCK_KEY,
        indicators.CURSOR_KEY,
        indicators.BUILT_AT_KEY,
        indicators.REBUILD_QUEUED_KEY,
        indicators.DIRTY_KEY,
        indicators.DIRTY_EVENTS_KEY,
    )


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


class TestScoreFunction:
    """The scoring rules alone, on hand-built indicators."""

    cfg = scoring.config()

    def _score(self, **indicator):
        indicator = {
            "type": "ip-dst",
            "last_seen": NOW,
            "sources": [{"type": "feed", "name": "A", "event_count": 1}],
            **indicator,
        }
        return scoring.score(indicator, self.cfg, NOW)

    def test_base_is_the_best_source(self):
        score, breakdown = self._score(
            sources=[
                {"type": "feed", "name": "A", "event_count": 1},
                {"type": "local", "name": "local", "event_count": 1},
            ]
        )
        # local (70) + one more source (5)
        assert score == 75
        assert breakdown[0] == {
            "factor": "base",
            "points": 70,
            "detail": "local source",
        }

    def test_corroboration_is_capped(self):
        sources = [{"type": "feed", "name": str(i), "event_count": 1} for i in range(9)]
        assert self._score(sources=sources)[0] == 50 + 15

    def test_decay_halves_per_half_life(self):
        assert self._score(last_seen=NOW - 30 * DAY)[0] == 25
        assert self._score(last_seen=NOW - 60 * DAY)[0] == 12
        # Hashes don't decay.
        assert self._score(type="sha256", last_seen=NOW - 900 * DAY)[0] == 50
        # Unlisted types use the default half-life (180 days).
        assert self._score(type="mutex", last_seen=NOW - 180 * DAY)[0] == 25

    def test_sightings(self):
        assert self._score(sightings={"positive": 1})[0] == 55
        assert self._score(sightings={"positive": 7})[0] == 65
        assert self._score(sightings={"positive": 1000})[0] == 65
        assert self._score(sightings={"false_positive": 1})[0] == 30
        assert self._score(sightings={"false_positive": 9})[0] == 0

    def test_expiration_caps_until_a_later_positive_sighting(self):
        expired = {"last_expiration_at": NOW - DAY, "last_positive_at": NOW - 2 * DAY}
        score, breakdown = self._score(sightings=expired)
        assert score == 10
        assert breakdown[-1]["factor"] == "expiration"
        revived = {"last_expiration_at": NOW - 2 * DAY, "last_positive_at": NOW - DAY}
        assert self._score(sightings=revived)[0] == 50

    def test_warninglist_penalty_and_bounds(self):
        assert self._score(warninglist_hits=["List"])[0] == 0
        assert (
            self._score(
                sources=[{"type": "local", "name": "local", "event_count": 1}] * 4,
                sightings={"positive": 100},
            )[0]
            == 100
        )

    def _trusted(self, **trust):
        cfg = scoring.config()
        cfg["_trust"] = {"feed": {}, "server": {}, "organisation": {}, **trust}
        return cfg

    def test_source_trust_best_source_wins(self):
        cfg = self._trusted(feed={1: (10, None), 2: (-10, 40)})
        noisy = {"type": "feed", "id": 2, "name": "Noisy", "event_count": 1}
        good = {"type": "feed", "id": 1, "name": "Good", "event_count": 1}
        indicator = {"type": "sha256", "sources": [noisy]}
        score, breakdown = scoring.score(indicator, cfg, NOW)
        assert score == 40
        assert _factors({"score_breakdown": breakdown})["source_trust"] == -10
        # A trusted source reporting it too sets the base and lifts the cap.
        score, breakdown = scoring.score(
            {**indicator, "sources": [noisy, good]}, cfg, NOW
        )
        assert score == 50 + 10 + 5
        assert "cap" not in _factors({"score_breakdown": breakdown})

    def test_cap_holds_only_when_every_source_is_capped(self):
        cfg = self._trusted(server={3: (0, 20)}, organisation={7: (0, 30)})
        server = {"type": "server", "id": 3, "name": "S", "event_count": 1}
        local = {"type": "local", "name": "local", "event_count": 1}
        noisy_org = {"id": 7, "name": "Noisy Org", "event_count": 1}
        other_org = {"id": 8, "name": "Other Org", "event_count": 1}

        def score(sources, organisations):
            indicator = {"type": "sha256", "sources": sources}
            return scoring.score(
                {**indicator, "organisations": organisations}, cfg, NOW
            )[0]

        assert score([server], [other_org]) == 20
        assert score([server, local], [other_org]) == 75
        # Organisation caps are combined on their own: an uncapped source
        # doesn't lift them, an uncapped organisation does.
        assert score([local], [noisy_org]) == 30
        assert score([local], [noisy_org, other_org]) == 70

    def test_organisation_modifier_takes_the_most_favourable(self):
        cfg = self._trusted(organisation={1: (15, None), 2: (-30, None)})
        indicator = {
            "type": "sha256",
            "sources": [{"type": "feed", "id": 9, "name": "F", "event_count": 1}],
        }
        bad = {"id": 2, "name": "Bad", "event_count": 1}
        assert scoring.score({**indicator, "organisations": [bad]}, cfg, NOW)[0] == 20
        both = [bad, {"id": 1, "name": "Good", "event_count": 1}]
        assert scoring.score({**indicator, "organisations": both}, cfg, NOW)[0] == 65

    def test_disabled(self):
        cfg = scoring.config({"enabled": False})
        assert scoring.score({"type": "ip-dst"}, cfg, NOW) == (None, [])

    def test_rewrites_on_a_step_or_crossing_the_threshold(self):
        assert not scoring.needs_rewrite(70, 66, self.cfg)
        assert scoring.needs_rewrite(70, 65, self.cfg)
        # 31 -> 28 is small, but crosses decayed_below (30).
        assert scoring.needs_rewrite(31, 28, self.cfg)
        assert scoring.needs_rewrite(None, 50, self.cfg)

    def test_config_merges_saved_values_over_defaults(self):
        cfg = scoring.config({"half_life_days": {"ip-dst": 7}, "refresh_step": 1})
        assert cfg["half_life_days"]["ip-dst"] == 7
        assert cfg["half_life_days"]["domain"] == 90
        assert cfg["refresh_step"] == 1

    @pytest.mark.parametrize(
        "stored",
        [
            {"enabled": "yes"},
            {"warninglist_penalty": -1},
            {"half_life_days": {"ip-dst": "a month"}},
            {"base_by_source": []},
        ],
    )
    def test_validate(self, stored):
        with pytest.raises(scoring.InvalidScoringConfig):
            scoring.validate(stored)


class TestIndicatorScoring(ApiTester):
    @pytest.fixture(scope="class", autouse=True)
    def dataset(self, cleanup):
        client = get_opensearch_client()
        _reset_redis()
        values = [k[2] for k in (OLD_IP, FRESH_IP, OLD_HASH, LISTED, EXPIRED)]
        client.delete_by_query(
            index="misp-sightings",
            body={"query": {"terms": {"value.keyword": values}}},
            refresh=True,
            ignore=[404],
        )
        for uuid, source in (
            (FEED_EVENT, {"type": "feed", "id": 1, "name": "Feed A"}),
            (LOCAL_EVENT, {"type": "local", "id": None, "name": None}),
        ):
            client.index(
                index="misp-events",
                id=uuid,
                body={
                    "uuid": uuid,
                    "info": "scoring",
                    "deleted": False,
                    "published": True,
                    "threat_level": 2,
                    "organisation": {"name": TRUST_ORG},
                    "source": source,
                    "tags": [],
                },
            )
        for doc in (
            _attribute(OLD_IP, FEED_EVENT, NOW - 120 * DAY),
            _attribute(FRESH_IP, LOCAL_EVENT, NOW - 3600),
            _attribute(OLD_HASH, FEED_EVENT, NOW - 400 * DAY),
            _attribute(LISTED, LOCAL_EVENT, NOW, warninglist_hits=["Top domains"]),
            _attribute(EXPIRED, LOCAL_EVENT, NOW - DAY),
        ):
            client.index(index="misp-attributes", id=doc["uuid"], body=doc)
        for type_, at in (("positive", NOW - 5 * DAY), ("expiration", NOW - 2 * DAY)):
            client.index(
                index="misp-sightings",
                body={
                    "value": EXPIRED[2],
                    "type": type_,
                    "@timestamp": _iso(at),
                    "observer": {"organisation": "scoring-test"},
                },
            )
        client.indices.refresh(index="misp-events,misp-attributes,misp-sightings")
        indicators.rebuild()
        yield
        client.delete_by_query(
            index="misp-sightings",
            body={"query": {"terms": {"value.keyword": values}}},
            refresh=True,
            ignore=[404],
        )
        _reset_redis()

    @pytest.fixture(autouse=True)
    def _sinks(self, db: Session):
        db.query(sink_models.Sink).delete()
        db.commit()
        yield
        db.query(sink_models.Sink).delete()
        db.commit()

    def test_scores_and_breakdowns(self):
        fresh = _indicator(FRESH_IP)
        assert fresh["score"] == 70
        assert fresh["scored_at"] >= NOW
        old = _indicator(OLD_IP)
        # feed (50), four half-lives ago
        assert old["score"] == 3
        assert _factors(old)["decay"] == -47
        assert _indicator(OLD_HASH)["score"] == 50
        assert _factors(_indicator(LISTED))["warninglist"] == -50
        expired = _indicator(EXPIRED)
        assert expired["score"] == 10
        assert expired["sightings"]["last_expiration_at"] > (
            expired["sightings"]["last_positive_at"]
        )

    @pytest.mark.parametrize("scopes", [["attributes:read"]])
    def test_search_and_scores_api(self, client: TestClient, auth_token: auth.Token):
        headers = {"Authorization": "Bearer " + auth_token}
        page = client.get(
            "/indicators",
            params={"min_score": 30, "sort": "score"},
            headers=headers,
        ).json()
        assert [i["value"] for i in page["items"]] == [FRESH_IP[2], OLD_HASH[2]]
        assert page["items"][0]["score_breakdown"][0]["factor"] == "base"

        response = client.post(
            "/indicators/scores",
            json={
                "attributes": [
                    {"type": "ip-dst", "value": FRESH_IP[2]},
                    {"type": "text", "value": "context, not an indicator"},
                ]
            },
            headers=headers,
        )
        assert response.status_code == status.HTTP_200_OK
        fresh, missing = response.json()["scores"]
        assert fresh["score"] == 70
        assert missing is None

    @pytest.mark.parametrize("scopes", [["attributes:read"]])
    def test_lookup_min_score(self, client: TestClient, auth_token: auth.Token):
        response = client.post(
            "/lookup",
            json={
                "values": [OLD_IP[2], FRESH_IP[2]],
                "to_ids_only": False,
                "min_score": 30,
            },
            headers={"Authorization": "Bearer " + auth_token},
        )
        [match] = response.json()["matches"]
        assert match["value"] == FRESH_IP[2]
        assert match["score"] == 70

    @pytest.mark.parametrize("scopes", [["attributes:read"]])
    def test_rest_search_decay(self, client: TestClient, auth_token: auth.Token):
        headers = {"Authorization": "Bearer " + auth_token}

        def search(body):
            response = client.post("/attributes/restSearch", json=body, headers=headers)
            assert response.status_code == status.HTTP_200_OK, response.text
            return {a["value"]: a for a in response.json()["response"]["Attribute"]}

        found = search({"includeDecayScore": 1})
        [fresh] = found[FRESH_IP[2]]["decay_score"]
        assert fresh["score"] == 70.0
        assert fresh["base_score"] == 70.0
        assert fresh["decayed"] is False
        assert found[OLD_IP[2]]["decay_score"][0]["decayed"] is True

        kept = search({"excludeDecayed": 1})
        assert set(kept) == {FRESH_IP[2], OLD_HASH[2]}
        assert all("decay_score" not in a for a in kept.values())
        # score overrides the threshold.
        assert set(search({"excludeDecayed": 1, "score": 60})) == {FRESH_IP[2]}

        bad = client.post(
            "/attributes/restSearch",
            json={"excludeDecayed": 1, "score": "high"},
            headers=headers,
        )
        assert bad.status_code == status.HTTP_400_BAD_REQUEST

    def test_sink_min_score(self, db: Session, receiver):
        url, received = receiver
        sink = sinks_repository.create_sink(
            db,
            sink_schemas.SinkCreate(
                name="scored",
                type="webhook",
                config={"url": url},
                filters={"to_ids_only": False, "exclude_tags": [], "min_score": 30},
            ),
        )
        # The local event holds the fresh IP (70), the expired URL (10) and
        # the warninglisted domain (left out by the sink's warninglist filter).
        assert sinks_repository.deliver_event(sink, LOCAL_EVENT) == 1
        assert [a["value"] for a in received[0]["attributes"]] == [FRESH_IP[2]]

    @pytest.mark.parametrize("scopes", [["settings:update", "settings:delete"]])
    def test_settings_are_validated_and_rescore(
        self, client: TestClient, auth_token: auth.Token, db: Session
    ):
        headers = {"Authorization": "Bearer " + auth_token}
        bad = client.post(
            "/settings/runtime/scoring",
            json={"half_life_days": {"ip-dst": "a month"}},
            headers=headers,
        )
        assert bad.status_code == status.HTTP_400_BAD_REQUEST
        assert "half_life_days.ip-dst" in bad.json()["detail"]

        get_redis_client().delete(indicators.REBUILD_QUEUED_KEY)
        try:
            with patch.object(tasks.rebuild_indicators, "delay") as delay:
                response = client.post(
                    "/settings/runtime/scoring",
                    json={"half_life_days": {"sha256": 30}},
                    headers=headers,
                )
                assert response.status_code == status.HTTP_200_OK
                delay.assert_called_once()
        finally:
            runtime_settings_repository.delete_setting(db, "scoring")
            get_redis_client().delete(indicators.REBUILD_QUEUED_KEY)

    @staticmethod
    def _set_event_org(event_uuid, org_id):
        get_opensearch_client().update(
            index="misp-events",
            id=event_uuid,
            body={"doc": {"orgc_id": org_id, "organisation": None}},
            refresh=True,
        )

    # Last: it lowers every score, which the tests above don't expect.
    def test_organisation_trust(self, db: Session, api_tester_user):
        get_redis_client().delete(indicators.REBUILD_QUEUED_KEY)
        organisation = organisations_repository.create_organisation(
            db,
            organisation_schemas.OrganisationCreate(
                name=TRUST_ORG, local=True, created_by=api_tester_user.id
            ),
        )
        with patch.object(tasks.rebuild_indicators, "delay") as delay:
            organisations_repository.update_organisation(
                db,
                organisation.id,
                organisation_schemas.OrganisationUpdate(
                    score_modifier=-20, score_cap=25
                ),
            )
            # Changing a source's trust queues a rescore...
            delay.assert_called_once()
            get_redis_client().delete(indicators.REBUILD_QUEUED_KEY)
            # ...but saving it unchanged doesn't.
            organisations_repository.update_organisation(
                db,
                organisation.id,
                organisation_schemas.OrganisationUpdate(score_modifier=-20),
            )
            delay.assert_called_once()

        # An impostor with the same name (as a feed can create) gets none of
        # the trust: organisations are identified by id.
        impostor = organisations_repository.create_organisation(
            db,
            organisation_schemas.OrganisationCreate(
                name=TRUST_ORG, local=False, created_by=api_tester_user.id
            ),
        )
        self._set_event_org(LOCAL_EVENT, impostor.id)
        indicators.rebuild()
        assert _indicator(FRESH_IP)["score"] == 70

        self._set_event_org(LOCAL_EVENT, organisation.id)
        indicators.rebuild()
        fresh = _indicator(FRESH_IP)
        # local (70) - 20, then capped at 25
        assert fresh["score"] == 25
        assert _factors(fresh)["organisation_trust"] == -20
        assert _factors(fresh)["cap"] == -25
