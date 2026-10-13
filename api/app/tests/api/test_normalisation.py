import json
import time

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.auth import auth
from app.repositories import indicators
from app.repositories import runtime_settings as runtime_settings_repository
from app.services import normalisation, scoring
from app.services.opensearch import get_opensearch_client
from app.services.redis import get_redis_client
from app.services.sinks import formatters
from app.tests.api_tester import ApiTester

EVENT = "40a10000-0000-4000-8000-000000000001"

# (type, value as received, to_ids, value as stored, issues)
CASES = [
    ("ip-dst", "1.2.3[.]4", True, "1.2.3.4", None),
    ("ip-dst", "010.001.002.003", False, "10.1.2.3", None),
    ("ip-src", "2001:0DB8:0000:0000:0000:0000:0000:0001", False, "2001:db8::1", None),
    ("ip-src", "::ffff:127.0.0.1", True, "::ffff:127.0.0.1", ["loopback-ip"]),
    ("ip-src", "10.20.30.40", True, "10.20.30.40", ["private-ip"]),
    ("ip-src", "10.20.30.41", False, "10.20.30.41", None),
    ("ip-dst", "192.0.2.77", True, "192.0.2.77", ["documentation-ip"]),
    ("ip-dst", "fe80::1", True, "fe80::1", ["link-local-ip"]),
    ("ip-dst", "224.0.0.251", True, "224.0.0.251", ["multicast-ip"]),
    ("ip-dst", "300.1.1.1", True, "300.1.1.1", ["invalid-ip"]),
    ("ip-dst", "1.2.3.0/33", True, "1.2.3.0/33", ["invalid-cidr"]),
    ("ip-dst|port", "8.8.4.4|99999", True, "8.8.4.4|99999", ["invalid-port"]),
    ("domain", "WWW.Example.COM.", True, "www.example.com", None),
    ("hostname", "c2[.]Evil[.]example", True, "c2.evil.example", None),
    (
        "url",
        "hxxps://Login.EXAMPLE.org:443/Verify?id=7#top",
        True,
        "https://login.example.org/Verify?id=7#top",
        None,
    ),
    ("email-src", "Bob[@]Example.COM", True, "Bob@example.com", None),
    (
        "domain|ip",
        "Evil[.]Example|192.168.7.7",
        True,
        "evil.example|192.168.7.7",
        ["private-ip"],
    ),
    (
        "md5",
        "D41D8CD98F00B204E9800998ECF8427E",
        True,
        "d41d8cd98f00b204e9800998ecf8427e",
        None,
    ),
    ("sha256", "abc123", True, "abc123", ["invalid-hash"]),
    (
        "filename|sha1",
        "Run.EXE|DA39A3EE5E6B4B0D3255BFEF95601890AFD80709",
        True,
        "Run.EXE|da39a3ee5e6b4b0d3255bfef95601890afd80709",
        None,
    ),
    # Not an indicator type: left alone.
    ("text", "see hxxp://example[.]org", True, "see hxxp://example[.]org", None),
]


def _uuid(i):
    return f"40a10000-1000-4000-8000-{i:012d}"


def _index(doc):
    client = get_opensearch_client()
    client.index(index="misp-attributes", id=doc["uuid"], body=doc, refresh=True)
    return client.get(index="misp-attributes", id=doc["uuid"])["_source"]


def _attribute(i, type_, value, to_ids=True):
    return {
        "uuid": _uuid(i),
        "event_uuid": EVENT,
        "type": type_,
        "category": "Network activity",
        "value": value,
        "to_ids": to_ids,
        "deleted": False,
        "comment": "",
        "timestamp": int(time.time()),
        "tags": [],
    }


class TestNormalisationConfig:
    @pytest.mark.skipif(
        not normalisation.REPO_PIPELINE_FILE.exists(),
        reason="needs the repo's opensearch/ directory",
    )
    def test_repo_pipeline_matches_the_script_and_defaults(self):
        # Regenerate with `python -m app.services.normalisation`.
        shipped = json.loads(normalisation.REPO_PIPELINE_FILE.read_text())
        assert shipped == normalisation.build_pipeline(normalisation.config())

    def test_disabled_is_a_no_op(self):
        cfg = normalisation.config({"enabled": False})
        assert normalisation.build_pipeline(cfg)["processors"] == []

    @pytest.mark.parametrize(
        "stored",
        [{"refang": "yes"}, {"tracking_params": "utm_*"}, {"tracking_params": [""]}],
    )
    def test_validate(self, stored):
        with pytest.raises(normalisation.InvalidNormalisationConfig):
            normalisation.validate(stored)


