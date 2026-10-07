import csv
import io
import json
import time

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from app.auth import auth
from app.repositories import stream_exports as stream_exports_repository
from app.services.opensearch import get_opensearch_client
from app.tests.api_tester import ApiTester

EVENT_A = "44444444-4444-4444-8444-444444444444"
EVENT_DELETED = "55555555-5555-4555-8555-555555555555"

ATTR_IP = "bbbbbbbb-0000-4000-8000-000000000001"
ATTR_IPV6 = "bbbbbbbb-0000-4000-8000-000000000002"
ATTR_TEXT = "bbbbbbbb-0000-4000-8000-000000000003"
ATTR_EDITED = "bbbbbbbb-0000-4000-8000-000000000004"
ATTR_TO_DELETE = "bbbbbbbb-0000-4000-8000-000000000005"
ATTR_ALREADY_DELETED = "bbbbbbbb-0000-4000-8000-000000000006"

LIVE_BEFORE_DELTA = sorted([ATTR_IP, ATTR_IPV6, ATTR_TEXT, ATTR_EDITED, ATTR_TO_DELETE])


def _attribute(uuid, type_, value, deleted=False):
    return {
        "uuid": uuid,
        "event_uuid": EVENT_A,
        "type": type_,
        "category": "Network activity",
        "value": value,
        "to_ids": True,
        "timestamp": 1700000000,
        "comment": "",
        "deleted": deleted,
        "tags": [{"name": "tlp:green"}],
    }


