import time
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.auth import auth
from app.models import detection_profile as profile_models
from app.models import organisation as organisation_models
from app.models import user as user_models
from app.models import warninglist as warninglist_models
from app.repositories import (
    detection_profiles,
    indicators,
    local_warninglists,
    profile_gate,
    warninglists,
)
from app.schemas import detection_profile as profile_schemas
from app.services.opensearch import get_opensearch_client
from app.tests.api_tester import ApiTester

DAY = 86400
NOW = int(time.time())
EVENT = "10ca0000-0000-4000-8000-000000000001"

# value, type
ATTRIBUTES = [
    ("vpn.corp.example", "domain"),
    ("10.20.30.40", "ip-dst"),
    ("10.20.30.40|443", "ip-dst|port"),
    ("partner.example", "domain"),
    ("vpn-17.corp.example.net", "hostname"),
    ("old.example", "domain"),
    ("evil.example", "domain"),
]
MANAGE = ["warninglists:read", "local_warninglists:manage"]


class TestEntries:
    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("10.0.0.0/8", ("cidr", "10.0.0.0/8")),
            ("10.1.2.3/8", ("cidr", "10.0.0.0/8")),
            ("*.Corp.Example", ("suffix", "corp.example")),
            (".corp.example", ("suffix", "corp.example")),
            ("/^vpn-\\d+\\./i", ("regex", "/^vpn-\\d+\\./i")),
            ("evil.example", ("value", "evil.example")),
            ("1.2.3.4", ("value", "1.2.3.4")),
        ],
    )
    def test_kinds_are_guessed(self, raw, expected):
        assert local_warninglists.normalise(raw) == expected

    @pytest.mark.parametrize(
        "raw", ["/(a+)+$/", "/(\\w*)*/", "/(a|ab)*/", "/(a)\\1/", "/(/", "*.x", " "]
    )
    def test_bad_entries_are_refused(self, raw):
        with pytest.raises(local_warninglists.InvalidEntry):
            local_warninglists.normalise(raw)

    def test_plain_lists(self):
        text = "# Corp\n10.0.0.0/8  # offices\n\n*.corp.example\nevil.example\n"
        assert local_warninglists.parse_lines(text) == [
            {"value": "10.0.0.0/8", "comment": "offices"},
            {"value": "*.corp.example", "comment": None},
            {"value": "evil.example", "comment": None},
        ]

    def test_hits(self):
        matcher = warninglists.LocalMatcher.__new__(warninglists.LocalMatcher)
        matcher.regexes = [(4, warninglists._compile_regex("/^vpn-\\d+\\./"))]
        entries = [
            {"warninglist_id": 1, "type": "string", "value": "evil.example"},
            {"warninglist_id": 2, "type": "hostname", "value": "corp.example"},
            {"warninglist_id": 3, "type": "cidr", "range": "10.0.0.0/8"},
        ]

        def hits(type_, value):
            return matcher._hits(value, warninglists._candidates(type_, value), entries)

        assert hits("domain", "evil.example") == {1}
        assert hits("domain", "vpn.corp.example") == {2}
        assert hits("domain", "corp.example") == {2}
        assert hits("domain", "notcorp.example") == set()
        assert hits("ip-dst|port", "10.20.30.40|443") == {3}
        assert hits("hostname", "vpn-17.elsewhere") == {4}

    def test_profiles_attach_lists(self):
        ctx = {"now": NOW, "trust": {}}
        listed = {"to_ids": True, "local_list_hits": [7]}
        assert detection_profiles.failing_rule({}, listed, ctx) is None
        assert (
            detection_profiles.failing_rule({"exclude_lists": [7]}, listed, ctx)
            == "listed"
        )
        assert detection_profiles.matches({"exclude_lists": [8]}, listed, ctx)
        # An exclusion: never held back by an approval gate.
        assert "listed" in profile_gate.FORCED_REMOVALS
        rules = detection_profiles.exclusions_only({"exclude_lists": [7]})
        assert rules.exclude_lists == [7]