class TestNormalisation(ApiTester):
    @pytest.fixture(scope="class", autouse=True)
    def pipeline(self, cleanup):
        # The tests run against whatever the stack was set up with: put the
        # default rules in place, as the API does at startup.
        normalisation.sync(normalisation.config())
        yield
        normalisation.sync(normalisation.config())

    @pytest.mark.parametrize("case", CASES, ids=[f"{c[0]}:{c[1]}" for c in CASES])
    def test_rules(self, case):
        type_, value, to_ids, expected, issues = case
        i = CASES.index(case)
        stored = _index(_attribute(i, type_, value, to_ids))
        assert stored["value"] == expected
        assert stored.get("validation_issues") == issues
        assert stored.get("original_value") == (value if expected != value else None)
        assert "normalisation_error" not in stored

    def test_invalid_ips_are_indexed_without_expanded_ip(self):
        # expanded.ip is typed ip: setting it to a malformed value used to
        # reject the whole attribute.
        stored = _index(_attribute(100, "ip-dst", "999.1.1.1"))
        assert stored["validation_issues"] == ["invalid-ip"]
        assert "ip" not in (stored.get("expanded") or {})

    def test_edits_keep_or_drop_the_original(self):
        client = get_opensearch_client()
        doc = _attribute(101, "domain", "Evil[.]Example")
        _index(doc)
        # A partial update (a tag, say) goes through the pipeline again and
        # keeps the original.
        client.update(
            index="misp-attributes",
            id=doc["uuid"],
            body={"doc": {"comment": "tagged"}},
            refresh=True,
        )
        stored = client.get(index="misp-attributes", id=doc["uuid"])["_source"]
        assert stored["value"] == "evil.example"
        assert stored["original_value"] == "Evil[.]Example"
        # Editing the value to something else drops the stale original.
        client.update(
            index="misp-attributes",
            id=doc["uuid"],
            body={"doc": {"value": "other.example"}},
            refresh=True,
        )
        stored = client.get(index="misp-attributes", id=doc["uuid"])["_source"]
        assert stored["value"] == "other.example"
        assert "original_value" not in stored
        # And a flag that no longer applies goes away too.
        ip = _attribute(102, "ip-dst", "10.9.9.9")
        assert _index(ip)["validation_issues"] == ["private-ip"]
        client.update(
            index="misp-attributes",
            id=ip["uuid"],
            body={"doc": {"to_ids": False}},
            refresh=True,
        )
        stored = client.get(index="misp-attributes", id=ip["uuid"])["_source"]
        assert "validation_issues" not in stored

    @pytest.mark.parametrize("scopes", [["settings:update", "settings:delete"]])
    def test_settings_switch_rules(
        self, client: TestClient, auth_token: auth.Token, db: Session
    ):
        headers = {"Authorization": "Bearer " + auth_token}
        bad = client.post(
            "/settings/runtime/normalisation",
            json={"refang": "yes"},
            headers=headers,
        )
        assert bad.status_code == status.HTTP_400_BAD_REQUEST

        try:
            response = client.post(
                "/settings/runtime/normalisation",
                json={"refang": False, "strip_tracking_params": True},
                headers=headers,
            )
            assert response.status_code == status.HTTP_200_OK
            assert _index(_attribute(200, "domain", "a[.]example"))["value"] == (
                "a[.]example"
            )
            assert (
                _index(_attribute(201, "url", "https://b.example/?utm_source=x&id=1"))[
                    "value"
                ]
                == "https://b.example/?id=1"
            )
        finally:
            runtime_settings_repository.delete_setting(db, "normalisation")
            normalisation.sync(normalisation.config())

    @pytest.mark.parametrize("scopes", [["settings:update"]])
    def test_apply_to_existing(self, client: TestClient, auth_token: auth.Token):
        response = client.post(
            "/settings/runtime/normalisation/apply",
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["task"]

    def test_issues_reach_indicators_and_sinks(self):
        doc = _attribute(300, "ip-dst", "192.168.50.50")
        stored = _index(doc)
        get_redis_client().delete(indicators.LOCK_KEY)
        indicators.refresh_values([stored["value"]])
        get_opensearch_client().indices.refresh(index=indicators.INDEX)
        indicator = indicators.get_indicator(
            indicators.indicator_uuid("ip-dst", "192.168.50.50")
        )
        assert indicator["validation_issues"] == ["private-ip"]
        assert 'workbench:validation="private-ip"' in indicator["tags"]
        penalty = scoring.config()["validation_penalty"]
        assert {"factor": "validation", "points": -penalty, "detail": "private-ip"} in (
            indicator["score_breakdown"]
        )
        # Sink records carry them as tags, so a tag exclusion can drop them.
        record = formatters.build_record(stored, {})
        assert 'workbench:validation="private-ip"' in record["tags"]
