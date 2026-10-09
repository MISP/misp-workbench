import json
import os
import time
from datetime import datetime, timezone

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.auth import auth
from app.models import export as export_models
from app.repositories import exports as exports_repository
from app.repositories import runtime_settings as runtime_settings_repository
from app.services import exports_storage
from app.services.opensearch import get_opensearch_client
from app.tests.api_tester import ApiTester

EVENT = "66666666-6666-4666-8666-666666666666"
IP_1 = "cccccccc-0000-4000-8000-000000000001"
IP_2 = "cccccccc-0000-4000-8000-000000000002"
IP_V6 = "cccccccc-0000-4000-8000-000000000003"
DOMAIN = "cccccccc-0000-4000-8000-000000000004"
IP_NEW = "cccccccc-0000-4000-8000-000000000005"


def _attribute(uuid, type_, value):
    return {
        "uuid": uuid,
        "event_uuid": EVENT,
        "type": type_,
        "category": "Network activity",
        "value": value,
        "to_ids": True,
        "timestamp": 1700000000,
        "comment": "",
        "deleted": False,
        "tags": [],
    }


def _index(*docs):
    client = get_opensearch_client()
    for doc in docs:
        client.index(index="misp-attributes", id=doc["uuid"], body=doc)
    client.indices.refresh(index="misp-attributes")


def _update(uuid, doc):
    client = get_opensearch_client()
    client.update(index="misp-attributes", id=uuid, body={"doc": doc})
    client.indices.refresh(index="misp-attributes")


def _past_this_second():
    """Writes stamped from here on sort strictly after any cursor taken before.

    Cursors are whole seconds and deltas include their lower bound, so step
    into the next second before writing what a delta should (or shouldn't) hold.
    """
    time.sleep(1.1)


def _ndjson(response):
    return {d["uuid"]: d for d in map(json.loads, response.text.splitlines())}


