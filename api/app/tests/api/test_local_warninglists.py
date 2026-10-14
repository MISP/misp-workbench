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
MANAGE = [
    "warninglists:read",
    "local_warninglists:manage",
    "detection_profiles:read",
    "detection_profiles:update",
]


class TestEntries:
    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("10.0.0.0/8", ("cidr", "10.0.0.0/8")),
            ("10.1.2.3/8", ("cidr", "10.0.0.0/8")),
            ("*.Corp.Example", ("suffix", "corp.example")),
            (".corp.example", ("suffix", "corp.example")),
            ("/vpn-\\d+\\./i", ("regex", "/vpn-\\d+\\./i")),
            ("evil.example", ("value", "evil.example")),
            ("1.2.3.4", ("value", "1.2.3.4")),
        ],
    )
    def test_kinds_are_guessed(self, raw, expected):
        assert local_warninglists.normalise(raw) == expected

    @pytest.mark.parametrize(
        "raw", ["/(a)\\1/", "/(?=a)b/", "/(/", "/" + "a" * 300 + "/", "*.x", " "]
    )
    def test_bad_entries_are_refused(self, raw):
        with pytest.raises(local_warninglists.InvalidEntry):
            local_warninglists.normalise(raw)

    def test_regexes_take_linear_time(self):
        # Catastrophic for a backtracking engine; RE2 doesn't backtrack.
        pattern = local_warninglists.compile_local_regex("/(a+)+$/")
        started = time.monotonic()
        assert not pattern.search("a" * 5000 + "!")
        assert time.monotonic() - started < 1

    def test_plain_lists(self):
        text = "# Corp\n10.0.0.0/8  # offices\n\n*.corp.example\nevil.example\n"
        assert local_warninglists.parse_lines(text) == [
            {"value": "10.0.0.0/8", "comment": "offices"},
            {"value": "*.corp.example", "comment": None},
            {"value": "evil.example", "comment": None},
        ]

    def test_sync_sources_are_the_operators_call(self, monkeypatch):
        monkeypatch.setattr(local_warninglists, "allowed_hosts", lambda: [])
        with pytest.raises(local_warninglists.InvalidEntry):
            local_warninglists.check_source_url("https://cmdb.corp.example/r.txt")
        monkeypatch.setattr(
            local_warninglists, "allowed_hosts", lambda: ["*.corp.example"]
        )
        assert local_warninglists.check_source_url("https://cmdb.corp.example/r.txt")
        for url in ("file:///etc/passwd", "https://cmdb.other.example/r.txt"):
            with pytest.raises(local_warninglists.InvalidEntry):
                local_warninglists.check_source_url(url)

    @pytest.mark.parametrize(
        "address,forbidden",
        [
            ("169.254.169.254", True),
            ("127.0.0.1", True),
            ("::1", True),
            ("0.0.0.0", True),
            ("224.0.0.1", True),
            ("fe80::1", True),
            # A CMDB on the internal network is the point.
            ("10.1.2.3", False),
            ("192.168.1.10", False),
            ("198.51.100.7", False),
        ],
    )
    def test_destinations_a_sync_never_reaches(self, address, forbidden):
        assert local_warninglists._forbidden(address) is forbidden

    def test_hits(self):
        matcher = local_warninglists.LocalMatcher.__new__(
            local_warninglists.LocalMatcher
        )
        matcher.regexes = [
            (4, local_warninglists.compile_local_regex("/^vpn-\\d+\\./"))
        ]
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
        # Members are looked up once per context (here, given).
        ctx = {"now": NOW, "trust": {}, "_list_members": {7: {"u1"}, 8: set()}}
        listed = {"uuid": "u1", "to_ids": True}
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

    def _evaluate(self, db):
        indicators.refresh_values([v for v, _ in ATTRIBUTES])
        get_opensearch_client().indices.refresh(index=indicators.INDEX)
        local_warninglists.evaluate_all(db)

    def _uuid(self, value):
        type_ = dict(ATTRIBUTES)[value]
        return indicators.indicator_uuid(type_, value)

    def _on(self, list_id):
        members = local_warninglists.members(list_id)
        return {v for v, _ in ATTRIBUTES if self._uuid(v) in members}

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
            f"{url}/entries", json={"entries": [{"value": "/(a)\\1/"}]}, headers=headers
        )
        assert bad.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        self._evaluate(db)
        # Expired (old.example) no longer matches; evil.example isn't listed.
        assert self._on(list_id) == {
            "vpn.corp.example",
            "10.20.30.40",
            "10.20.30.40|443",
            "partner.example",
            "vpn-17.corp.example.net",
        }
        indicator = indicators.get_indicator(self._uuid("partner.example"))
        # Private: nothing on the indicator (anyone can query those), and the
        # MISP lists are untouched by it.
        assert "local_list_hits" not in indicator
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

        hits = client.post(
            "/local-warninglists/hits",
            json={"indicators": [indicator["uuid"], self._uuid("evil.example")]},
            headers=headers,
        ).json()["hits"]
        assert hits == {indicator["uuid"]: [list_id]}

        # A value without an indicator yet is matched as it comes.
        fresh = {
            "type": "domain",
            "value": "fresh.corp.example",
            "to_ids": True,
            "timestamp": NOW,
            "tags": [],
        }
        assert detection_profiles.attribute_matches({}, fresh, {}, ctx)
        assert not detection_profiles.attribute_matches(
            {"exclude_lists": [list_id]}, fresh, {}, ctx
        )
        # Explore can't leave private members out: the query says so.
        assert detection_profiles.to_lucene({"exclude_lists": [list_id]}, ctx)[
            "snapshot"
        ]

        # Another organisation neither sees it nor what it says.
        other = {"Authorization": "Bearer " + other_org_token}
        assert client.get(url, headers=other).status_code == 404
        # ...nor can it compare what rules attaching it leave out.
        for path in ("/detection-profiles/preview", "/detection-profiles/query"):
            probe = client.post(
                path, json={"rules": {"exclude_lists": [list_id]}}, headers=other
            )
            assert probe.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY, path
        assert (
            client.post(
                "/local-warninglists/hits",
                json={"indicators": [indicator["uuid"]]},
                headers=other,
            ).json()["hits"]
            == {}
        )
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
        swept = local_warninglists.sweep(db)
        assert swept["expired"] == 1
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
        # Around another organisation's list, a profile's rules can't be
        # dry-run or changed (and the outputs compared) but by admins.
        attaching = (
            db.query(profile_models.DetectionProfile)
            .filter(profile_models.DetectionProfile.name == "Attaching")
            .one()
        )
        dry = client.post(
            f"/detection-profiles/{attaching.id}/changes",
            json={"rules": {"tags": ["probe"], "exclude_lists": [list_id]}},
            headers=other,
        )
        assert dry.status_code == status.HTTP_403_FORBIDDEN
        edit = client.patch(
            f"/detection-profiles/{attaching.id}",
            json={"rules": {"tags": ["probe"], "exclude_lists": [list_id]}},
            headers=other,
        )
        assert edit.status_code == status.HTTP_403_FORBIDDEN
        renamed = client.patch(
            f"/detection-profiles/{attaching.id}",
            json={"name": "Renamed"},
            headers=other,
        )
        assert renamed.status_code == status.HTTP_200_OK, renamed.text
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


