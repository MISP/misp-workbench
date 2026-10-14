import json
import time

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.auth import auth
from app.models import detection_profile as profile_models
from app.repositories import detection_profiles, indicators, profile_membership
from app.schemas import detection_profile as profile_schemas
from app.services.opensearch import get_opensearch_client
from app.services.redis import get_redis_client
from app.tests.api_tester import ApiTester

DAY = 86400
NOW = int(time.time())
FEED_EVENT = "41e40000-0000-4000-8000-000000000001"
LOCAL_EVENT = "41e40000-0000-4000-8000-000000000002"

# value -> (event, type, reported days ago, tags)
ATTRIBUTES = {
    "quiet.example": (FEED_EVENT, "domain", 60, []),
    "hit.example": (FEED_EVENT, "domain", 60, []),
    "benign.example": (FEED_EVENT, "domain", 60, []),
    "fresh.example": (FEED_EVENT, "domain", 1, []),
    "45.33.32.9": (FEED_EVENT, "ip-dst", 10, []),
    "internal.example": (FEED_EVENT, "domain", 60, ["internal:keep"]),
    "local.example": (LOCAL_EVENT, "domain", 60, []),
}
# value -> (sighting type, days ago)
SIGHTINGS = {
    "hit.example": ("positive", 2),
    # A false positive moves last_seen, but is no hit.
    "benign.example": ("false-positive", 1),
}
OWNER = "test:hit-expiry"

RULE_SETS = [
    {"hit_expiry": {"days": 30}},
    {"hit_expiry": {"days": 30, "types": {"ip-dst": 7}}},
    {"hit_expiry": {"types": {"ip-dst": 7}}},
    {"hit_expiry": {"days": 5, "exempt_tags": ["internal:*"]}},
    {"hit_expiry": {"days": 30, "exempt_sources": ["local"]}},
]


def _selected(rules, ctx=None):
    ctx = ctx or detection_profiles.context()
    response = get_opensearch_client().search(
        index=indicators.INDEX,
        body={"size": 1000, "query": detection_profiles.to_query(rules, ctx)},
    )
    return {h["_source"]["value"] for h in response["hits"]["hits"]}


def _sight(value, days_ago):
    client = get_opensearch_client()
    client.index(
        index="misp-sightings",
        body={
            "value": value,
            "type": "positive",
            "@timestamp": time.strftime(
                "%Y-%m-%dT%H:%M:%S", time.gmtime(NOW - days_ago * DAY)
            ),
            "observer": {"organisation": "hit-expiry-test"},
        },
        refresh=True,
    )
    indicators.refresh_values([value])
    client.indices.refresh(index=indicators.INDEX)


