import json
import time
from datetime import datetime, timezone

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.auth import auth
from app.models import detection_profile as profile_models
from app.models import indicator_review as review_models
from app.models import warninglist as warninglist_models
from app.repositories import detection_profiles, indicators, warninglists
from app.schemas import detection_profile as profile_schemas
from app.schemas import indicator_review as review_schemas
from app.services.opensearch import get_opensearch_client
from app.services.redis import get_redis_client
from app.tests.api_tester import ApiTester

DAY = 86400
NOW = int(time.time())

FEED_EVENT = "7e7e0000-0000-4000-8000-000000000001"
LOCAL_EVENT = "7e7e0000-0000-4000-8000-000000000002"
HASH = "0cc175b9c0f1b6a831c399e269772661"

# value -> (event, type, to_ids)
ATTRIBUTES = [
    ("waits.example", LOCAL_EVENT, "domain", True),
    ("approve.example", LOCAL_EVENT, "domain", True),
    ("reject.example", LOCAL_EVENT, "domain", True),
    ("snooze.example", LOCAL_EVENT, "domain", True),
    # Approved by the auto-approve profile (md5 from the feed).
    (HASH, FEED_EVENT, "md5", True),
    # Not flagged for IDS: the profile doesn't select it, so it never waits.
    ("quiet.example", LOCAL_EVENT, "domain", False),
]
REVIEWED = {"types": ["domain", "md5"], "require_approval": True}
AUTO = {"types": ["md5"], "sources": ["feed:5"]}

# Rule sets the query, the per-indicator check and Lucene must agree on,
# once decisions are taken.
RULE_SETS = [
    {"require_approval": True},
    {"require_approval": True, "types": ["domain"]},
    {"exclude_rejected": True},
    {"exclude_rejected": True, "to_ids": False},
]


def _uuid(value, type_="domain"):
    return indicators.indicator_uuid(type_, value)


def _reset_redis():
    get_redis_client().delete(
        indicators.LOCK_KEY,
        indicators.CURSOR_KEY,
        indicators.BUILT_AT_KEY,
        indicators.REBUILD_QUEUED_KEY,
        indicators.DIRTY_KEY,
        indicators.DIRTY_EVENTS_KEY,
    )


def _selected(rules):
    ctx = detection_profiles.context()
    response = get_opensearch_client().search(
        index=indicators.INDEX,
        body={"size": 1000, "query": detection_profiles.to_query(rules, ctx)},
    )
    return {h["_source"]["value"] for h in response["hits"]["hits"]}


def _live():
    client = get_opensearch_client()
    client.indices.refresh(index=indicators.INDEX)
    return [
        h["_source"]
        for h in client.search(
            index=indicators.INDEX,
            body={"size": 1000, "query": {"term": {"deleted": False}}},
        )["hits"]["hits"]
    ]