class TestStreamExports(ApiTester):
    @pytest.fixture(scope="class", autouse=True)
    def dataset(self, cleanup):
        client = get_opensearch_client()
        for doc in (
            _attribute(ATTR_IP, "ip-dst", "198.51.100.7"),
            _attribute(ATTR_IPV6, "ip-dst", "2001:db8::1"),
            _attribute(ATTR_TEXT, "text", "line one\nline two"),
            _attribute(ATTR_EDITED, "domain", "edited.example.com"),
            _attribute(ATTR_TO_DELETE, "domain", "gone.example.com"),
            _attribute(ATTR_ALREADY_DELETED, "domain", "old.example.com", deleted=True),
        ):
            client.index(index="misp-attributes", id=doc["uuid"], body=doc)
        for uuid, info, deleted in (
            (EVENT_A, "event a", False),
            (EVENT_DELETED, "deleted event", True),
        ):
            client.index(
                index="misp-events",
                id=uuid,
                body={"uuid": uuid, "info": info, "deleted": deleted},
            )
        client.indices.refresh(index="misp-attributes")
        client.indices.refresh(index="misp-events")
        yield

    def _get(self, client, token, path="/attributes/export", headers=None, **params):
        return client.get(
            path,
            params=params,
            headers={"Authorization": "Bearer " + token, **(headers or {})},
        )

    @pytest.mark.parametrize("scopes", [["attributes:read"]])
    def test_json_excludes_deleted_by_default(
        self, client: TestClient, auth_token: auth.Token
    ):
        response = self._get(client, auth_token)
        assert response.status_code == status.HTTP_200_OK
        hits = response.json()
        assert sorted(h["_id"] for h in hits) == LIVE_BEFORE_DELTA
        assert all("_source" in h for h in hits)

        response = self._get(client, auth_token, include_deleted=True)
        assert len(response.json()) == 6

    @pytest.mark.parametrize("scopes", [["attributes:read"]])
    def test_ndjson(self, client: TestClient, auth_token: auth.Token):
        response = self._get(client, auth_token, format="ndjson", query="type:ip-dst")
        assert response.headers["content-type"].startswith("application/x-ndjson")
        docs = [json.loads(line) for line in response.text.splitlines()]
        assert sorted(d["uuid"] for d in docs) == [ATTR_IP, ATTR_IPV6]

    @pytest.mark.parametrize("scopes", [["attributes:read"]])
    def test_csv(self, client: TestClient, auth_token: auth.Token):
        response = self._get(client, auth_token, format="csv", query="type:domain")
        rows = list(csv.DictReader(io.StringIO(response.text)))
        assert list(rows[0].keys()) == stream_exports_repository.CSV_COLUMNS
        assert sorted(r["value"] for r in rows) == [
            "edited.example.com",
            "gone.example.com",
        ]
        assert rows[0]["to_ids"] == "1"
        assert rows[0]["deleted"] == "0"
        assert rows[0]["tags"] == "tlp:green"

    @pytest.mark.parametrize("scopes", [["attributes:read"]])
    def test_text_skips_multiline_values(
        self, client: TestClient, auth_token: auth.Token
    ):
        response = self._get(client, auth_token, format="text")
        assert sorted(response.text.splitlines()) == [
            "198.51.100.7",
            "2001:db8::1",
            "edited.example.com",
            "gone.example.com",
        ]

    @pytest.mark.parametrize("scopes", [["attributes:read"]])
    def test_cdb_quotes_keys_with_colons(
        self, client: TestClient, auth_token: auth.Token
    ):
        response = self._get(client, auth_token, format="cdb", query="type:ip-dst")
        assert sorted(response.text.splitlines()) == [
            '"2001:db8::1":ip-dst',
            "198.51.100.7:ip-dst",
        ]

    @pytest.mark.parametrize("scopes", [["attributes:read"]])
    def test_conditional_requests(self, client: TestClient, auth_token: auth.Token):
        first = self._get(client, auth_token, format="ndjson")
        etag = first.headers["etag"]
        assert first.headers["x-export-timestamp"].isdigit()

        again = self._get(
            client, auth_token, headers={"If-None-Match": etag}, format="ndjson"
        )
        assert again.status_code == status.HTTP_304_NOT_MODIFIED
        assert again.text == ""

        # The ETag is per request: another format or filter is another resource.
        other = self._get(
            client, auth_token, headers={"If-None-Match": etag}, format="csv"
        )
        assert other.status_code == status.HTTP_200_OK

        if "last-modified" in first.headers:
            since = self._get(
                client,
                auth_token,
                headers={"If-Modified-Since": first.headers["last-modified"]},
                format="ndjson",
            )
            assert since.status_code == status.HTTP_304_NOT_MODIFIED

    @pytest.mark.parametrize("scopes", [["attributes:read"]])
    def test_since_returns_changes_and_tombstones(
        self, client: TestClient, auth_token: auth.Token
    ):
        before = self._get(client, auth_token, format="ndjson")
        etag = before.headers["etag"]
        cutoff = int(before.headers["x-export-timestamp"]) + 1
        # updated_at is stamped by the ingest pipeline: step past the cutoff
        # second before writing.
        time.sleep(1.1)

        os_client = get_opensearch_client()
        os_client.update(
            index="misp-attributes",
            id=ATTR_EDITED,
            body={"doc": {"to_ids": False}},
            refresh=True,
        )
        os_client.update(
            index="misp-attributes",
            id=ATTR_TO_DELETE,
            body={"doc": {"deleted": True}},
            refresh=True,
        )

        delta = self._get(client, auth_token, format="ndjson", since=str(cutoff))
        assert delta.status_code == status.HTTP_200_OK
        docs = {d["uuid"]: d for d in map(json.loads, delta.text.splitlines())}
        assert sorted(docs) == sorted([ATTR_EDITED, ATTR_TO_DELETE])
        assert docs[ATTR_EDITED]["to_ids"] is False
        assert docs[ATTR_TO_DELETE]["deleted"] is True

        # Any write to a matching document changes the full export's ETag.
        after = self._get(
            client, auth_token, headers={"If-None-Match": etag}, format="ndjson"
        )
        assert after.status_code == status.HTTP_200_OK

    @pytest.mark.parametrize("scopes", [["attributes:read"]])
    def test_invalid_params(self, client: TestClient, auth_token: auth.Token):
        assert self._get(client, auth_token, format="xml").status_code == 400
        assert self._get(client, auth_token, since="yesterday").status_code == 400
        # text and cdb can't express a deletion, so can't carry a delta.
        assert (
            self._get(client, auth_token, format="text", since="1d").status_code == 400
        )
        assert (
            self._get(client, auth_token, format="cdb", since="1d").status_code == 400
        )

    @pytest.mark.parametrize("scopes", [["events:read"]])
    def test_events_export(self, client: TestClient, auth_token: auth.Token):
        response = self._get(client, auth_token, path="/events/export")
        assert [h["_id"] for h in response.json()] == [EVENT_A]

        response = self._get(
            client,
            auth_token,
            path="/events/export",
            format="ndjson",
            include_deleted=True,
        )
        assert sorted(
            json.loads(line)["uuid"] for line in response.text.splitlines()
        ) == [
            EVENT_A,
            EVENT_DELETED,
        ]
        assert (
            self._get(
                client, auth_token, path="/events/export", format="csv"
            ).status_code
            == 400
        )

    @pytest.mark.parametrize("scopes", [[]])
    def test_requires_scope(self, client: TestClient, auth_token: auth.Token):
        assert self._get(client, auth_token).status_code == status.HTTP_401_UNAUTHORIZED
        assert (
            self._get(client, auth_token, path="/events/export").status_code
            == status.HTTP_401_UNAUTHORIZED
        )

    def test_export_reads_a_consistent_snapshot(self, monkeypatch):
        # Small pages so the export spans several PIT searches.
        monkeypatch.setattr(stream_exports_repository, "PAGE_SIZE", 2)
        os_client = get_opensearch_client()

        export = stream_exports_repository.prepare_attribute_export(
            "", "ndjson", include_deleted=True
        )
        chunks = stream_exports_repository.stream(export)
        first = next(chunks)

        # Sorts after every seeded uuid, so without a snapshot a later page
        # would pick it up.
        late = "ffffffff-0000-4000-8000-000000000099"
        os_client.index(
            index="misp-attributes",
            id=late,
            body=_attribute(late, "domain", "late.example.com"),
            refresh=True,
        )
        try:
            body = first + "".join(chunks)
        finally:
            os_client.delete(index="misp-attributes", id=late, refresh=True)

        uuids = [json.loads(line)["uuid"] for line in body.splitlines()]
        assert late not in uuids
        assert len(uuids) == len(set(uuids)) == 6
        assert os_client.get_all_pits().get("pits", []) == []

    def test_abandoned_export_releases_its_snapshot(self, monkeypatch):
        monkeypatch.setattr(stream_exports_repository, "PAGE_SIZE", 2)
        os_client = get_opensearch_client()

        export = stream_exports_repository.prepare_attribute_export("", "ndjson")
        chunks = stream_exports_repository.stream(export)
        next(chunks)
        assert len(os_client.get_all_pits().get("pits", [])) == 1

        # What Starlette does when the client disconnects mid-stream.
        chunks.close()
        assert os_client.get_all_pits().get("pits", []) == []