class TestHitExpiry(ApiTester):
    @pytest.fixture(scope="class", autouse=True)
    def dataset(self, cleanup):
        client = get_opensearch_client()
        client.delete_by_query(
            index="misp-sightings",
            body={"query": {"terms": {"value.keyword": list(ATTRIBUTES)}}},
            refresh=True,
            ignore=[404],
        )
        for uuid, source in (
            (FEED_EVENT, {"type": "feed", "id": 41, "name": "Feed 41"}),
            (LOCAL_EVENT, {"type": "local", "id": None, "name": None}),
        ):
            client.index(
                index="misp-events",
                id=uuid,
                body={
                    "uuid": uuid,
                    "info": "hit expiry",
                    "deleted": False,
                    "published": True,
                    "organisation": {"id": 941, "name": "Org 941"},
                    "source": source,
                    "tags": [],
                },
            )
        for i, (value, (event, type_, days, tags)) in enumerate(ATTRIBUTES.items()):
            uuid = f"41e40000-1000-4000-8000-{i:012d}"
            client.index(
                index="misp-attributes",
                id=uuid,
                body={
                    "uuid": uuid,
                    "event_uuid": event,
                    "type": type_,
                    "category": "Network activity",
                    "value": value,
                    "to_ids": True,
                    "deleted": False,
                    "comment": "",
                    "timestamp": NOW - days * DAY,
                    "tags": [{"name": t} for t in tags],
                },
            )
        for value, (type_, days) in SIGHTINGS.items():
            client.index(
                index="misp-sightings",
                body={
                    "value": value,
                    "type": type_,
                    "@timestamp": time.strftime(
                        "%Y-%m-%dT%H:%M:%S", time.gmtime(NOW - days * DAY)
                    ),
                    "observer": {"organisation": "hit-expiry-test"},
                },
            )
        client.indices.refresh(index="misp-events,misp-attributes,misp-sightings")
        indicators.rebuild()
        client.indices.refresh(index=indicators.INDEX)
        yield
        # Not wiped between test classes; the sightings tests count them.
        client.delete_by_query(
            index="misp-sightings",
            body={"query": {"terms": {"value.keyword": list(ATTRIBUTES)}}},
            refresh=True,
            ignore=[404],
        )
        get_redis_client().delete(profile_membership.state_key(OWNER))

    @pytest.fixture(autouse=True)
    def _clean(self, db: Session):
        db.query(profile_models.DetectionProfile).delete()
        db.commit()
        yield
        db.query(profile_models.DetectionProfile).delete()
        db.commit()

    def test_last_reported_leaves_sightings_out(self):
        [benign] = indicators.find_by_values(["benign.example"])["benign.example"]
        assert benign["last_reported"] == NOW - 60 * DAY
        assert benign["last_seen"] > NOW - 2 * DAY

    def test_windows_and_exemptions(self):
        everything = set(ATTRIBUTES)
        assert _selected({}) == everything
        expired = {"quiet.example", "benign.example", "internal.example"}
        expired.add("local.example")
        assert _selected(RULE_SETS[0]) == everything - expired
        assert _selected(RULE_SETS[1]) == everything - expired - {"45.33.32.9"}
        # Only the types listed expire.
        assert _selected(RULE_SETS[2]) == everything - {"45.33.32.9"}
        assert _selected(RULE_SETS[3]) == {"hit.example", "fresh.example"} | {
            "internal.example"
        }
        assert "local.example" in _selected(RULE_SETS[4])

    @pytest.mark.parametrize("rules", RULE_SETS, ids=[json.dumps(r) for r in RULE_SETS])
    def test_query_check_and_lucene_agree(self, rules):
        ctx = detection_profiles.context()
        client = get_opensearch_client()
        docs = [
            h["_source"]
            for h in client.search(
                index=indicators.INDEX,
                body={"size": 1000, "query": {"term": {"deleted": False}}},
            )["hits"]["hits"]
        ]
        by_check = {
            d["value"] for d in docs if detection_profiles.matches(rules, d, ctx)
        }
        assert _selected(rules, ctx) == by_check
        lucene = detection_profiles.to_lucene(rules, ctx)
        response = client.search(
            index=indicators.INDEX,
            body={
                "size": 1000,
                "query": {
                    "query_string": {"query": lucene["query"], "default_field": "value"}
                },
            },
        )
        assert {h["_source"]["value"] for h in response["hits"]["hits"]} == by_check

    def test_removed_as_no_hits_and_back_when_seen(self):
        rules = {"types": ["domain"], "hit_expiry": {"days": 30}}
        state = profile_membership.state_key(OWNER)
        redis = get_redis_client()
        redis.delete(state)
        # Forty days ago, every domain had been reported within the window.
        before = detection_profiles.context(now=NOW - 40 * DAY)
        diff = profile_membership.Diff(OWNER, rules, before, state)
        diff.commit(state)

        diff = profile_membership.Diff(
            OWNER, rules, detection_profiles.context(), state
        )
        removals = {r["value"]: r for batch in diff.removals() for r in batch}
        assert set(removals) == {
            "quiet.example",
            "benign.example",
            "internal.example",
            "local.example",
        }
        assert {r["reason"] for r in removals.values()} == {"no_hits"}
        diff.commit(state)

        # Seen again: back in.
        _sight("quiet.example", 0)
        diff = profile_membership.Diff(
            OWNER, rules, detection_profiles.context(), state
        )
        added = {i["value"] for batch in diff.added_indicators() for i in batch}
        assert added == {"quiet.example"}
        diff.discard()

    @pytest.mark.parametrize("scopes", [["detection_profiles:read"]])
    def test_hit_report(self, client: TestClient, auth_token: auth.Token, db: Session):
        headers = {"Authorization": "Bearer " + auth_token}
        profile = detection_profiles.create_profile(
            db,
            profile_schemas.DetectionProfileCreate(
                name="Domains",
                rules={"types": ["domain"], "hit_expiry": {"days": 30}},
            ),
        )
        report = client.get(f"/detection-profiles/{profile.id}/hits", headers=headers)
        assert report.status_code == status.HTTP_200_OK, report.text
        body = report.json()
        assert body["expiry"] is True
        assert body["window_days"] == 30
        # Whether the test above sighted quiet.example or not: from the data.
        members = _selected(profile.rules)
        assert body["members"] == len(members)
        hit = {"hit.example", "quiet.example"} & members
        assert body["hit_recently"] == len(hit)
        assert body["never_hit"] == len(members - hit)
        assert body["expired"] == 6 - len(members)
        [local] = [s for s in body["by_source"] if s["key"] == "local"]
        assert local == {
            "key": "local",
            "name": "local",
            "members": 0,
            "never_hit": 0,
            "expired": 1,
        }
        missing = client.get("/detection-profiles/99999/hits", headers=headers)
        assert missing.status_code == status.HTTP_404_NOT_FOUND
