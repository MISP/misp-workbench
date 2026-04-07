from unittest.mock import MagicMock, patch

import pytest
from app.auth import auth
from app.tests.api_tester import ApiTester
from fastapi import status
from fastapi.testclient import TestClient

SAMPLE_MODULES_RESPONSE = [
    {
        "name": "virustotal",
        "type": "expansion",
        "mispattributes": {},
        "meta": {
            "version": "0.1",
            "author": "Alexandre Dulaunoy",
            "description": "Module to get information from VirusTotal.",
            "module-type": ["expansion", "hover"],
            "name": "VirusTotal",
            "logo": "",
        },
    },
    {
        "name": "csvimport",
        "type": "import_mod",
        "mispattributes": {},
        "meta": {
            "version": "0.2",
            "author": "Christian Studer",
            "description": "Module to import MISP attributes from a CSV file.",
            "module-type": ["import"],
            "name": "CSV import",
            "logo": "",
        },
    },
    {
        "name": "cef_export",
        "type": "export_mod",
        "mispattributes": {},
        "meta": {
            "version": "1",
            "author": "Hannah Ward",
            "description": "Module to export a MISP event to CEF format.",
            "module-type": ["export"],
            "name": "CEF export",
            "logo": "",
        },
    },
]


class TestDiagnosticsModules(ApiTester):
    @pytest.mark.parametrize("scopes", [["tasks:read"]])
    def test_get_modules_connected(self, client: TestClient, auth_token: auth.Token):
        with patch("app.routers.diagnostics.urllib.request.urlopen") as mock_urlopen:
            import io
            import json

            body = json.dumps(SAMPLE_MODULES_RESPONSE).encode()
            mock_response = io.BytesIO(body)
            mock_urlopen.return_value.__enter__ = lambda s: mock_response
            mock_urlopen.return_value.__exit__ = lambda s, *a: None

            response = client.get(
                "/diagnostics/modules",
                headers={"Authorization": "Bearer " + auth_token},
            )

        data = response.json()

        assert response.status_code == status.HTTP_200_OK
        assert data["connected"] is True
        assert data["total"] == 3
        assert data["counts"]["expansion"] == 1
        assert data["counts"]["import_mod"] == 1
        assert data["counts"]["export_mod"] == 1
        assert len(data["modules"]) == 3

        vt = next(m for m in data["modules"] if m["name"] == "virustotal")
        assert vt["type"] == "expansion"
        assert vt["meta_name"] == "VirusTotal"
        assert vt["version"] == "0.1"
        assert "expansion" in vt["module_type"]
        assert "hover" in vt["module_type"]

    @pytest.mark.parametrize("scopes", [["tasks:read"]])
    def test_get_modules_unreachable(self, client: TestClient, auth_token: auth.Token):
        with patch(
            "app.routers.diagnostics.urllib.request.urlopen",
            side_effect=ConnectionRefusedError("Connection refused"),
        ):
            response = client.get(
                "/diagnostics/modules",
                headers={"Authorization": "Bearer " + auth_token},
            )

        data = response.json()

        assert response.status_code == status.HTTP_200_OK
        assert data["connected"] is False
        assert "url" in data
        assert "error" in data

    @pytest.mark.parametrize("scopes", [[]])
    def test_get_modules_unauthorized(self, client: TestClient, auth_token: auth.Token):
        response = client.get(
            "/diagnostics/modules",
            headers={"Authorization": "Bearer " + auth_token},
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


# ── /health ───────────────────────────────────────────────────────────────────

PATCH_ENGINE = "app.routers.diagnostics.engine"
PATCH_OS = "app.routers.diagnostics.OpenSearchClient"
PATCH_REDIS = "app.routers.diagnostics.RedisClient"
PATCH_URLOPEN = "app.routers.diagnostics.urllib.request.urlopen"
PATCH_ISDIR = "app.routers.diagnostics.os.path.isdir"
PATCH_CELERY = "app.worker.tasks.celery_app"


def _all_ok_patches():
    """Return a dict of patch kwargs that make every service appear healthy."""
    mock_engine = MagicMock()
    mock_engine.connect.return_value.__enter__ = lambda s: MagicMock()
    mock_engine.connect.return_value.__exit__ = MagicMock(return_value=False)

    mock_celery_app = MagicMock()
    mock_celery_app.control.inspect.return_value.active.return_value = {"worker@host": []}

    return {
        PATCH_ENGINE: mock_engine,
        PATCH_ISDIR: MagicMock(return_value=True),
        PATCH_CELERY: mock_celery_app,
    }


class TestHealth(ApiTester):
    def test_liveness_returns_ok_without_auth(self, client):
        """Basic probe returns instantly with no service calls and no auth."""
        response = client.get("/health")

        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {"status": "ok"}

    def test_liveness_does_not_require_auth(self, client):
        """Endpoint must be accessible without an Authorization header."""
        response = client.get("/health")

        assert response.status_code != status.HTTP_401_UNAUTHORIZED
        assert response.status_code != status.HTTP_403_FORBIDDEN

    def test_full_check_healthy(self, client):
        """All services reachable → 200 + status healthy + all checks ok."""
        patches = _all_ok_patches()
        with (
            patch(PATCH_ENGINE, patches[PATCH_ENGINE]),
            patch(PATCH_OS),
            patch(PATCH_REDIS),
            patch(PATCH_URLOPEN),
            patch(PATCH_ISDIR, patches[PATCH_ISDIR]),
            patch(PATCH_CELERY, patches[PATCH_CELERY]),
        ):
            response = client.get("/health?full=true")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "ok"
        assert all(v == "ok" for v in data["checks"].values())

    def test_full_check_includes_all_services(self, client):
        """Response must contain a key for every monitored service."""
        patches = _all_ok_patches()
        with (
            patch(PATCH_ENGINE, patches[PATCH_ENGINE]),
            patch(PATCH_OS),
            patch(PATCH_REDIS),
            patch(PATCH_URLOPEN),
            patch(PATCH_ISDIR, patches[PATCH_ISDIR]),
            patch(PATCH_CELERY, patches[PATCH_CELERY]),
        ):
            response = client.get("/health?full=true")

        assert set(response.json()["checks"].keys()) == {
            "postgres", "opensearch", "redis", "modules", "storage", "workers",
        }

    def test_full_check_degraded_when_service_down(self, client):
        """Any failing service → 503 + status degraded."""
        patches = _all_ok_patches()
        with (
            patch(PATCH_ENGINE, patches[PATCH_ENGINE]),
            patch(PATCH_OS),
            patch(PATCH_REDIS + ".ping", side_effect=Exception("connection refused")),
            patch(PATCH_URLOPEN),
            patch(PATCH_ISDIR, patches[PATCH_ISDIR]),
            patch(PATCH_CELERY, patches[PATCH_CELERY]),
        ):
            response = client.get("/health?full=true")

        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        data = response.json()
        assert data["status"] == "degraded"
        assert data["checks"]["redis"] == "error"

    def test_full_check_still_runs_all_checks_on_partial_failure(self, client):
        """A failure in one service must not short-circuit the remaining checks."""
        patches = _all_ok_patches()
        with (
            patch(PATCH_ENGINE, patches[PATCH_ENGINE]),
            patch(PATCH_OS + ".cluster.health", side_effect=Exception("opensearch down")),
            patch(PATCH_REDIS),
            patch(PATCH_URLOPEN),
            patch(PATCH_ISDIR, patches[PATCH_ISDIR]),
            patch(PATCH_CELERY, patches[PATCH_CELERY]),
        ):
            response = client.get("/health?full=true")

        checks = response.json()["checks"]
        assert checks["opensearch"] == "error"
        # All other keys must still be present
        assert {"postgres", "redis", "modules", "storage", "workers"}.issubset(checks.keys())

    def test_full_check_no_workers_is_degraded(self, client):
        """inspect().active() returning None means no workers → error."""
        patches = _all_ok_patches()
        mock_celery_app = MagicMock()
        mock_celery_app.control.inspect.return_value.active.return_value = None

        with (
            patch(PATCH_ENGINE, patches[PATCH_ENGINE]),
            patch(PATCH_OS),
            patch(PATCH_REDIS),
            patch(PATCH_URLOPEN),
            patch(PATCH_ISDIR, patches[PATCH_ISDIR]),
            patch(PATCH_CELERY, mock_celery_app),
        ):
            response = client.get("/health?full=true")

        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        assert response.json()["checks"]["workers"] == "error"

    def test_full_check_modules_unreachable_is_degraded(self, client):
        """Modules service timing out → error."""
        patches = _all_ok_patches()
        with (
            patch(PATCH_ENGINE, patches[PATCH_ENGINE]),
            patch(PATCH_OS),
            patch(PATCH_REDIS),
            patch(PATCH_URLOPEN, side_effect=ConnectionRefusedError("refused")),
            patch(PATCH_ISDIR, patches[PATCH_ISDIR]),
            patch(PATCH_CELERY, patches[PATCH_CELERY]),
        ):
            response = client.get("/health?full=true")

        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        assert response.json()["checks"]["modules"] == "error"

    def test_full_check_local_storage_missing_is_degraded(self, client):
        """/tmp/attachments not found → storage error."""
        patches = _all_ok_patches()
        with (
            patch(PATCH_ENGINE, patches[PATCH_ENGINE]),
            patch(PATCH_OS),
            patch(PATCH_REDIS),
            patch(PATCH_URLOPEN),
            patch(PATCH_ISDIR, MagicMock(return_value=False)),
            patch(PATCH_CELERY, patches[PATCH_CELERY]),
        ):
            response = client.get("/health?full=true")

        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        assert response.json()["checks"]["storage"] == "error"
