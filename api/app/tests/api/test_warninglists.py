import json
from unittest.mock import patch

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.auth import auth
from app.models import warninglist as warninglist_models
from app.repositories import lookup as lookup_repository
from app.repositories import warninglists as warninglists_repository
from app.services.opensearch import get_opensearch_client
from app.services.redis import get_redis_client
from app.tests.api_tester import ApiTester
from app.worker import tasks

EVENT = "abababab-abab-4bab-8bab-abababababab"
RESOLVER = "abababab-0000-4000-8000-000000000001"
PRIVATE = "abababab-0000-4000-8000-000000000002"
TOP_DOMAIN = "abababab-0000-4000-8000-000000000003"
EVIL = "abababab-0000-4000-8000-000000000004"

LISTS = {
    "test-resolvers": {
        "name": "Test public resolvers",
        "type": "string",
        "version": 1,
        "matching_attributes": ["ip-src", "ip-dst"],
        "list": ["8.8.8.8", "1.1.1.1"],
    },
    "test-rfc1918": {
        "name": "Test RFC1918",
        "type": "cidr",
        "version": 1,
        "matching_attributes": ["ip-src", "ip-dst"],
        "list": ["10.0.0.0/8", "192.168.0.0/16"],
    },
    "test-top-domains": {
        "name": "Test top domains",
        "type": "hostname",
        "version": 1,
        "matching_attributes": ["domain", "hostname", "url"],
        "list": ["example.com"],
    },
}


def _attribute(uuid, type_, value):
    return {
        "uuid": uuid,
        "event_uuid": EVENT,
        "type": type_,
        "category": "Network activity",
        "value": value,
        "to_ids": True,
        "deleted": False,
        "comment": "",
        "timestamp": 1700000000,
        "tags": [],
    }


def _hits(uuid):
    doc = get_opensearch_client().get(index="misp-attributes", id=uuid)["_source"]
    return doc.get("warninglist_hits") or []


