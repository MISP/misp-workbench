"""API tests for the Tech Lab — Reactor Scripts router."""

import os
import shutil
from unittest.mock import patch

import pytest
from app.auth import auth
from app.tests.api_tester import ApiTester
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session


SAMPLE_SOURCE = "def handle(ctx, payload):\n    ctx.log('hello', payload)\n"


@pytest.fixture(autouse=True)
def _local_storage(monkeypatch):
    # Force the local-storage path so script bodies land in /tmp/reactor.
    from app.settings import get_settings

    monkeypatch.setattr(get_settings().Storage, "engine", "local")
    base = "/tmp/reactor"
    yield
    if os.path.isdir(base):
        shutil.rmtree(base, ignore_errors=True)


class TestReactorRouter(ApiTester):
    # ── POST /tech-lab/reactor/scripts/ ──────────────────────────────────────

    @pytest.mark.parametrize("scopes", [["reactor:create"]])
    def test_create_script(self, client: TestClient, auth_token: auth.Token):
        response = client.post(
            "/tech-lab/reactor/scripts/",
            json={
                "name": "tag-ipsrc",
                "description": "Tag every new ip-src as tlp:amber",
                "entrypoint": "handle",
                "triggers": [
                    {
                        "resource_type": "attribute",
                        "action": "created",
                        "filters": {"type": "ip-src"},
                    }
                ],
                "status": "active",
                "timeout_seconds": 30,
                "max_writes": 50,
                "source": SAMPLE_SOURCE,
            },
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert response.status_code == status.HTTP_201_CREATED, response.text
        data = response.json()
        assert data["id"] is not None
        assert data["name"] == "tag-ipsrc"
        assert data["language"] == "python"
        assert len(data["source_sha256"]) == 64
        assert data["status"] == "active"

    @pytest.mark.parametrize("scopes", [[]])
    def test_create_script_unauthorized(
        self, client: TestClient, auth_token: auth.Token
    ):
        response = client.post(
            "/tech-lab/reactor/scripts/",
            json={"name": "x", "source": "x"},
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    # ── GET /tech-lab/reactor/scripts/ ───────────────────────────────────────

    @pytest.mark.parametrize("scopes", [["reactor:read", "reactor:create"]])
    def test_list_scripts(self, client: TestClient, auth_token: auth.Token):
        client.post(
            "/tech-lab/reactor/scripts/",
            json={"name": "foo", "source": SAMPLE_SOURCE, "triggers": []},
            headers={"Authorization": "Bearer " + auth_token},
        )
        response = client.get(
            "/tech-lab/reactor/scripts/",
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert any(item["name"] == "foo" for item in data["items"])

    # ── GET /tech-lab/reactor/scripts/{id}/source ────────────────────────────

    @pytest.mark.parametrize("scopes", [["reactor:read", "reactor:create"]])
    def test_get_script_source_returns_uploaded_body(
        self, client: TestClient, auth_token: auth.Token
    ):
        created = client.post(
            "/tech-lab/reactor/scripts/",
            json={"name": "src-test", "source": SAMPLE_SOURCE, "triggers": []},
            headers={"Authorization": "Bearer " + auth_token},
        ).json()

        response = client.get(
            f"/tech-lab/reactor/scripts/{created['id']}/source",
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["source"] == SAMPLE_SOURCE

    # ── PATCH /tech-lab/reactor/scripts/{id} ─────────────────────────────────

    @pytest.mark.parametrize(
        "scopes", [["reactor:read", "reactor:create", "reactor:update"]]
    )
    def test_update_script_replaces_source(
        self, client: TestClient, auth_token: auth.Token
    ):
        created = client.post(
            "/tech-lab/reactor/scripts/",
            json={"name": "u-test", "source": SAMPLE_SOURCE, "triggers": []},
            headers={"Authorization": "Bearer " + auth_token},
        ).json()
        old_sha = created["source_sha256"]

        response = client.patch(
            f"/tech-lab/reactor/scripts/{created['id']}",
            json={"source": "def handle(ctx, payload):\n    return 1\n"},
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["source_sha256"] != old_sha

    # ── DELETE /tech-lab/reactor/scripts/{id} ────────────────────────────────

    @pytest.mark.parametrize(
        "scopes", [["reactor:read", "reactor:create", "reactor:delete"]]
    )
    def test_delete_script(self, client: TestClient, auth_token: auth.Token):
        created = client.post(
            "/tech-lab/reactor/scripts/",
            json={"name": "to-delete", "source": SAMPLE_SOURCE, "triggers": []},
            headers={"Authorization": "Bearer " + auth_token},
        ).json()
        response = client.delete(
            f"/tech-lab/reactor/scripts/{created['id']}",
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert response.status_code == status.HTTP_204_NO_CONTENT

    # ── POST /tech-lab/reactor/scripts/{id}/test ─────────────────────────────

    @pytest.mark.parametrize(
        "scopes", [["reactor:create", "reactor:run", "reactor:read"]]
    )
    def test_test_run_executes_script_and_creates_run(
        self, client: TestClient, auth_token: auth.Token
    ):
        created = client.post(
            "/tech-lab/reactor/scripts/",
            json={
                "name": "test-run",
                "source": "def handle(ctx, payload):\n    ctx.log('payload was', payload)\n",
                "triggers": [],
            },
            headers={"Authorization": "Bearer " + auth_token},
        ).json()

        response = client.post(
            f"/tech-lab/reactor/scripts/{created['id']}/test",
            json={"payload": {"hello": "world"}},
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert response.status_code == status.HTTP_200_OK, response.text
        run = response.json()
        assert run["status"] == "success"

        log_response = client.get(
            f"/tech-lab/reactor/runs/{run['id']}/log",
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert log_response.status_code == status.HTTP_200_OK
        assert "payload was" in log_response.json()["log"]

    # ── trigger dispatch wiring ──────────────────────────────────────────────

    @pytest.mark.parametrize("scopes", [["reactor:create"]])
    def test_handle_created_attribute_calls_reactor_dispatch(
        self,
        client: TestClient,
        auth_token: auth.Token,
        db: Session,
    ):
        # Imports inside the test so the module is loaded with the dispatch
        # name we want to patch.
        from app.worker import tasks as worker_tasks

        with patch.object(worker_tasks.reactor_dispatch, "delay") as mock_delay:
            with patch.object(
                worker_tasks.attributes_repository,
                "get_attribute_from_opensearch",
                return_value=type(
                    "A", (), {"model_dump": lambda self, mode: {"type": "ip-src"}}
                )(),
            ):
                with patch.object(
                    worker_tasks.notifications_repository,
                    "create_attribute_notifications",
                    return_value=None,
                ):
                    worker_tasks.handle_created_attribute(
                        "11111111-1111-1111-1111-111111111111", None, None
                    )

        assert mock_delay.called
        args, _ = mock_delay.call_args
        assert args[0] == "attribute"
        assert args[1] == "created"
        assert args[2]["attribute_uuid"] == "11111111-1111-1111-1111-111111111111"
