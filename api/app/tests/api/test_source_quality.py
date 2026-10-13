import time
from datetime import datetime, timezone

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.auth import auth
from app.repositories import indicators
from app.repositories import runtime_settings as runtime_settings_repository
from app.repositories import source_quality
from app.services import scoring
from app.services.opensearch import get_opensearch_client
from app.services.redis import get_redis_client
from app.tests.api_tester import ApiTester

DAY = 86400
NOW = int(time.time())

FEED_EVENT = "50a1e000-0000-4000-8000-000000000001"
SERVER_EVENT = "50a1e000-0000-4000-8000-000000000002"

# The feed reports four values, one of them also through the server; one
# was sighted, one reported benign recently and one benign long ago.
SHARED = "198.51.100.40"
SIGHTED = "198.51.100.41"
BENIGN = "198.51.100.42"
OLD_BENIGN = "198.51.100.43"
SERVER_ONLY = "198.51.100.44"
VALUES = [SHARED, SIGHTED, BENIGN, OLD_BENIGN, SERVER_ONLY]


def _iso(ts):
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")


def _reset_redis():
    get_redis_client().delete(
        indicators.LOCK_KEY,
        indicators.CURSOR_KEY,
        indicators.BUILT_AT_KEY,
        indicators.REBUILD_QUEUED_KEY,
        indicators.DIRTY_KEY,
        indicators.DIRTY_EVENTS_KEY,
        source_quality.ADAPTIVE_CACHE_KEY,
    )


class TestAdaptiveRules:
    cfg = scoring.config()

    def test_penalty(self):
        # 1 point per percent of false positives, up to 30, from 20 indicators.
        assert source_quality.adaptive_penalty(self.cfg, 100, 0.12) == 12
        assert source_quality.adaptive_penalty(self.cfg, 100, 0.9) == 30
        assert source_quality.adaptive_penalty(self.cfg, 19, 0.5) == 0

    def test_score_applies_it_to_the_best_source(self):
        cfg = scoring.config()
        cfg["_trust"] = {"feed": {}, "server": {}, "organisation": {}}
        cfg["_adaptive"] = {
            "feed": {1: [25, 0.25]},
            "server": {},
            "organisation": {7: [10, 0.1]},
        }
        noisy = {"type": "feed", "id": 1, "name": "Noisy", "event_count": 1}
        clean = {"type": "feed", "id": 2, "name": "Clean", "event_count": 1}
        org = {"id": 7, "name": "Org", "event_count": 1}
        score, breakdown = scoring.score(
            {"type": "sha256", "sources": [noisy], "organisations": [org]},
            cfg,
            NOW,
        )
        factors = {c["factor"]: c["points"] for c in breakdown}
        assert factors["adaptive_trust"] == -25
        assert factors["organisation_adaptive_trust"] == -10
        assert score == 50 - 25 - 10
        # A clean source reporting it too becomes the best one.
        score, breakdown = scoring.score(
            {"type": "sha256", "sources": [noisy, clean]}, cfg, NOW
        )
        assert "adaptive_trust" not in {c["factor"] for c in breakdown}
        assert score == 50 + 5

    def test_validate(self):
        with pytest.raises(scoring.InvalidScoringConfig, match="adaptive_trust"):
            scoring.validate({"adaptive_trust": "yes"})
        with pytest.raises(scoring.InvalidScoringConfig, match="adaptive_max_penalty"):
            scoring.validate({"adaptive_max_penalty": -5})