class FakeResponse:
    def __init__(self, body: bytes, status_code: int = 200, redirect: bool = False):
        self.body = body
        self.status_code = status_code
        self.is_redirect = redirect

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def raise_for_status(self):
        if self.status_code >= 400:
            import requests

            raise requests.HTTPError(f"{self.status_code}")

    def iter_content(self, size):
        yield self.body


class TestDestinations:
    def test_destinations_are_checked_when_fetching(self, monkeypatch):
        monkeypatch.setattr(
            local_warninglists, "allowed_hosts", lambda: ["cmdb.corp.example"]
        )

        def resolves_to(address):
            return lambda host, port: {address}

        monkeypatch.setattr(
            local_warninglists, "_resolve", resolves_to("169.254.169.254")
        )
        with pytest.raises(local_warninglists.InvalidEntry, match="may not reach"):
            local_warninglists._check_destination("http://cmdb.corp.example/r.txt")
        monkeypatch.setattr(local_warninglists, "_resolve", resolves_to("10.1.2.3"))
        local_warninglists._check_destination("http://cmdb.corp.example/r.txt")

        def unresolvable(host, port):
            raise local_warninglists.socket.gaierror("no such host")

        monkeypatch.setattr(local_warninglists, "_resolve", unresolvable)
        with pytest.raises(local_warninglists.InvalidEntry, match="doesn't resolve"):
            local_warninglists._check_destination("http://cmdb.corp.example/r.txt")

    def test_exports_read_back_as_imports(self):
        class Entry:
            def __init__(self, kind, value, comment=None):
                self.kind, self.value, self.comment = kind, value, comment

        class Query:
            def __init__(self, rows):
                self.rows = rows

            def filter(self, *args):
                return self

            def order_by(self, *args):
                return self.rows

        class Db:
            def query(self, model):
                return Query(
                    [
                        Entry("suffix", "corp.example", "ours"),
                        Entry("value", "evil.example"),
                    ]
                )

        class List:
            name = "Corporate"
            id = 1

        text = "".join(local_warninglists.export_lines(Db(), List()))
        assert local_warninglists.parse_lines(text) == [
            {"value": "*.corp.example", "comment": "ours"},
            {"value": "evil.example", "comment": None},
        ]


