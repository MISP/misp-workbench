import time
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.auth import auth
from app.models import audit_log as audit_log_models
from app.models import detection_profile as profile_models
from app.models import edl as edl_models
from app.models import organisation as organisation_models
from app.models import user as user_models
from app.repositories import detection_profiles, edls, indicators
from app.routers.edls import RedactTokens
from app.schemas import detection_profile as profile_schemas
from app.schemas import edl as edl_schemas
from app.services.opensearch import get_opensearch_client
from app.tests.api_tester import ApiTester

DAY = 86400
NOW = int(time.time())
EVENT = "ed1e0000-0000-4000-8000-000000000001"
MANAGE = ["edls:read", "edls:manage"]

# value -> type
ATTRIBUTES = {
    "198.51.100.7": "ip-dst",
    "203.0.113.0/24": "ip-src",
    "192.0.2.44|8443": "ip-dst|port",
    "bad.example": "domain",
    "worse.example|192.0.2.45": "domain|ip",
    "https://bad.example/payload?id=1": "url",
    "d41d8cd98f00b204e9800998ecf8427e": "md5",
}


def _edl(**fields):
    return SimpleNamespace(
        **{
            "vendor": "plain",
            "list_type": "ip",
            "max_entries": None,
            "include_subdomains": False,
            **fields,
        }
    )


def _token(**fields):
    return SimpleNamespace(
        **{"revoked_at": None, "expires_at": None, "allowed_ips": [], **fields}
    )


class TestFormats:
    @pytest.mark.parametrize(
        "vendor,list_type,type_,value,expected",
        [
            ("plain", "ip", "ip-dst", "198.51.100.7", ["198.51.100.7"]),
            ("plain", "ip", "ip-src", "203.0.113.9/24", ["203.0.113.0/24"]),
            ("plain", "ip", "ip-dst", "2001:db8::1/128", ["2001:db8::1"]),
            ("plain", "ip", "ip-dst|port", "192.0.2.44|8443", ["192.0.2.44"]),
            ("plain", "ip", "domain|ip", "worse.example|192.0.2.45", ["192.0.2.45"]),
            ("plain", "ip", "ip-dst", "not an ip", []),
            (
                "plain",
                "domain",
                "domain|ip",
                "worse.example|192.0.2.45",
                ["worse.example"],
            ),
            ("plain", "domain", "domain", "Bad.Example.", ["bad.example"]),
            ("plain", "domain", "domain", "bücher.example", ["xn--bcher-kva.example"]),
            ("plain", "domain", "domain", "localhost", []),
            ("plain", "domain", "domain", "198.51.100.7", []),
            ("paloalto", "domain", "domain", "bad.example", ["bad.example"]),
            ("squid", "domain", "domain", "bad.example", ["bad.example"]),
            (
                "plain",
                "hash",
                "md5",
                "D41D8CD98F00B204E9800998ECF8427E",
                ["d41d8cd98f00b204e9800998ecf8427e"],
            ),
            ("plain", "hash", "filename|sha1", "a.exe|" + "a" * 40, ["a" * 40]),
            ("plain", "hash", "md5", "xyz", []),
            # PAN-OS URL lists: no scheme, a path of at least /.
            (
                "paloalto",
                "url",
                "url",
                "https://Bad.Example/payload?id=1#x",
                ["bad.example/payload?id=1"],
            ),
            ("paloalto", "url", "url", "http://bad.example", ["bad.example/"]),
            ("paloalto", "url", "url", "bad.example:8080/a", ["bad.example:8080/a"]),
            # * and ^ are PAN-OS wildcards: such a URL would match too much.
            ("paloalto", "url", "url", "http://bad.example/*", []),
            ("paloalto", "url", "url", "http://bad.example/" + "a" * 300, []),
            ("fortinet", "url", "url", "https://bad.example/x", ["bad.example/x"]),
            ("cisco", "url", "url", "https://bad.example/x", ["https://bad.example/x"]),
            (
                "squid",
                "url",
                "url",
                "http://bad.example/a.php?x=1",
                ["^https?://bad\\.example/a\\.php\\?x=1"],
            ),
            ("plain", "url", "url", "ftp://bad.example/x", []),
            ("plain", "url", "url", "http://bad.example/a b", []),
        ],
    )
    def test_entries(self, vendor, list_type, type_, value, expected):
        assert edls.entries(vendor, list_type, type_, value, False) == expected

    def test_subdomains(self):
        def subdomains(vendor):
            return edls.entries(vendor, "domain", "domain", "bad.example", True)

        assert subdomains("squid") == [".bad.example"]
        assert subdomains("fortinet") == ["bad.example", "*.bad.example"]
        # PAN-OS covers subdomains with its own list setting.
        assert subdomains("paloalto") == ["bad.example"]

    def test_vendors_take_their_lists(self):
        edl_schemas.EdlCreate(
            name="x", profile_id=1, list_type="url", vendor="paloalto"
        )
        with pytest.raises(ValidationError):
            edl_schemas.EdlCreate(
                name="x", profile_id=1, list_type="hash", vendor="paloalto"
            )
        with pytest.raises(ValidationError):
            edl_schemas.EdlCreate(
                name="x", profile_id=1, list_type="url", vendor="checkpoint"
            )

    def test_render_keeps_the_best_scored_up_to_the_limit(self):
        # Pages come best scored first; duplicates count once.
        pages = [
            [
                {"type": "ip-dst", "value": "192.0.2.1"},
                {"type": "ip-dst|port", "value": "192.0.2.1|80"},
                {"type": "ip-dst", "value": "192.0.2.2"},
            ],
            [{"type": "ip-dst", "value": "192.0.2.3"}],
        ]
        lines, truncated = edls.render(_edl(max_entries=2), iter(pages))
        assert lines == ["192.0.2.1", "192.0.2.2"]
        assert truncated == 1

    def test_vendor_limits(self):
        assert edls.limit_of(_edl(vendor="paloalto")) == 50_000
        assert edls.limit_of(_edl(vendor="fortinet")) == 131_072
        assert edls.limit_of(_edl(vendor="paloalto", max_entries=10)) == 10
        assert edls.limit_of(_edl()) == edl_schemas.MAX_ENTRIES


