import json
import time

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.auth import auth
from app.models import detection_profile as profile_models
from app.models import export as export_models
from app.models import notification as notification_models
from app.models import profile_release as release_models
from app.models import user as user_models
from app.repositories import detection_profiles, exports, indicators, profile_gate
from app.schemas import detection_profile as profile_schemas
from app.schemas import export as export_schemas
from app.services.opensearch import get_opensearch_client
from app.services.redis import get_redis_client
from app.tests.api_tester import ApiTester

DAY = 86400
NOW = int(time.time())
EVENT = "9a7e0000-0000-4000-8000-000000000001"
FIRST = ["one.example", "two.example", "three.example"]
LATER = ["four.example", "five.example", "six.example"]
# Joins after a preview (test_api).
AFTER = ["seven.example"]


def _write(values, offset=0, **extra):
    client = get_opensearch_client()
    for i, value in enumerate(values):
        uuid = f"9a7e0000-1000-4000-8000-{offset + i:012d}"
        client.index(
            index="misp-attributes",
            id=uuid,
            body={
                "uuid": uuid,
                "event_uuid": EVENT,
                "type": "domain",
                "category": "Network activity",
                "value": value,
                "to_ids": True,
                "deleted": False,
                "comment": "",
                "timestamp": NOW - DAY,
                "tags": [],
                **extra,
            },
        )
    client.indices.refresh(index="misp-attributes")
    indicators.refresh_values(values)
    client.indices.refresh(index=indicators.INDEX)


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


class TestGateRules:
    gate = profile_schemas.ProfileGate(
        enabled=True,
        max_additions=10,
        max_removals=5,
        hold_on_risk=["new_source", "popular_domain"],
        spike_factor=3,
        low_score=40,
    )

    def summary(self, **changes):
        return {"first": False, "added": 0, "removed": 0, "risks": {}, **changes}

    def test_risk_flags(self):
        indicator = {
            "warninglist_hits": [
                "Top 1,000,000 most-used sites from Tranco",
                "List of known Amazon AWS IP address ranges",
                "List of known sinkholes",
            ],
            "source_keys": ["feed:9"],
            "score": 30,
        }
        flags = dict(profile_gate.risk_flags(indicator, self.gate, {"feed:9": "New"}))
        assert set(flags) == {
            "popular_domain",
            "shared_infrastructure",
            "warninglisted",
            "new_source",
            "low_score",
        }
        assert flags["warninglisted"] == "List of known sinkholes"
        # An established source reporting it too: not new to anyone.
        indicator["source_keys"] = ["feed:9", "server:1"]
        assert "new_source" not in dict(
            profile_gate.risk_flags(indicator, self.gate, {"feed:9": "New"})
        )

    def test_hold_reasons(self):
        assert profile_gate.hold_reasons(self.summary(added=10), self.gate, None) == []
        assert profile_gate.hold_reasons(self.summary(added=11), self.gate, None) == [
            "11 additions, more than 10"
        ]
        assert profile_gate.hold_reasons(self.summary(removed=6), self.gate, None) == [
            "6 removals, more than 5"
        ]
        risky = self.summary(added=1, risks={"new_source": {"count": 1}})
        assert profile_gate.hold_reasons(risky, self.gate, None) == [
            "1 addition flagged new source"
        ]
        # Low scores are flagged, but this gate doesn't hold on them.
        low = self.summary(added=1, risks={"low_score": {"count": 1}})
        assert profile_gate.hold_reasons(low, self.gate, None) == []

    def test_what_is_held(self):
        too_many = profile_gate.plan(self.summary(added=11), self.gate, None)
        assert (too_many["all_added"], too_many["removed"]) == (True, False)
        risky = profile_gate.plan(
            self.summary(added=1, risks={"new_source": {"count": 1}}), self.gate, None
        )
        # Only the flagged additions (collected by summarise), not all.
        assert risky["reasons"] and not risky["all_added"]
        removals = profile_gate.plan(self.summary(removed=6), self.gate, None)
        assert (removals["all_added"], removals["removed"]) == (False, True)

    def test_spikes(self):
        gate = self.gate.model_copy(update={"max_additions": None})
        assert profile_gate.hold_reasons(self.summary(added=31), gate, 10) == [
            "31 additions, 3.1× the usual 10"
        ]
        assert profile_gate.hold_reasons(self.summary(added=30), gate, 10) == []
        # Too few to be a spike, whatever the usual.
        assert profile_gate.hold_reasons(self.summary(added=19), gate, 1) == []
        # No history yet.
        assert profile_gate.hold_reasons(self.summary(added=500), gate, None) == []

    def test_first_runs_and_open_gates_never_hold(self):
        assert (
            profile_gate.hold_reasons(
                self.summary(first=True, added=1000), self.gate, None
            )
            == []
        )
        open_gate = self.gate.model_copy(update={"enabled": False})
        assert (
            profile_gate.hold_reasons(self.summary(added=1000), open_gate, None) == []
        )

    def test_gate_settings_are_checked(self):
        with pytest.raises(ValidationError):
            profile_schemas.ProfileGate(hold_on_risk=["nope"])
        with pytest.raises(ValidationError):
            profile_schemas.ProfileGate(spike_factor=1)