class TestLocalWarninglists(ApiTester):
    @pytest.fixture(scope="class", autouse=True)
    def dataset(self, cleanup):
        client = get_opensearch_client()
        client.index(
            index="misp-events",
            id=EVENT,
            body={
                "uuid": EVENT,
                "info": "local lists",
                "deleted": False,
                "published": True,
                "organisation": {"id": 961, "name": "Org 961"},
                "source": {"type": "local", "id": None, "name": None},
                "tags": [],
            },
        )
        for i, (value, type_) in enumerate(ATTRIBUTES):
            uuid = f"10ca0000-1000-4000-8000-{i:012d}"
            client.index(
                index="misp-attributes",
                id=uuid,
                body={
                    "uuid": uuid,
                    "event_uuid": EVENT,
                    "type": type_,
                    "category": "Network activity",
                    "value": value,
                    "to_ids": True,
                    "deleted": False,
                    "comment": "",
                    "timestamp": NOW - DAY,
                    "tags": [],
                },
            )
        client.indices.refresh(index="misp-events,misp-attributes")
        yield

    @pytest.fixture
    def other_org_token(self, db: Session):
        org = organisation_models.Organisation(
            name="other organisation",
            date_created="2020-01-01 01:01:01",
            date_modified="2020-01-01 01:01:01",
            type="test",
            sector="test",
            nationality="test",
            created_by=1,
            local=True,
            uuid="9a1f3c2e-4b5d-4e6f-8a7b-0c1d2e3f4a5b",
        )
        db.add(org)
        db.commit()
        user = user_models.User(
            org_id=org.id, role_id=3, email="other@org.test", hashed_password="x"
        )
        db.add(user)
        db.commit()
        yield auth.create_access_token(
            data={"sub": user.email, "scopes": MANAGE},
            expires_delta=timedelta(hours=1),
        )
        db.delete(user)
        db.delete(org)
        db.commit()

    def _flag(self, db):
        warninglists._evaluate(
            warninglists.Matcher(db),
            {"bool": {"must_not": [{"term": {"deleted": True}}]}},
        )
        indicators.refresh_values([v for v, _ in ATTRIBUTES])
        get_opensearch_client().indices.refresh(index=indicators.INDEX)

    def _hits(self):
        client = get_opensearch_client()
        return {
            h["_source"]["value"]: h["_source"].get("local_list_hits") or []
            for h in client.search(
                index="misp-attributes",
                body={
                    "size": 100,
                    "query": {"term": {"event_uuid": EVENT}},
                    "_source": ["value", "local_list_hits"],
                },
            )["hits"]["hits"]
        }

    @pytest.mark.parametrize("scopes", [MANAGE])
    def test_lists(
        self,
        client: TestClient,
        auth_token: auth.Token,
        db: Session,
        other_org_token,
    ):
        headers = {"Authorization": "Bearer " + auth_token}
        created = client.post(
            "/local-warninglists",
            json={"name": "Corporate", "description": "our ranges"},
            headers=headers,
        )
        assert created.status_code == status.HTTP_201_CREATED, created.text
        list_id = created.json()["id"]
        url = f"/local-warninglists/{list_id}"

        added = client.post(
            f"{url}/entries",
            json={
                "entries": [
                    {"value": "*.corp.example", "comment": "our domains"},
                    {"value": "10.0.0.0/8", "comment": "offices"},
                    {"value": "/^vpn-\\d+\\./"},
                    {"value": "partner.example"},
                    {
                        "value": "old.example",
                        "expires_at": (
                            datetime.now(timezone.utc) - timedelta(days=1)
                        ).isoformat(),
                    },
                ]
            },
            headers=headers,
        )
        assert added.json() == {"added": 5, "updated": 0, "removed": 0}
        bad = client.post(
            f"{url}/entries", json={"entries": [{"value": "/(a+)+/"}]}, headers=headers
        )
        assert bad.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        self._flag(db)
        hits = self._hits()
        for value in (
            "vpn.corp.example",
            "10.20.30.40",
            "10.20.30.40|443",
            "partner.example",
            "vpn-17.corp.example.net",
        ):
            assert hits[value] == [list_id], value
        # Expired: no longer matches. Not listed: nothing.
        assert hits["old.example"] == []
        assert hits["evil.example"] == []
        # The MISP lists are untouched by it.
        indicator = indicators.get_indicator(
            indicators.indicator_uuid("domain", "partner.example")
        )
        assert indicator["local_list_hits"] == [list_id]
        assert indicator["warninglist_hits"] == []

        # Only profiles attaching the list leave its matches out.
        ctx = detection_profiles.context()
        assert detection_profiles.matches({}, indicator, ctx)
        assert not detection_profiles.matches(
            {"exclude_lists": [list_id]}, indicator, ctx
        )
        response = get_opensearch_client().search(
            index=indicators.INDEX,
            body={
                "size": 100,
                "query": detection_profiles.to_query(
                    {"exclude_lists": [list_id], "types": ["domain"]}, ctx
                ),
            },
        )
        assert {h["_source"]["value"] for h in response["hits"]["hits"]} == {
            "evil.example",
            "old.example",
        }

        explained = client.post(
            "/local-warninglists/explain",
            json={"values": ["vpn.corp.example", "evil.example"]},
            headers=headers,
        ).json()["matches"]
        assert list(explained) == ["vpn.corp.example"]
        assert explained["vpn.corp.example"][0]["entry"] == "corp.example"
        assert explained["vpn.corp.example"][0]["comment"] == "our domains"

        # Another organisation neither sees it nor what it says.
        other = {"Authorization": "Bearer " + other_org_token}
        assert client.get(url, headers=other).status_code == 404
        assert client.get("/local-warninglists", headers=other).json() == []
        assert (
            client.post(
                "/local-warninglists/explain",
                json={"values": ["vpn.corp.example"]},
                headers=other,
            ).json()["matches"]
            == {}
        )
        # ...and keeps a list of the same name of its own.
        same_name = client.post(
            "/local-warninglists", json={"name": "Corporate"}, headers=other
        )
        assert same_name.status_code == status.HTTP_201_CREATED, same_name.text

        exported = client.get(f"{url}/export", headers=headers).text
        assert "*.corp.example  # our domains" in exported
        imported = client.post(
            f"{url}/import",
            json={"text": "evil.example  # sinkholed now\n", "replace": False},
            headers=headers,
        )
        assert imported.json()["added"] == 1

        # Expired entries go; a list attached to a profile can't.
        assert local_warninglists.sweep(db)["expired"] == 1
        db.add(
            profile_models.DetectionProfile(
                name="Attaching",
                rules=profile_schemas.ProfileRules(
                    exclude_lists=[list_id]
                ).model_dump(),
                created_at=datetime.now(timezone.utc),
            )
        )
        db.commit()
        refused = client.delete(url, headers=headers)
        assert refused.status_code == status.HTTP_409_CONFLICT
        db.query(profile_models.DetectionProfile).delete()
        db.commit()
        assert client.delete(url, headers=headers).status_code == 204
        assert (
            db.query(warninglist_models.WarninglistEntry)
            .filter(warninglist_models.WarninglistEntry.warninglist_id == list_id)
            .count()
            == 0
        )

    @pytest.mark.parametrize("scopes", [["warninglists:read"]])
    def test_managing_needs_the_scope(self, client: TestClient, auth_token: auth.Token):
        response = client.post(
            "/local-warninglists",
            json={"name": "Nope"},
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