class TestTokens:
    def test_refused(self):
        now = datetime.now(timezone.utc)
        assert edls.refused(_token(), "192.0.2.1") is None
        assert edls.refused(_token(revoked_at=now), "192.0.2.1") == "revoked"
        assert (
            edls.refused(_token(expires_at=now - timedelta(seconds=1)), "192.0.2.1")
            == "expired"
        )
        assert edls.refused(_token(expires_at=now + timedelta(days=1)), None) is None
        allowed = _token(allowed_ips=["192.0.2.0/24", "2001:db8::/32"])
        assert edls.refused(allowed, "192.0.2.200") is None
        assert edls.refused(allowed, "2001:db8::5") is None
        assert edls.refused(allowed, "198.51.100.1") == "address"
        assert edls.refused(allowed, None) == "address"
        assert edls.refused(allowed, "testclient") == "address"

    def test_token_settings_are_checked(self):
        token = edl_schemas.EdlTokenCreate(
            name="fw", allowed_ips=[" 192.0.2.9/24 ", "2001:db8::1"]
        )
        assert token.allowed_ips == ["192.0.2.0/24", "2001:db8::1/128"]
        with pytest.raises(ValidationError):
            edl_schemas.EdlTokenCreate(name="fw", allowed_ips=["nope"])
        with pytest.raises(ValidationError):
            edl_schemas.EdlTokenCreate(
                name="fw", expires_at=datetime.now(timezone.utc) - timedelta(days=1)
            )

    def test_tokens_are_kept_out_of_access_logs(self):
        import logging

        record = logging.LogRecord(
            "uvicorn.access",
            logging.INFO,
            __file__,
            1,
            '%s - "%s %s HTTP/%s" %d',
            ("192.0.2.1:5000", "GET", "/edl/edl_secret-Value_1?x=1", "1.1", 200),
            None,
        )
        RedactTokens().filter(record)
        assert "secret" not in record.getMessage()
        assert "/edl/<token>?x=1" in record.getMessage()