class TestListLifecycle(ApiTester):
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
        client.indices.refresh(index="misp-events")
        yield

    def _attribute(self, i, value, type_="domain"):
        client = get_opensearch_client()
        uuid = f"10ca0000-2000-4000-8000-{i:012d}"
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
        client.indices.refresh(index="misp-attributes")
        indicators.refresh_values([value])
        client.indices.refresh(index=indicators.INDEX)
        return indicators.indicator_uuid(type_, value)

    @pytest.mark.parametrize("scopes", [MANAGE])
    def test_lifecycle(
        self, client: TestClient, auth_token: auth.Token, db: Session, monkeypatch
    ):
        headers = {"Authorization": "Bearer " + auth_token}
        created = client.post(
            "/local-warninglists", json={"name": "Partners"}, headers=headers
        )
        list_id = created.json()["id"]
        url = f"/local-warninglists/{list_id}"
        again = client.post(
            "/local-warninglists", json={"name": "Partners"}, headers=headers
        )
        assert again.status_code == status.HTTP_409_CONFLICT
        assert client.get(url, headers=headers).json()["name"] == "Partners"
        assert [
            w["id"] for w in client.get("/local-warninglists", headers=headers).json()
        ] == [list_id]

        # Sources are the operator's call: none allowed by default.
        refused = client.patch(
            url, json={"source_url": "https://cmdb.corp.example/r.txt"}, headers=headers
        )
        assert refused.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert (
            client.post(f"{url}/sync", headers=headers).status_code
            == status.HTTP_400_BAD_REQUEST
        )

        monkeypatch.setattr(
            local_warninglists, "allowed_hosts", lambda: ["cmdb.corp.example"]
        )
        monkeypatch.setattr(
            local_warninglists, "_resolve", lambda host, port: {"10.1.2.3"}
        )
        updated = client.patch(
            url,
            json={
                "source_url": "https://cmdb.corp.example/r.txt",
                "description": "partners",
            },
            headers=headers,
        )
        assert updated.status_code == status.HTTP_200_OK, updated.text

        bodies = iter(
            [
                FakeResponse(b"# partners\npartner.example  # main\n*.partner.net\n"),
                FakeResponse(b"", redirect=True),
                FakeResponse(b"", status_code=500),
            ]
        )
        monkeypatch.setattr("requests.get", lambda *a, **k: next(bodies))
        synced = client.post(f"{url}/sync", headers=headers).json()
        assert synced["sync_error"] is None
        assert synced["entry_count"] == 2
        redirected = client.post(f"{url}/sync", headers=headers).json()
        assert "redirects" in redirected["sync_error"]
        # A failed sync keeps what the last one brought.
        failed = client.post(f"{url}/sync", headers=headers).json()
        assert failed["sync_error"] and failed["entry_count"] == 2

        page = client.get(
            f"{url}/entries", params={"q": "partner.net"}, headers=headers
        ).json()
        assert [e["value"] for e in page["items"]] == ["partner.net"]
        assert page["items"][0]["origin"] == "sync"

        # Members: a full run, then the indicators written since.
        listed = self._attribute(1, "partner.example")
        local_warninglists.evaluate_all(db)
        assert local_warninglists.members(list_id) == {listed}
        newcomer = self._attribute(2, "api.partner.net")
        local_warninglists.evaluate_recent(db)
        assert local_warninglists.members(list_id) == {listed, newcomer}

        removed = client.post(
            f"{url}/entries/delete",
            json={"ids": [page["items"][0]["id"]]},
            headers=headers,
        )
        assert removed.json()["removed"] == 1
        local_warninglists.evaluate_all(db)
        assert local_warninglists.members(list_id) == {listed}

        # Disabled: no members, nothing matched.
        disabled = client.patch(url, json={"enabled": False}, headers=headers)
        assert disabled.json()["enabled"] is False
        local_warninglists.evaluate_all(db)
        assert local_warninglists.members(list_id) == set()
        assert (
            client.post(
                "/local-warninglists/explain",
                json={"values": ["partner.example"]},
                headers=headers,
            ).json()["matches"]
            == {}
        )
        client.patch(url, json={"enabled": True}, headers=headers)

        # Created from a URL: fetched at once.
        assert client.get("/local-warninglists/sources", headers=headers).json() == {
            "hosts": ["cmdb.corp.example"]
        }
        bodies = iter([FakeResponse(b"10.0.0.0/8  # offices\n")])
        from_url = client.post(
            "/local-warninglists",
            json={"name": "Ranges", "source_url": "https://cmdb.corp.example/r.txt"},
            headers=headers,
        ).json()
        assert (from_url["entry_count"], from_url["sync_error"]) == (1, None)
        client.delete(f"/local-warninglists/{from_url['id']}", headers=headers)

        # A due sync runs with the sweep.
        bodies = iter([FakeResponse(b"partner.example\n")])
        db.expire_all()
        db_list = db.get(warninglist_models.Warninglist, list_id)
        db_list.synced_at = None
        db.commit()
        swept = local_warninglists.sweep(db)
        assert swept["synced"] == 1

        assert client.delete(url, headers=headers).status_code == 204
        assert local_warninglists.members(list_id) == set()