class TestExportFeeds(ApiTester):
    @pytest.fixture(scope="class", autouse=True)
    def dataset(self, cleanup):
        _index(
            _attribute(IP_1, "ip-dst", "198.51.100.1"),
            _attribute(IP_2, "ip-dst", "198.51.100.2"),
            _attribute(IP_V6, "ip-dst", "2001:db8::7"),
            _attribute(DOMAIN, "domain", "feed.example.com"),
        )
        _past_this_second()
        yield

    def _export(self, db: Session, user, **fields) -> export_models.Export:
        db_export = export_models.Export(
            user_id=user.id,
            name=fields.pop("name", "feed"),
            query=fields.pop("query", "type:ip-dst"),
            index_target="attributes",
            status="queued",
            created_at=datetime.now(timezone.utc),
            **fields,
        )
        db.add(db_export)
        db.commit()
        db.refresh(db_export)
        return db_export

    def _run(self, db: Session, db_export):
        exports_repository.run_export(db, db_export.id)
        db.refresh(db_export)
        assert db_export.status == "completed", db_export.error
        return db_export

    def _feed(self, client, token, export_id, headers=None, **params):
        return client.get(
            f"/exports/{export_id}/feed",
            params=params,
            headers={"Authorization": "Bearer " + token, **(headers or {})},
        )

    @pytest.mark.parametrize("scopes", [["exports:read"]])
    def test_streamed_line_formats(
        self, client: TestClient, auth_token: auth.Token, db: Session, api_tester_user
    ):
        cdb = self._run(db, self._export(db, api_tester_user, format="cdb"))
        assert cdb.record_count == 3
        assert len(cdb.checksum) == 64
        response = client.get(
            f"/exports/{cdb.id}/download",
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert response.status_code == status.HTTP_200_OK
        assert sorted(response.text.splitlines()) == [
            '"2001:db8::7":ip-dst',
            "198.51.100.1:ip-dst",
            "198.51.100.2:ip-dst",
        ]

        # The stored artifact's checksum is its ETag.
        etag = response.headers["etag"]
        assert etag == f'"{cdb.checksum}"'
        again = client.get(
            f"/exports/{cdb.id}/download",
            headers={"Authorization": "Bearer " + auth_token, "If-None-Match": etag},
        )
        assert again.status_code == status.HTTP_304_NOT_MODIFIED

        # A feed endpoint only exists for incremental exports.
        assert (
            self._feed(client, auth_token, cdb.id).status_code
            == status.HTTP_409_CONFLICT
        )

    @pytest.mark.parametrize("scopes", [["exports:read"]])
    def test_incremental_feed(
        self, client: TestClient, auth_token: auth.Token, db: Session, api_tester_user
    ):
        feed = self._export(db, api_tester_user, format="ndjson", incremental=True)
        assert (
            self._feed(client, auth_token, feed.id).status_code
            == status.HTTP_409_CONFLICT
        )

        # First run: the full artifact is the base, no delta yet.
        feed = self._run(db, feed)
        full = self._feed(client, auth_token, feed.id)
        assert full.status_code == status.HTTP_200_OK
        assert full.headers["x-feed-type"] == "full"
        assert sorted(_ndjson(full)) == sorted([IP_1, IP_2, IP_V6])
        cursor_1 = int(full.headers["x-feed-cursor"])
        assert cursor_1 == feed.cursor

        assert (
            self._feed(client, auth_token, feed.id, since=cursor_1).status_code
            == status.HTTP_304_NOT_MODIFIED
        )
        assert (
            self._feed(
                client,
                auth_token,
                feed.id,
                headers={"If-None-Match": full.headers["etag"]},
            ).status_code
            == status.HTTP_304_NOT_MODIFIED
        )

        # Changes: an edit, a soft delete, a new indicator, and one outside the query.
        _past_this_second()
        _update(IP_1, {"comment": "edited"})
        _update(IP_2, {"deleted": True})
        _index(_attribute(IP_NEW, "ip-dst", "198.51.100.9"))
        _update(DOMAIN, {"comment": "not in this feed"})

        feed = self._run(db, feed)
        delta = self._feed(client, auth_token, feed.id, since=cursor_1)
        assert delta.status_code == status.HTTP_200_OK
        assert delta.headers["x-feed-type"] == "delta"
        docs = _ndjson(delta)
        assert sorted(docs) == sorted([IP_1, IP_2, IP_NEW])
        assert docs[IP_1]["comment"] == "edited"
        assert docs[IP_2]["deleted"] is True
        cursor_2 = int(delta.headers["x-feed-cursor"])
        assert cursor_2 > cursor_1

        # The full artifact moved on too: the deleted one is gone.
        full = self._feed(client, auth_token, feed.id)
        assert sorted(_ndjson(full)) == sorted([IP_1, IP_V6, IP_NEW])
        assert (
            self._feed(client, auth_token, feed.id, since=cursor_2).status_code
            == status.HTTP_304_NOT_MODIFIED
        )

        # Two more runs with one delta retained: cursor_1 is now out of reach.
        runtime_settings_repository.set_setting(db, "exports", {"delta_retention": 1})
        try:
            _past_this_second()
            _update(IP_V6, {"comment": "third run"})
            feed = self._run(db, feed)
            _past_this_second()
            _update(IP_NEW, {"comment": "fourth run"})
            feed = self._run(db, feed)
        finally:
            runtime_settings_repository.delete_setting(db, "exports")

        deltas = (
            db.query(export_models.ExportDelta)
            .filter(export_models.ExportDelta.export_id == feed.id)
            .all()
        )
        assert [d.seq for d in deltas] == [3]
        gone = self._feed(client, auth_token, feed.id, since=cursor_1)
        assert gone.status_code == status.HTTP_410_GONE
        assert gone.headers["x-feed-cursor"] == str(feed.cursor)

        # Deleting the export removes its delta artifacts with it.
        delta_path = exports_storage._local_path(deltas[0].storage_key)
        assert os.path.exists(delta_path)
        exports_repository.delete_export(db, feed.id, api_tester_user.id)
        assert not os.path.exists(delta_path)

    @pytest.mark.parametrize("scopes", [["exports:create"]])
    def test_create_validation(self, client: TestClient, auth_token: auth.Token):
        def create(**fields):
            return client.post(
                "/exports/",
                json={"name": "x", "query": "*", **fields},
                headers={"Authorization": "Bearer " + auth_token},
            )

        # Deltas need a format that can carry deletions.
        assert create(format="csv", incremental=True).status_code == 422
        # Line formats hold attribute values.
        assert create(format="cdb", index_target="events").status_code == 422
        # updated_at only exists on attributes.
        assert (
            create(format="ndjson", index_target="events", incremental=True).status_code
            == 422
        )