class TestEdls(ApiTester):
    @pytest.fixture(scope="class", autouse=True)
    def dataset(self, cleanup):
        client = get_opensearch_client()
        client.index(
            index="misp-events",
            id=EVENT,
            body={
                "uuid": EVENT,
                "info": "edl",
                "deleted": False,
                "published": True,
                "organisation": {"id": 961, "name": "Org 961"},
                "source": {"type": "local", "id": None, "name": None},
                "tags": [],
            },
        )
        for i, (value, type_) in enumerate(ATTRIBUTES.items()):
            uuid = f"ed1e0000-1000-4000-8000-{i:012d}"
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
        indicators.refresh_values(list(ATTRIBUTES))
        client.indices.refresh(index=indicators.INDEX)
        yield

    @pytest.fixture(autouse=True)
    def _clean(self, db: Session):
        def clean():
            db.query(edl_models.EdlToken).delete()
            db.query(edl_models.Edl).delete()
            db.query(profile_models.DetectionProfile).delete()
            db.commit()

        clean()
        yield
        clean()

    @pytest.fixture
    def profile(self, db: Session):
        return detection_profiles.create_profile(
            db,
            profile_schemas.DetectionProfileCreate(
                name="Block", rules={"exclude_validation_issues": False}
            ),
        )

    @pytest.fixture
    def other_org_token(self, db: Session):
        org = organisation_models.Organisation(
            name="edl other organisation",
            date_created="2020-01-01 01:01:01",
            date_modified="2020-01-01 01:01:01",
            type="test",
            sector="test",
            nationality="test",
            created_by=1,
            local=True,
            uuid="2b9c4d1e-5f6a-4b7c-8d9e-0f1a2b3c4d5e",
        )
        db.add(org)
        db.commit()
        user = user_models.User(
            org_id=org.id, role_id=3, email="edl-other@org.test", hashed_password="x"
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

    @pytest.mark.parametrize("scopes", [MANAGE])
    def test_a_panos_list_end_to_end(
        self,
        client: TestClient,
        auth_token: auth.Token,
        db: Session,
        profile,
        other_org_token,
    ):
        headers = {"Authorization": "Bearer " + auth_token}
        created = client.post(
            "/edls",
            json={
                "name": "PAN-OS URLs",
                "profile_id": profile.id,
                "list_type": "url",
                "vendor": "paloalto",
            },
            headers=headers,
        )
        assert created.status_code == status.HTTP_201_CREATED, created.text
        edl_id = created.json()["id"]
        duplicate = client.post(
            "/edls",
            json={
                "name": "PAN-OS URLs",
                "profile_id": profile.id,
                "list_type": "ip",
                "vendor": "paloalto",
            },
            headers=headers,
        )
        assert duplicate.status_code == status.HTTP_409_CONFLICT
        refused = client.post(
            "/edls",
            json={
                "name": "hashes",
                "profile_id": profile.id,
                "list_type": "hash",
                "vendor": "paloalto",
            },
            headers=headers,
        )
        assert refused.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        token = client.post(
            f"/edls/{edl_id}/tokens", json={"name": "fw-01"}, headers=headers
        )
        assert token.status_code == status.HTTP_201_CREATED, token.text
        path = token.json()["path"]
        assert path == f"/edl/{token.json()['token']}"
        # Only its hash is kept.
        stored = db.get(edl_models.EdlToken, token.json()["id"])
        assert token.json()["token"] not in (stored.token_hash, stored.prefix)
        listed = client.get(f"/edls/{edl_id}/tokens", headers=headers).json()
        assert "token" not in listed[0]

        not_built = client.get(path)
        assert not_built.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        built = client.post(f"/edls/{edl_id}/build", headers=headers)
        assert built.json()["entry_count"] == 1, built.text

        # A firewall fetches it with the URL alone.
        fetched = client.get(path)
        assert fetched.status_code == status.HTTP_200_OK
        assert fetched.headers["content-type"].startswith("text/plain")
        assert fetched.text == "bad.example/payload?id=1\n"
        unchanged = client.get(path, headers={"If-None-Match": fetched.headers["ETag"]})
        assert unchanged.status_code == status.HTTP_304_NOT_MODIFIED
        db.refresh(stored)
        assert stored.use_count == 3
        audited = (
            db.query(audit_log_models.AuditLog)
            .filter(audit_log_models.AuditLog.action == "edl.fetched")
            .count()
        )
        assert audited == 3

        preview = client.get(f"/edls/{edl_id}/preview", headers=headers).json()
        assert preview["lines"] == ["bad.example/payload?id=1"]

        # The token opens its list and nothing else.
        as_bearer = {"Authorization": "Bearer " + token.json()["token"]}
        assert client.get("/edls", headers=as_bearer).status_code == 401
        assert client.get(f"/edls/{edl_id}", headers=as_bearer).status_code == 401
        assert client.get("/edl/edl_not-a-token").status_code == 404

        # Another organisation doesn't see it.
        other = {"Authorization": "Bearer " + other_org_token}
        assert client.get("/edls", headers=other).json() == []
        assert client.get(f"/edls/{edl_id}", headers=other).status_code == 404
        assert (
            client.post(
                f"/edls/{edl_id}/tokens", json={"name": "x"}, headers=other
            ).status_code
            == 404
        )

        # Revoked: gone at once.
        revoked = client.delete(
            f"/edls/{edl_id}/tokens/{token.json()['id']}", headers=headers
        )
        assert revoked.status_code == status.HTTP_204_NO_CONTENT
        assert client.get(path).status_code == status.HTTP_404_NOT_FOUND
        assert (
            client.get(f"/edls/{edl_id}", headers=headers).json()["active_tokens"] == 0
        )

        # Limited to addresses the test client isn't at.
        limited = client.post(
            f"/edls/{edl_id}/tokens",
            json={"name": "fw-02", "allowed_ips": ["192.0.2.0/24"]},
            headers=headers,
        ).json()
        assert client.get(limited["path"]).status_code == status.HTTP_403_FORBIDDEN

        # A profile an EDL reads can't be deleted.
        assert "EDL 'PAN-OS URLs'" in detection_profiles.users_of(db, profile.id)

        deleted = client.delete(f"/edls/{edl_id}", headers=headers)
        assert deleted.status_code == status.HTTP_204_NO_CONTENT
        assert client.get(limited["path"]).status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.parametrize("scopes", [["edls:read"]])
    def test_reading_isnt_managing(
        self, client: TestClient, auth_token: auth.Token, profile
    ):
        headers = {"Authorization": "Bearer " + auth_token}
        assert client.get("/edls", headers=headers).status_code == 200
        assert client.get("/edls/vendors", headers=headers).status_code == 200
        created = client.post(
            "/edls",
            json={"name": "x", "profile_id": profile.id, "list_type": "ip"},
            headers=headers,
        )
        assert created.status_code == status.HTTP_401_UNAUTHORIZED

    def test_lists_of_each_kind(self, db: Session, api_tester_user, profile):
        def build(**fields):
            edl = edls.create_edl(
                db,
                edl_schemas.EdlCreate(
                    name=f"{fields['vendor']}-{fields['list_type']}",
                    profile_id=profile.id,
                    **fields,
                ),
                api_tester_user,
            )
            edls.build(db, edl)
            assert edl.build_error is None
            return sorted(edls.preview(edl)["lines"])

        assert build(vendor="paloalto", list_type="ip") == sorted(
            ["198.51.100.7", "203.0.113.0/24", "192.0.2.44", "192.0.2.45"]
        )
        assert build(
            vendor="fortinet", list_type="domain", include_subdomains=True
        ) == [
            "*.bad.example",
            "*.worse.example",
            "bad.example",
            "worse.example",
        ]
        assert build(vendor="plain", list_type="hash") == [
            "d41d8cd98f00b204e9800998ecf8427e"
        ]
        capped = build(vendor="squid", list_type="ip", max_entries=2)
        assert len(capped) == 2

    def test_due_lists_are_refreshed(self, db: Session, api_tester_user, profile):
        edl = edls.create_edl(
            db,
            edl_schemas.EdlCreate(
                name="refresh", profile_id=profile.id, list_type="domain"
            ),
            api_tester_user,
        )
        assert edls.due(db) == [edl]
        assert edls.refresh_due(db) == 1
        assert edls.due(db) == []
        later = datetime.now(timezone.utc) + timedelta(minutes=edl.refresh_minutes)
        assert edls.due(db, later) == [edl]