class TestReviewRules:
    ctx = {
        "now": NOW,
        "trust": {},
        "auto_approve": [profile_schemas.ProfileRules(types=["md5"], to_ids=False)],
    }

    @pytest.mark.parametrize(
        "rules,indicator,reason",
        [
            ({"require_approval": True}, {"type": "domain", "to_ids": True}, "pending"),
            (
                {"require_approval": True},
                {"type": "domain", "to_ids": True, "review": {"status": "approved"}},
                None,
            ),
            (
                {"require_approval": True},
                {"type": "domain", "to_ids": True, "review": {"status": "snoozed"}},
                "pending",
            ),
            # Auto-approved...
            ({"require_approval": True}, {"type": "md5", "to_ids": True}, None),
            # ...unless an analyst rejected it.
            (
                {"require_approval": True},
                {"type": "md5", "to_ids": True, "review": {"status": "rejected"}},
                "rejected",
            ),
            (
                {"exclude_rejected": True},
                {"type": "domain", "to_ids": True, "review": {"status": "rejected"}},
                "rejected",
            ),
            ({"exclude_rejected": True}, {"type": "domain", "to_ids": True}, None),
            # Without the rule, a rejection changes nothing.
            (
                {},
                {"type": "domain", "to_ids": True, "review": {"status": "rejected"}},
                None,
            ),
        ],
    )
    def test_reasons(self, rules, indicator, reason):
        assert detection_profiles.failing_rule(rules, indicator, self.ctx) == reason

    def test_fresh_values_are_judged_on_their_stored_decision(self):
        fresh = detection_profiles.attribute_indicator(
            {"type": "domain", "value": "new.example", "to_ids": True}
        )
        ctx = {**self.ctx, "_reviews": {_uuid("new.example"): "rejected"}}
        assert detection_profiles.failing_rule(
            {"exclude_rejected": True, "to_ids": False}, fresh, ctx
        ) == ("rejected")
        ctx = {**self.ctx, "_reviews": {_uuid("new.example"): "approved"}}
        assert detection_profiles.matches(
            {"require_approval": True, "sources": ["unknown"]}, fresh, ctx
        )

    def test_exclusions_keep_rejections(self):
        rules = detection_profiles.exclusions_only({"require_approval": True})
        assert rules.exclude_rejected and not rules.require_approval

    def test_auto_approve_profiles_cant_require_approval(self):
        with pytest.raises(ValidationError):
            profile_schemas.DetectionProfileCreate(
                name="Circular",
                auto_approve=True,
                rules=profile_schemas.ProfileRules(require_approval=True),
            )

    def test_deciders_are_shown_to_their_organisation_only(self):
        from types import SimpleNamespace

        from app.repositories import indicator_reviews

        def entries():
            return [
                {"user_email": "a@one.test", "user_org_id": 1},
                {"user_email": "b@two.test", "user_org_id": 2},
            ]

        def viewer(org_id, scopes):
            return SimpleNamespace(org_id=org_id, role=SimpleNamespace(scopes=scopes))

        shown = indicator_reviews.redact(entries(), viewer(1, ["attributes:read"]))
        assert [e["user_email"] for e in shown] == ["a@one.test", None]
        shown = indicator_reviews.redact(entries(), viewer(3, ["audit_logs:admin"]))
        assert [e["user_email"] for e in shown] == ["a@one.test", "b@two.test"]

    def test_requests_are_consistent(self):
        with pytest.raises(ValidationError):
            review_schemas.ReviewDecisionRequest(indicators=["x"], action="snooze")
        with pytest.raises(ValidationError):
            review_schemas.ReviewDecisionRequest(
                indicators=["x"], action="approve", allowlist=True
            )
        review_schemas.ReviewDecisionRequest(
            indicators=["x"], action="reject", allowlist=True
        )