class TestProfileGate(ApiTester):
    @pytest.fixture(scope="class", autouse=True)
    def dataset(self, cleanup):
        _reset_redis()
        get_opensearch_client().index(
            index="misp-events",
            id=EVENT,
            body={
                "uuid": EVENT,
                "info": "gate",
                "deleted": False,
                "published": True,
                "organisation": {"id": 951, "name": "Org 951"},
                "source": {"type": "local", "id": None, "name": None},
                "tags": [],
            },
        )
        get_opensearch_client().indices.refresh(index="misp-events")
        _write(FIRST)
        yield
        _reset_redis()

    @pytest.fixture(autouse=True)
    def profile(self, db: Session):
        def clean():
            db.query(export_models.Export).delete()
            db.query(profile_models.DetectionProfile).delete()
            db.query(notification_models.Notification).delete()
            db.commit()
            client = get_opensearch_client()
            client.delete_by_query(
                index="misp-attributes",
                body={"query": {"terms": {"value.keyword": LATER + AFTER}}},
                refresh=True,
            )
            indicators.refresh_values(LATER + AFTER)
            client.indices.refresh(index=indicators.INDEX)

        clean()
        profile = detection_profiles.create_profile(
            db,
            profile_schemas.DetectionProfileCreate(
                name="Gated",
                rules=profile_schemas.ProfileRules(types=["domain"], min_score=0),
                gate=profile_schemas.ProfileGate(enabled=True, max_additions=2),
            ),
        )
        profile_gate.forget(profile.id)
        self.profile_id = profile.id
        yield profile
        profile_gate.forget(profile.id)
        clean()

    def _releases(self, db):
        return (
            db.query(release_models.ProfileRelease)
            .filter(release_models.ProfileRelease.profile_id == self.profile_id)
            .order_by(release_models.ProfileRelease.id)
            .all()
        )

    def test_holds_until_approved(self, db: Session, api_tester_user, organisation_1):
        reviewer = user_models.User(
            org_id=organisation_1.id,
            role_id=2,
            email="reviewer@gate.test",
            hashed_password="secret",
        )
        db.add(reviewer)
        db.commit()

        # The first run releases everything: the baseline.
        profile_gate.ready(self.profile_id)
        assert [(r.status, r.added) for r in self._releases(db)] == [("baseline", 3)]

        db_export = exports.create_export(
            db,
            export_schemas.ExportCreate(
                name="gated feed",
                query="*",
                format="ndjson",
                profile_id=self.profile_id,
            ),
            api_tester_user.id,
        )

        _write(LATER, offset=10)
        # Too many additions: all of them are held, and the run goes ahead
        # without them.
        exports.run_export(db, db_export.id)
        db.refresh(db_export)
        assert db_export.status == "completed", db_export.error
        assert db_export.record_count == 3
        db.expire_all()
        hold = self._releases(db)[-1]
        assert (hold.status, hold.added, hold.reasons) == (
            "held",
            3,
            ["3 additions, more than 2"],
        )
        assert (
            db.query(notification_models.Notification)
            .filter(notification_models.Notification.user_id == reviewer.id)
            .one()
            .payload["added"]
            == 3
        )
        # Held again: the same hold, not another one (nor another notification).
        profile_gate.ready(self.profile_id)
        db.expire_all()
        assert [r.status for r in self._releases(db)] == ["baseline", "held"]

        seen = profile_gate.preview(db, self.profile_id)["fingerprint"]
        approved = profile_gate.approve(db, self.profile_id, reviewer.id, seen)
        assert approved["added"] == 3
        db.expire_all()
        assert [r.status for r in self._releases(db)] == [
            "baseline",
            "lifted",
            "approved",
        ]
        exports.run_export(db, db_export.id)
        db.refresh(db_export)
        assert db_export.status == "completed", db_export.error
        assert db_export.record_count == 6

    def test_only_flagged_additions_are_held(self, db: Session):
        db_profile = detection_profiles.get_profile(db, self.profile_id)
        detection_profiles.update_profile(
            db,
            db_profile,
            profile_schemas.DetectionProfileUpdate(
                rules=profile_schemas.ProfileRules(
                    types=["domain"], min_score=0, exclude_warninglisted=False
                ),
                gate=profile_schemas.ProfileGate(
                    enabled=True, hold_on_risk=["warninglisted"]
                ),
            ),
        )
        profile_gate.ready(self.profile_id)
        _write(LATER[:1], offset=10, warninglist_hits=["List of known sinkholes"])
        _write(LATER[1:], offset=11)
        profile_gate.ready(self.profile_id)

        released = {
            m.decode() if isinstance(m, bytes) else m
            for m in get_redis_client().smembers(
                profile_gate.baseline_key(self.profile_id)
            )
        }
        assert indicators.indicator_uuid("domain", LATER[0]) not in released
        assert {indicators.indicator_uuid("domain", v) for v in LATER[1:]} <= released
        db.expire_all()
        assert [(r.status, r.added) for r in self._releases(db)][-2:] == [
            ("released", 2),
            ("held", 1),
        ]

    def test_held_removals_stay_out(self, db: Session):
        db_profile = detection_profiles.get_profile(db, self.profile_id)
        detection_profiles.update_profile(
            db,
            db_profile,
            profile_schemas.DetectionProfileUpdate(
                gate=profile_schemas.ProfileGate(enabled=True, max_removals=0)
            ),
        )
        profile_gate.ready(self.profile_id)
        # Narrowing the profile would remove everything: those stay out there.
        detection_profiles.update_profile(
            db,
            db_profile,
            profile_schemas.DetectionProfileUpdate(
                rules=profile_schemas.ProfileRules(types=["url"], min_score=0)
            ),
        )
        profile_gate.ready(self.profile_id)
        released = get_redis_client().scard(profile_gate.baseline_key(self.profile_id))
        # The sentinel, and the three domains still released.
        assert released == 4
        db.expire_all()
        assert (self._releases(db)[-1].status, self._releases(db)[-1].removed) == (
            "held",
            3,
        )

    def test_check_looks_ahead_and_lifts(self, db: Session):
        profile_gate.ready(self.profile_id)
        _write(LATER, offset=10)
        assert profile_gate.check(self.profile_id) == ["3 additions, more than 2"]
        db.expire_all()
        assert self._releases(db)[-1].status == "held"

        # The gate opened up: the hold no longer applies.
        db_profile = detection_profiles.get_profile(db, self.profile_id)
        detection_profiles.update_profile(
            db,
            db_profile,
            profile_schemas.DetectionProfileUpdate(
                gate=profile_schemas.ProfileGate(enabled=True, max_additions=10)
            ),
        )
        assert profile_gate.check(self.profile_id) == []
        db.expire_all()
        assert self._releases(db)[-1].status == "lifted"
        # Looking ahead releases nothing: the next run still sees 3 additions.
        profile_gate.ready(self.profile_id)
        db.expire_all()
        assert (self._releases(db)[-1].status, self._releases(db)[-1].added) == (
            "released",
            3,
        )

    @pytest.mark.parametrize(
        "scopes", [["detection_profiles:read", "indicators:review"]]
    )
    def test_api(self, client: TestClient, auth_token: auth.Token, db: Session):
        headers = {"Authorization": "Bearer " + auth_token}
        url = f"/detection-profiles/{self.profile_id}/changes"

        first = client.get(url, headers=headers).json()
        assert first["changes"]["first"] is True
        assert first["reasons"] == []
        profile_gate.ready(self.profile_id)

        _write(LATER, offset=10)
        preview = client.get(url, headers=headers)
        assert preview.status_code == status.HTTP_200_OK, preview.text
        body = preview.json()
        assert body["changes"]["added"] == 3
        assert body["changes"]["added_by_type"] == {"domain": 3}
        assert body["changes"]["added_by_source"][0]["key"] == "local"
        assert body["reasons"] == ["3 additions, more than 2"]
        assert body["held"] is False

        # A dry run of an edit: only URLs would leave every domain out.
        dry = client.post(url, json={"rules": {"types": ["url"]}}, headers=headers)
        assert dry.json()["changes"]["added"] == 0
        assert dry.json()["changes"]["removed"] == 3
        assert dry.json()["changes"]["removed_by_reason"] == {"type": 3}

        profile_gate.check(self.profile_id)
        listed = client.get("/detection-profiles", headers=headers).json()
        assert [p["held"] for p in listed] == [True]

        seen = client.get(url, headers=headers).json()["fingerprint"]
        # Something joined after the reviewer looked: not what they approve.
        _write(AFTER, offset=20)
        moved = client.post(
            f"{url}/approve", json={"fingerprint": seen}, headers=headers
        )
        assert moved.status_code == status.HTTP_409_CONFLICT
        seen = client.get(url, headers=headers).json()["fingerprint"]
        approved = client.post(
            f"{url}/approve", json={"fingerprint": seen}, headers=headers
        )
        assert approved.status_code == status.HTTP_200_OK, approved.text
        assert approved.json()["status"] == "approved"
        after = client.get(url, headers=headers).json()
        assert after["held"] is False
        assert after["changes"]["added"] == 0
        assert [r["status"] for r in after["releases"]][:2] == ["approved", "lifted"]

    @pytest.mark.parametrize("scopes", [["detection_profiles:read"]])
    def test_approving_needs_the_scope(
        self, client: TestClient, auth_token: auth.Token
    ):
        response = client.post(
            f"/detection-profiles/{self.profile_id}/changes/approve",
            json={"fingerprint": "0" * 64},
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_runs_send_only_what_was_released(self, db: Session):
        from app.repositories import stream_exports

        profile_gate.ready(self.profile_id)
        # Joins after the check, before the run reads the profile.
        _write(LATER, offset=10)
        export = stream_exports.prepare_attribute_export(
            "*",
            "ndjson",
            index=stream_exports.INDICATORS_INDEX,
            profile=detection_profiles.load(self.profile_id),
        )
        export.released = profile_gate.baseline_key(self.profile_id)
        lines = "".join(stream_exports.stream(export)).splitlines()
        assert sorted(json.loads(line)["value"] for line in lines) == sorted(FIRST)

    @pytest.mark.parametrize("scopes", [["detection_profiles:update"]])
    def test_review_settings_need_a_reviewer(
        self, client: TestClient, auth_token: auth.Token
    ):
        headers = {"Authorization": "Bearer " + auth_token}
        url = f"/detection-profiles/{self.profile_id}"
        # Switching the gate off would let held changes out.
        off = client.patch(url, json={"gate": {"enabled": False}}, headers=headers)
        assert off.status_code == status.HTTP_403_FORBIDDEN
        assert "indicators:review" in off.json()["detail"]
        auto = client.patch(url, json={"auto_approve": True}, headers=headers)
        assert auto.status_code == status.HTTP_403_FORBIDDEN
        # Anything else is the editor's to change.
        renamed = client.patch(url, json={"name": "Renamed"}, headers=headers)
        assert renamed.status_code == status.HTTP_200_OK, renamed.text

    @pytest.mark.parametrize(
        "scopes", [["detection_profiles:update", "indicators:review"]]
    )
    def test_reviewers_change_review_settings(
        self, client: TestClient, auth_token: auth.Token
    ):
        response = client.patch(
            f"/detection-profiles/{self.profile_id}",
            json={"gate": {"enabled": False}},
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert response.status_code == status.HTTP_200_OK, response.text
