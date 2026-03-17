from unittest.mock import patch

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