class TestReviewQueue(ApiTester):
    @pytest.fixture(scope="class", autouse=True)
    def dataset(self, cleanup):
        client = get_opensearch_client()
        _reset_redis()
        for uuid, source in (
            (FEED_EVENT, {"type": "feed", "id": 5, "name": "Feed Five"}),
            (LOCAL_EVENT, {"type": "local", "id": None, "name": None}),
        ):
            client.index(
                index="misp-events",
                id=uuid,
                body={
                    "uuid": uuid,
                    "info": "review queue",
                    "deleted": False,
                    "published": True,
                    "organisation": {"id": 931, "name": "Org 931"},
                    "source": source,
                    "tags": [],
                },
            )
        for i, (value, event, type_, to_ids) in enumerate(ATTRIBUTES):
            uuid = f"7e7e0000-1000-4000-8000-{i:012d}"
            client.index(
                index="misp-attributes",
                id=uuid,
                body={
                    "uuid": uuid,
                    "event_uuid": event,
                    "type": type_,
                    "category": "Network activity",
                    "value": value,
                    "to_ids": to_ids,
                    "deleted": False,
                    "comment": "",
                    "timestamp": NOW - DAY,
                    "tags": [],
                },
            )
        client.indices.refresh(index="misp-events,misp-attributes")
        indicators.rebuild()
        client.indices.refresh(index=indicators.INDEX)
        yield
        _reset_redis()

    @pytest.fixture(autouse=True)
    def profiles(self, db: Session):
        db.query(profile_models.DetectionProfile).delete()
        db.query(review_models.IndicatorReview).delete()
        db.commit()
        for name, rules, auto in (
            ("Reviewed", REVIEWED, False),
            ("Feed hashes", AUTO, True),
        ):
            detection_profiles.create_profile(
                db,
                profile_schemas.DetectionProfileCreate(
                    name=name,
                    rules=profile_schemas.ProfileRules(**rules),
                    auto_approve=auto,
                ),
            )
        yield
        db.query(profile_models.DetectionProfile).delete()
        db.query(review_models.IndicatorReview).delete()
        db.commit()
        indicators.refresh_values([a[0] for a in ATTRIBUTES])
        get_opensearch_client().indices.refresh(index=indicators.INDEX)

    def _decide(self, client, headers, values, action, **extra):
        response = client.post(
            "/indicators/review/decisions",
            json={
                "indicators": [
                    _uuid(v, "md5" if v == HASH else "domain") for v in values
                ],
                "action": action,
                **extra,
            },
            headers=headers,
        )
        assert response.status_code == status.HTTP_200_OK, response.text
        return response.json()

    def _queue(self, client, headers, **params):
        response = client.get("/indicators/review", params=params, headers=headers)
        assert response.status_code == status.HTTP_200_OK, response.text
        return response.json()

    @pytest.mark.parametrize("scopes", [["attributes:read", "indicators:review"]])
    def test_review(
        self, client: TestClient, auth_token: auth.Token, db: Session, api_tester_user
    ):
        headers = {"Authorization": "Bearer " + auth_token}

        queue = self._queue(client, headers)
        # The feed hash is auto-approved; quiet.example isn't for IDS.
        assert {i["value"] for i in queue["items"]} == {
            "waits.example",
            "approve.example",
            "reject.example",
            "snooze.example",
        }
        assert queue["items"][0]["pending_for"][0]["name"] == "Reviewed"
        assert _selected(REVIEWED) == {HASH}

        self._decide(client, headers, ["approve.example"], "approve")
        self._decide(client, headers, ["reject.example"], "reject", reason="benign CDN")
        self._decide(client, headers, ["snooze.example"], "snooze", snooze_days=7)

        assert {i["value"] for i in self._queue(client, headers)["items"]} == {
            "waits.example"
        }
        assert _selected(REVIEWED) == {HASH, "approve.example"}
        ctx = detection_profiles.context()
        by_value = {i["value"]: i for i in _live()}
        assert by_value["approve.example"]["review"]["status"] == "approved"
        assert (
            detection_profiles.failing_rule(REVIEWED, by_value["reject.example"], ctx)
            == "rejected"
        )
        assert (
            detection_profiles.failing_rule(REVIEWED, by_value["waits.example"], ctx)
            == "pending"
        )
        assert by_value["snooze.example"]["review"]["until"] > NOW + 6 * DAY

        summary = client.get("/indicators/review/summary", headers=headers).json()
        assert summary["pending"] == 1
        assert (summary["approved"], summary["rejected"], summary["snoozed"]) == (
            1,
            1,
            1,
        )
        assert [p["name"] for p in summary["auto_approve_profiles"]] == ["Feed hashes"]

        rejected = client.get(
            "/indicators/review/decisions",
            params={"status": "rejected"},
            headers=headers,
        ).json()
        assert rejected["items"][0]["value"] == "reject.example"
        assert rejected["items"][0]["reason"] == "benign CDN"
        assert rejected["items"][0]["user_email"] == api_tester_user.email

        # Taking it back puts it in the queue again, and the log keeps both.
        self._decide(client, headers, ["reject.example"], "reopen")
        assert "reject.example" in {
            i["value"] for i in self._queue(client, headers)["items"]
        }
        detail = client.get(
            f"/indicators/{_uuid('reject.example')}/review", headers=headers
        ).json()
        assert detail["decision"]["status"] == "pending"
        assert [h["action"] for h in detail["history"]] == ["reopened", "rejected"]

        # An analyst's rejection beats an auto-approve profile.
        self._decide(client, headers, [HASH], "reject")
        assert _selected(REVIEWED) == {"approve.example"}

    @pytest.mark.parametrize("scopes", [["attributes:read", "indicators:review"]])
    @pytest.mark.parametrize("rules", RULE_SETS, ids=[json.dumps(r) for r in RULE_SETS])
    def test_query_check_and_lucene_agree(
        self, client: TestClient, auth_token: auth.Token, rules
    ):
        headers = {"Authorization": "Bearer " + auth_token}
        self._decide(client, headers, ["approve.example"], "approve")
        self._decide(client, headers, ["reject.example", HASH], "reject")
        self._decide(client, headers, ["snooze.example"], "snooze", snooze_days=1)

        ctx = detection_profiles.context()
        by_check = {
            d["value"] for d in _live() if detection_profiles.matches(rules, d, ctx)
        }
        assert _selected(rules) == by_check
        lucene = detection_profiles.to_lucene(rules, ctx)
        response = get_opensearch_client().search(
            index=indicators.INDEX,
            body={
                "size": 1000,
                "query": {
                    "query_string": {"query": lucene["query"], "default_field": "value"}
                },
            },
        )
        assert {h["_source"]["value"] for h in response["hits"]["hits"]} == by_check

    @pytest.mark.parametrize("scopes", [["attributes:read", "indicators:review"]])
    def test_allowlist(self, client: TestClient, auth_token: auth.Token, db: Session):
        headers = {"Authorization": "Bearer " + auth_token}
        self._decide(client, headers, ["reject.example"], "reject", allowlist=True)
        by_value = {i["value"]: i for i in _live()}
        assert by_value["reject.example"]["warninglist_hits"] == [
            warninglists.ALLOWLIST_NAME
        ]
        # Every profile leaves it out now, not only those reading decisions.
        assert "reject.example" not in _selected({})

        self._decide(client, headers, ["reject.example"], "approve")
        by_value = {i["value"]: i for i in _live()}
        assert by_value["reject.example"]["warninglist_hits"] == []
        db.query(warninglist_models.Warninglist).filter(
            warninglist_models.Warninglist.name == warninglists.ALLOWLIST_NAME
        ).delete()
        db.commit()

    @pytest.mark.parametrize("scopes", [["attributes:read"]])
    def test_deciding_needs_the_scope(self, client: TestClient, auth_token: auth.Token):
        headers = {"Authorization": "Bearer " + auth_token}
        assert self._queue(client, headers)["total"] == 4
        response = client.post(
            "/indicators/review/decisions",
            json={"indicators": [_uuid("waits.example")], "action": "approve"},
            headers=headers,
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.parametrize("scopes", [["attributes:read", "indicators:review"]])
    def test_unknown_indicators(self, client: TestClient, auth_token: auth.Token):
        headers = {"Authorization": "Bearer " + auth_token}
        response = client.post(
            "/indicators/review/decisions",
            json={"indicators": [_uuid("never.example")], "action": "approve"},
            headers=headers,
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_fresh_values_keep_their_decision(self, db: Session):
        # Decided before, then purged: the value comes back as an attribute
        # before its indicator does.
        db.add(
            review_models.IndicatorReview(
                indicator_uuid=_uuid("returns.example"),
                type="domain",
                value="returns.example",
                status="rejected",
                decided_at=datetime.now(timezone.utc),
            )
        )
        db.commit()
        attribute = {
            "type": "domain",
            "value": "returns.example",
            "to_ids": True,
            "timestamp": NOW,
            "tags": [],
        }
        ctx = detection_profiles.context()
        for rules in ({"exclude_rejected": True}, {"require_approval": True}):
            assert not detection_profiles.attribute_matches(rules, attribute, {}, ctx)
        assert detection_profiles.attribute_matches({}, attribute, {}, ctx)

    def test_no_queue_without_a_profile_requiring_approval(self, db: Session):
        db.query(profile_models.DetectionProfile).filter(
            profile_models.DetectionProfile.name == "Reviewed"
        ).delete()
        db.commit()
        from app.repositories import indicator_reviews

        assert indicator_reviews.queue(db)["total"] == 0
        assert indicator_reviews.summary(db)["pending"] == 0
