from unittest.mock import patch

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.auth import auth
from app.models import export as export_models
from app.services.exports import converters
from app.tests.api_tester import ApiTester


class TestExportsResource(ApiTester):
    # ── GET /exports/ ─────────────────────────────────────────────────────────

    @pytest.mark.parametrize("scopes", [["exports:read"]])
    def test_get_exports(
        self,
        client: TestClient,
        export_1: export_models.Export,
        auth_token: auth.Token,
    ):
        response = client.get(
            "/exports/", headers={"Authorization": "Bearer " + auth_token}
        )
        data = response.json()

        assert response.status_code == status.HTTP_200_OK
        assert len(data["items"]) == 1
        assert data["items"][0]["id"] == export_1.id
        assert data["items"][0]["name"] == export_1.name
        assert data["items"][0]["format"] == export_1.format
        assert data["items"][0]["status"] == export_1.status

    @pytest.mark.parametrize("scopes", [[]])
    def test_get_exports_unauthorized(self, client: TestClient, auth_token: auth.Token):
        response = client.get(
            "/exports/", headers={"Authorization": "Bearer " + auth_token}
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.parametrize("scopes", [["exports:read"]])
    def test_get_exports_filter_no_match(
        self,
        client: TestClient,
        export_1: export_models.Export,
        auth_token: auth.Token,
    ):
        response = client.get(
            "/exports/",
            params={"filter": "nonexistent_export_xyz"},
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert response.status_code == status.HTTP_200_OK
        assert len(response.json()["items"]) == 0

    # ── POST /exports/ ────────────────────────────────────────────────────────

    @pytest.mark.parametrize("scopes", [["exports:create"]])
    def test_create_export_enqueues_task(
        self,
        client: TestClient,
        auth_token: auth.Token,
        db: Session,
    ):
        class _FakeResult:
            id = "fake-task-id"

        with patch(
            "app.worker.tasks.run_export.delay", return_value=_FakeResult()
        ) as mock_delay:
            response = client.post(
                "/exports/",
                json={
                    "name": "IP export",
                    "query": "type:ip-dst",
                    "index_target": "attributes",
                    "format": "csv",
                },
                headers={"Authorization": "Bearer " + auth_token},
            )

        data = response.json()
        assert response.status_code == status.HTTP_201_CREATED
        assert data["name"] == "IP export"
        assert data["format"] == "csv"
        assert data["status"] == "queued"
        assert data["celery_task_id"] == "fake-task-id"
        mock_delay.assert_called_once_with(data["id"])

    @pytest.mark.parametrize("scopes", [["exports:create"]])
    def test_create_export_invalid_format(
        self, client: TestClient, auth_token: auth.Token
    ):
        response = client.post(
            "/exports/",
            json={"name": "Bad", "query": "x", "format": "pdf"},
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.parametrize("scopes", [[]])
    def test_create_export_unauthorized(
        self, client: TestClient, auth_token: auth.Token
    ):
        response = client.post(
            "/exports/",
            json={"name": "x", "query": "y"},
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    # ── GET /exports/{id} ─────────────────────────────────────────────────────

    @pytest.mark.parametrize("scopes", [["exports:read"]])
    def test_get_export_by_id(
        self,
        client: TestClient,
        export_1: export_models.Export,
        auth_token: auth.Token,
    ):
        response = client.get(
            f"/exports/{export_1.id}",
            headers={"Authorization": "Bearer " + auth_token},
        )
        data = response.json()
        assert response.status_code == status.HTTP_200_OK
        assert data["id"] == export_1.id
        assert data["record_count"] == export_1.record_count

    @pytest.mark.parametrize("scopes", [["exports:read"]])
    def test_get_export_by_id_not_found(
        self, client: TestClient, auth_token: auth.Token
    ):
        response = client.get(
            "/exports/999999", headers={"Authorization": "Bearer " + auth_token}
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    # ── GET /exports/{id}/download ────────────────────────────────────────────

    @pytest.mark.parametrize("scopes", [["exports:read"]])
    def test_download_export(
        self,
        client: TestClient,
        export_1: export_models.Export,
        auth_token: auth.Token,
    ):
        with patch(
            "app.routers.exports.get_export", return_value=b'[{"value": "1.2.3.4"}]'
        ) as mock_get:
            response = client.get(
                f"/exports/{export_1.id}/download",
                headers={"Authorization": "Bearer " + auth_token},
            )

        assert response.status_code == status.HTTP_200_OK
        assert response.headers["content-type"].startswith("application/json")
        assert "attachment" in response.headers["content-disposition"]
        assert response.content == b'[{"value": "1.2.3.4"}]'
        mock_get.assert_called_once_with(export_1.storage_key)

    @pytest.mark.parametrize("scopes", [["exports:read"]])
    def test_download_export_not_ready(
        self,
        client: TestClient,
        auth_token: auth.Token,
        db: Session,
        api_tester_user,
    ):
        from datetime import datetime, timezone

        pending = export_models.Export(
            user_id=api_tester_user.id,
            name="Pending",
            query="type:ip-dst",
            index_target="attributes",
            format="json",
            status="running",
            created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
        )
        db.add(pending)
        db.commit()
        db.refresh(pending)
        try:
            response = client.get(
                f"/exports/{pending.id}/download",
                headers={"Authorization": "Bearer " + auth_token},
            )
            assert response.status_code == status.HTTP_409_CONFLICT
        finally:
            db.delete(pending)
            db.commit()

    # ── DELETE /exports/{id} ──────────────────────────────────────────────────

    @pytest.mark.parametrize("scopes", [["exports:delete"]])
    def test_delete_export(
        self,
        client: TestClient,
        auth_token: auth.Token,
        db: Session,
        api_tester_user,
    ):
        from datetime import datetime, timezone

        export = export_models.Export(
            user_id=api_tester_user.id,
            name="To delete",
            query="type:ip-dst",
            index_target="attributes",
            format="json",
            status="completed",
            storage_key="exports/export-del.json",
            created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
        )
        db.add(export)
        db.commit()
        db.refresh(export)
        export_id = export.id

        with patch("app.repositories.exports.delete_export_artifact") as mock_del:
            response = client.delete(
                f"/exports/{export_id}",
                headers={"Authorization": "Bearer " + auth_token},
            )

        assert response.status_code == status.HTTP_204_NO_CONTENT
        mock_del.assert_called_once_with("exports/export-del.json")
        assert (
            db.query(export_models.Export)
            .filter(export_models.Export.id == export_id)
            .first()
            is None
        )

    @pytest.mark.parametrize("scopes", [["exports:delete"]])
    def test_delete_export_not_found(self, client: TestClient, auth_token: auth.Token):
        response = client.delete(
            "/exports/999999", headers={"Authorization": "Bearer " + auth_token}
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    # ── run_export repository logic ───────────────────────────────────────────

    def test_run_export_completes_and_stores(
        self,
        db: Session,
        api_tester_user,
    ):
        from datetime import datetime, timezone

        from app.repositories import exports as exports_repository

        export = export_models.Export(
            user_id=api_tester_user.id,
            name="Run me",
            query="type:ip-dst",
            index_target="attributes",
            format="json",
            status="queued",
            created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
        )
        db.add(export)
        db.commit()
        db.refresh(export)

        hits = [
            {"uuid": "u1", "type": "ip-dst", "value": "1.2.3.4"},
            {"uuid": "u2", "type": "ip-dst", "value": "5.6.7.8"},
        ]
        try:
            with patch(
                "app.repositories.exports._fetch_hits", return_value=hits
            ), patch(
                "app.repositories.exports.store_export",
                return_value="exports/export-run.json",
            ) as mock_store:
                exports_repository.run_export(db, export.id)

            db.refresh(export)
            assert export.status == "completed"
            assert export.record_count == 2
            assert export.storage_key == "exports/export-run.json"
            assert export.file_size > 0
            assert export.last_run_at is not None
            mock_store.assert_called_once()
        finally:
            db.delete(export)
            db.commit()

    def test_run_export_records_failure(
        self,
        db: Session,
        api_tester_user,
    ):
        from datetime import datetime, timezone

        from app.repositories import exports as exports_repository

        export = export_models.Export(
            user_id=api_tester_user.id,
            name="Fail me",
            query="type:ip-dst",
            index_target="attributes",
            format="json",
            status="queued",
            created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
        )
        db.add(export)
        db.commit()
        db.refresh(export)

        try:
            with patch(
                "app.repositories.exports._fetch_hits",
                side_effect=RuntimeError("opensearch down"),
            ):
                exports_repository.run_export(db, export.id)

            db.refresh(export)
            assert export.status == "failed"
            assert "opensearch down" in export.error
        finally:
            db.delete(export)
            db.commit()

    # ── scheduling ────────────────────────────────────────────────────────────

    @pytest.mark.parametrize("scopes", [["exports:create"]])
    def test_create_export_with_schedule_registers_entry(
        self,
        client: TestClient,
        auth_token: auth.Token,
    ):
        class _FakeResult:
            id = "fake-task-id"

        with patch(
            "app.worker.tasks.run_export.delay", return_value=_FakeResult()
        ), patch(
            "app.repositories.exports._register_export_schedule",
            return_value="sched-uuid",
        ) as mock_register:
            response = client.post(
                "/exports/",
                json={
                    "name": "Daily IPs",
                    "query": "type:ip-dst",
                    "format": "json",
                    "schedule": {"type": "crontab", "minute": "0", "hour": "2"},
                    "schedule_enabled": True,
                },
                headers={"Authorization": "Bearer " + auth_token},
            )

        data = response.json()
        assert response.status_code == status.HTTP_201_CREATED
        assert data["schedule"]["hour"] == "2"
        assert data["schedule_enabled"] is True
        assert data["scheduled_task_name"] == "sched-uuid"
        mock_register.assert_called_once()

    @pytest.mark.parametrize("scopes", [["exports:create"]])
    def test_update_schedule_toggle_and_clear(
        self,
        client: TestClient,
        auth_token: auth.Token,
        db: Session,
        api_tester_user,
    ):
        from datetime import datetime, timezone

        export = export_models.Export(
            user_id=api_tester_user.id,
            name="Sched",
            query="type:ip-dst",
            index_target="attributes",
            format="json",
            status="completed",
            schedule={"type": "crontab", "minute": "0", "hour": "*"},
            scheduled_task_name="existing-uuid",
            schedule_enabled=True,
            created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
        )
        db.add(export)
        db.commit()
        db.refresh(export)

        # pause
        with patch(
            "app.repositories.exports._register_export_schedule",
            return_value="existing-uuid",
        ) as mock_register:
            response = client.patch(
                f"/exports/{export.id}/schedule",
                json={"schedule_enabled": False},
                headers={"Authorization": "Bearer " + auth_token},
            )
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["schedule_enabled"] is False
        mock_register.assert_called_once()

        # clear / unschedule
        with patch(
            "app.repositories.exports._unregister_export_schedule"
        ) as mock_unregister:
            response = client.patch(
                f"/exports/{export.id}/schedule",
                json={"schedule": None},
                headers={"Authorization": "Bearer " + auth_token},
            )
        data = response.json()
        assert response.status_code == status.HTTP_200_OK
        assert data["schedule"] is None
        assert data["scheduled_task_name"] is None
        assert data["schedule_enabled"] is False
        mock_unregister.assert_called_once_with("existing-uuid")

    @pytest.mark.parametrize("scopes", [["exports:delete"]])
    def test_delete_scheduled_export_unregisters(
        self,
        client: TestClient,
        auth_token: auth.Token,
        db: Session,
        api_tester_user,
    ):
        from datetime import datetime, timezone

        export = export_models.Export(
            user_id=api_tester_user.id,
            name="Sched delete",
            query="type:ip-dst",
            index_target="attributes",
            format="json",
            status="completed",
            scheduled_task_name="del-uuid",
            schedule={"type": "crontab", "minute": "0", "hour": "*"},
            schedule_enabled=True,
            created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
        )
        db.add(export)
        db.commit()
        db.refresh(export)

        with patch(
            "app.repositories.exports._unregister_export_schedule"
        ) as mock_unregister, patch(
            "app.repositories.exports.delete_export_artifact"
        ):
            response = client.delete(
                f"/exports/{export.id}",
                headers={"Authorization": "Bearer " + auth_token},
            )

        assert response.status_code == status.HTTP_204_NO_CONTENT
        mock_unregister.assert_called_once_with("del-uuid")


class TestExportConverters:
    SAMPLE_ATTRIBUTES = [
        {
            "uuid": "11111111-1111-4111-8111-111111111111",
            "event_uuid": "22222222-2222-4222-8222-222222222222",
            "type": "ip-dst",
            "value": "1.2.3.4",
            "category": "Network activity",
            "to_ids": True,
            "comment": "bad ip",
            "timestamp": 1700000000,
            "tags": [{"name": "tlp:white"}],
        },
        {
            "uuid": "33333333-3333-4333-8333-333333333333",
            "event_uuid": "22222222-2222-4222-8222-222222222222",
            "type": "domain",
            "value": "evil.com",
            "category": "Network activity",
            "to_ids": True,
            "timestamp": 1700000001,
            "tags": [],
        },
    ]

    def test_to_json(self):
        import json

        data, ext, ct = converters.convert("json", self.SAMPLE_ATTRIBUTES, "attributes")
        assert ext == "json"
        assert ct == "application/json"
        assert len(json.loads(data)) == 2

    def test_to_csv(self):
        data, ext, ct = converters.convert("csv", self.SAMPLE_ATTRIBUTES, "attributes")
        assert ext == "csv"
        assert ct == "text/csv"
        lines = data.decode().splitlines()
        assert lines[0].startswith("uuid,event_uuid")
        assert "1.2.3.4" in lines[1]
        assert "tlp:white" in lines[1]

    def test_to_stix21(self):
        import json

        data, ext, ct = converters.convert("stix", self.SAMPLE_ATTRIBUTES, "attributes")
        assert ext == "json"
        assert ct == "application/stix+json"
        bundle = json.loads(data)
        assert bundle["type"] == "bundle"
        object_types = {o["type"] for o in bundle["objects"]}
        assert "indicator" in object_types

    def test_stix_record_cap(self):
        oversized = [
            dict(self.SAMPLE_ATTRIBUTES[0], uuid=f"{i:032x}")
            for i in range(converters.MAX_STIX_RECORDS + 1)
        ]
        with pytest.raises(ValueError, match="STIX export is limited"):
            converters.convert("stix", oversized, "attributes")

    def test_unsupported_format(self):
        with pytest.raises(ValueError):
            converters.convert("pdf", self.SAMPLE_ATTRIBUTES, "attributes")