class TestWarninglists(ApiTester):
    @pytest.fixture(scope="class", autouse=True)
    def dataset(self, cleanup, db: Session, tmp_path_factory):
        lists_dir = tmp_path_factory.mktemp("warninglists")
        for folder, content in LISTS.items():
            (lists_dir / folder).mkdir()
            (lists_dir / folder / "list.json").write_text(json.dumps(content))

        client = get_opensearch_client()
        for doc in (
            _attribute(RESOLVER, "ip-dst", "8.8.8.8"),
            _attribute(PRIVATE, "ip-dst", "10.1.2.3"),
            _attribute(TOP_DOMAIN, "domain", "www.example.com"),
            _attribute(EVIL, "domain", "evil.example.net"),
        ):
            client.index(index="misp-attributes", id=doc["uuid"], body=doc)
        client.index(
            index="misp-events",
            id=EVENT,
            body={
                "uuid": EVENT,
                "info": "warninglist test",
                "deleted": False,
                "tags": [],
            },
        )
        client.indices.refresh(index="misp-attributes")

        redis = get_redis_client()
        redis.delete(
            warninglists_repository.LOCK_KEY,
            warninglists_repository.CURSOR_KEY,
            warninglists_repository.DIRTY_KEY,
        )
        counts = warninglists_repository.update_warninglists(
            db, lists_dir=str(lists_dir)
        )
        assert counts["created"] == 3
        warninglists_repository.evaluate_all(db)
        yield
        ids = [w.id for w in db.query(warninglist_models.Warninglist).all()]
        client.delete_by_query(
            index=warninglists_repository.ENTRIES_INDEX,
            body={"query": {"terms": {"warninglist_id": ids}}},
            refresh=True,
        )
        db.query(warninglist_models.Warninglist).delete()
        db.commit()

    def _headers(self, token):
        return {"Authorization": "Bearer " + token}

    def test_attributes_are_flagged(self):
        assert _hits(RESOLVER) == ["Test public resolvers"]
        assert _hits(PRIVATE) == ["Test RFC1918"]
        assert _hits(TOP_DOMAIN) == ["Test top domains"]
        assert _hits(EVIL) == []

    def test_reloading_unchanged_lists_is_a_no_op(self, db: Session, tmp_path):
        for folder, content in LISTS.items():
            (tmp_path / folder).mkdir()
            (tmp_path / folder / "list.json").write_text(json.dumps(content))
        counts = warninglists_repository.update_warninglists(
            db, lists_dir=str(tmp_path)
        )
        assert counts["unchanged"] == 3
        assert counts["changed"] is False

    @pytest.mark.parametrize("scopes", [["warninglists:read"]])
    def test_list_and_check(self, client: TestClient, auth_token: auth.Token):
        listed = client.get("/warninglists/", headers=self._headers(auth_token)).json()
        assert {w["name"] for w in listed} == {
            content["name"] for content in LISTS.values()
        }
        assert {w["name"]: w["entry_count"] for w in listed}["Test RFC1918"] == 2

        response = client.post(
            "/warninglists/check",
            json={"values": ["192.168.1.1", "evil.example.net", "mail.example.com"]},
            headers=self._headers(auth_token),
        )
        assert response.json() == {
            "hits": {
                "192.168.1.1": ["Test RFC1918"],
                "mail.example.com": ["Test top domains"],
            }
        }

    @pytest.mark.parametrize("scopes", [["attributes:read"]])
    def test_outputs_leave_warninglisted_out(
        self, client: TestClient, auth_token: auth.Token
    ):
        headers = self._headers(auth_token)
        everything = [RESOLVER, PRIVATE, TOP_DOMAIN, EVIL]

        rest = client.post(
            "/attributes/restSearch", json={"enforceWarninglist": 1}, headers=headers
        ).json()["response"]["Attribute"]
        assert [a["uuid"] for a in rest] == [EVIL]
        # MISP default: not enforced unless asked.
        rest_all = client.post(
            "/attributes/restSearch",
            json={"includeWarninglistHits": 1},
            headers=headers,
        ).json()["response"]["Attribute"]
        assert sorted(a["uuid"] for a in rest_all) == sorted(everything)
        assert {a["uuid"]: a.get("warninglist_hits") for a in rest_all}[RESOLVER] == [
            "Test public resolvers"
        ]

        exported = client.get(
            "/attributes/export", params={"format": "ndjson"}, headers=headers
        )
        assert [json.loads(line)["uuid"] for line in exported.text.splitlines()] == [
            EVIL
        ]
        exported_all = client.get(
            "/attributes/export",
            params={"format": "ndjson", "enforce_warninglist": False},
            headers=headers,
        )
        assert len(exported_all.text.splitlines()) == 4

        get_redis_client().delete(*[k for k in (lookup_repository.BUILT_AT_KEY,)])
        with patch.object(lookup_repository, "request_rebuild"):
            looked_up = client.post(
                "/lookup",
                json={"values": ["8.8.8.8", "evil.example.net"]},
                headers=headers,
            ).json()
            with_listed = client.post(
                "/lookup",
                json={"values": ["8.8.8.8"], "include_warninglisted": True},
                headers=headers,
            ).json()
        assert [m["value"] for m in looked_up["matches"]] == ["evil.example.net"]
        [match] = with_listed["matches"]
        assert match["attributes"][0]["warninglist_hits"] == ["Test public resolvers"]

    @pytest.mark.parametrize("scopes", [["warninglists:read", "warninglists:update"]])
    def test_disabling_a_list_clears_its_hits(
        self, client: TestClient, auth_token: auth.Token, db: Session
    ):
        listed = client.get("/warninglists/", headers=self._headers(auth_token)).json()
        resolvers = next(w for w in listed if w["name"] == "Test public resolvers")

        with patch.object(tasks.evaluate_all_warninglist_hits, "delay") as evaluate:
            response = client.patch(
                f"/warninglists/{resolvers['id']}",
                json={"enabled": False},
                headers=self._headers(auth_token),
            )
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["enabled"] is False
        evaluate.assert_called_once()

        warninglists_repository.evaluate_all(db)
        assert _hits(RESOLVER) == []
        assert _hits(PRIVATE) == ["Test RFC1918"]

    @pytest.mark.parametrize("scopes", [["warninglists:read"]])
    def test_update_scope_required(self, client: TestClient, auth_token: auth.Token):
        response = client.post(
            "/warninglists/update", headers=self._headers(auth_token)
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_recent_writes_are_flagged(self, db: Session):
        late = "abababab-0000-4000-8000-000000000005"
        client = get_opensearch_client()
        client.index(
            index="misp-attributes",
            id=late,
            body=_attribute(late, "ip-dst", "192.168.7.7"),
            refresh=True,
        )
        assert _hits(late) == []
        warninglists_repository.evaluate_recent(db)
        assert _hits(late) == ["Test RFC1918"]