class TestSourceQuality(ApiTester):
    @pytest.fixture(scope="class", autouse=True)
    def dataset(self, cleanup):
        client = get_opensearch_client()
        _reset_redis()
        client.delete_by_query(
            index="misp-sightings",
            body={"query": {"terms": {"value.keyword": VALUES}}},
            refresh=True,
            ignore=[404],
        )
        for uuid, source in (
            (FEED_EVENT, {"type": "feed", "id": 1, "name": "Feed One"}),
            (SERVER_EVENT, {"type": "server", "id": 2, "name": "Server Two"}),
        ):
            client.index(
                index="misp-events",
                id=uuid,
                body={
                    "uuid": uuid,
                    "info": "quality",
                    "deleted": False,
                    "organisation": None,
                    "orgc_id": None,
                    "source": source,
                    "tags": [],
                },
            )
        n = 0
        for event_uuid, values in (
            (FEED_EVENT, [SHARED, SIGHTED, BENIGN, OLD_BENIGN]),
            (SERVER_EVENT, [SHARED, SERVER_ONLY]),
        ):
            for value in values:
                n += 1
                uuid = f"50a1e000-1000-4000-8000-{n:012d}"
                client.index(
                    index="misp-attributes",
                    id=uuid,
                    body={
                        "uuid": uuid,
                        "event_uuid": event_uuid,
                        "type": "ip-dst",
                        "category": "Network activity",
                        "value": value,
                        "to_ids": True,
                        "deleted": False,
                        "timestamp": NOW - DAY,
                        "tags": [],
                    },
                )
        for value, type_, at in (
            (SIGHTED, "positive", NOW - 2 * DAY),
            (BENIGN, "false-positive", NOW - 3 * DAY),
            (OLD_BENIGN, "false-positive", NOW - 90 * DAY),
        ):
            client.index(
                index="misp-sightings",
                body={
                    "value": value,
                    "type": type_,
                    "@timestamp": _iso(at),
                    "observer": {"organisation": "quality-test"},
                },
            )
        client.indices.refresh(index="misp-events,misp-attributes,misp-sightings")
        indicators.rebuild()
        client.indices.refresh(index=indicators.INDEX)
        yield
        client.delete_by_query(
            index="misp-sightings",
            body={"query": {"terms": {"value.keyword": VALUES}}},
            refresh=True,
            ignore=[404],
        )
        _reset_redis()

    def _feed(self, report):
        return next(s for s in report["sources"] if s["key"] == "feed:1")

    def test_indicators_carry_flat_source_keys(self):
        shared = indicators.get_indicator(indicators.indicator_uuid("ip-dst", SHARED))
        assert shared["source_keys"] == ["feed:1", "server:2"]
        assert shared["source_count"] == 2

    def test_statistics(self):
        feed = self._feed(source_quality.statistics())
        assert feed["kind"] == "feed"
        assert feed["id"] == 1
        assert feed["indicators"] == 4
        assert feed["exclusive"] == 3
        assert feed["overlap_rate"] == 0.25
        assert feed["top_overlaps"] == [
            {"key": "server:2", "name": "server:2", "indicators": 1}
        ]
        assert feed["hit_rate"] == 0.25
        # Only the recent false positive is in the 30-day window.
        assert feed["false_positive_rate"] == 0.25
        # Adaptive trust is off, and the feed has fewer than 20 indicators.
        assert feed["adaptive_penalty"] == 0
        assert feed["effective_modifier"] == 0

    @pytest.mark.parametrize("scopes", [["attributes:read"]])
    def test_api(self, client: TestClient, auth_token: auth.Token):
        headers = {"Authorization": "Bearer " + auth_token}
        report = client.get("/indicators/sources", headers=headers)
        assert report.status_code == status.HTTP_200_OK
        assert {s["key"] for s in report.json()["sources"]} == {"feed:1", "server:2"}

        one = client.get("/indicators/sources/server/2", headers=headers)
        assert one.status_code == status.HTTP_200_OK
        assert one.json()["indicators"] == 2
        assert one.json()["exclusive"] == 1
        for path in ("/indicators/sources/feed/999", "/indicators/sources/feed/x"):
            assert client.get(path, headers=headers).status_code == 404

        # Every output that takes a query can now name one source exactly.
        found = client.get(
            "/indicators", params={"q": 'source_keys:"server:2"'}, headers=headers
        ).json()
        assert sorted(i["value"] for i in found["items"]) == sorted(
            [SERVER_ONLY, SHARED]
        )

    def test_adaptive_trust(self, db: Session):
        runtime_settings_repository.set_setting(
            db, "scoring", {"adaptive_trust": True, "adaptive_min_indicators": 1}
        )
        try:
            get_redis_client().delete(source_quality.ADAPTIVE_CACHE_KEY)
            feed = self._feed(source_quality.statistics())
            assert feed["adaptive_penalty"] == 25
            assert feed["effective_modifier"] == -25

            indicators.rebuild()
            get_opensearch_client().indices.refresh(index=indicators.INDEX)
            sighted = indicators.get_indicator(
                indicators.indicator_uuid("ip-dst", SIGHTED)
            )
            factors = {c["factor"]: c for c in sighted["score_breakdown"]}
            assert factors["adaptive_trust"]["points"] == -25
            assert "25% of feed: Feed One" in factors["adaptive_trust"]["detail"]
            # The shared value's best source is the server (60 > 50 - 25).
            shared = indicators.get_indicator(
                indicators.indicator_uuid("ip-dst", SHARED)
            )
            assert shared["score_breakdown"][0]["detail"] == "server: Server Two"
        finally:
            runtime_settings_repository.delete_setting(db, "scoring")
            get_redis_client().delete(source_quality.ADAPTIVE_CACHE_KEY)
