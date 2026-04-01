from unittest.mock import patch

import pytest
from app.auth import auth
from app.models import hunt as hunt_models
from app.schemas import hunt as hunt_schemas
from app.tests.api_tester import ApiTester
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session


class TestHuntsResource(ApiTester):
    # ── GET /hunts/ ──────────────────────────────────────────────────────────

    @pytest.mark.parametrize("scopes", [["hunts:read"]])
    def test_get_hunts(
        self,
        client: TestClient,
        hunt_1: hunt_models.Hunt,
        auth_token: auth.Token,
    ):
        response = client.get(
            "/hunts/", headers={"Authorization": "Bearer " + auth_token}
        )
        data = response.json()

        assert response.status_code == status.HTTP_200_OK
        assert len(data["items"]) == 1
        assert data["items"][0]["id"] == hunt_1.id
        assert data["items"][0]["name"] == hunt_1.name
        assert data["items"][0]["query"] == hunt_1.query
        assert data["items"][0]["hunt_type"] == hunt_1.hunt_type
        assert data["items"][0]["index_target"] == hunt_1.index_target
        assert data["items"][0]["status"] == hunt_1.status

    @pytest.mark.parametrize("scopes", [[]])
    def test_get_hunts_unauthorized(
        self, client: TestClient, auth_token: auth.Token
    ):
        response = client.get(
            "/hunts/", headers={"Authorization": "Bearer " + auth_token}
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.parametrize("scopes", [["hunts:read"]])
    def test_get_hunts_filter_match(
        self,
        client: TestClient,
        hunt_1: hunt_models.Hunt,
        auth_token: auth.Token,
    ):
        response = client.get(
            "/hunts/",
            params={"filter": "Test"},
            headers={"Authorization": "Bearer " + auth_token},
        )
        data = response.json()

        assert response.status_code == status.HTTP_200_OK
        assert len(data["items"]) == 1
        assert data["items"][0]["id"] == hunt_1.id

    @pytest.mark.parametrize("scopes", [["hunts:read"]])
    def test_get_hunts_filter_no_match(
        self,
        client: TestClient,
        hunt_1: hunt_models.Hunt,
        auth_token: auth.Token,
    ):
        response = client.get(
            "/hunts/",
            params={"filter": "nonexistent_hunt_xyz"},
            headers={"Authorization": "Bearer " + auth_token},
        )
        data = response.json()

        assert response.status_code == status.HTTP_200_OK
        assert len(data["items"]) == 0

    # ── POST /hunts/ ─────────────────────────────────────────────────────────

    @pytest.mark.parametrize("scopes", [["hunts:create"]])
    def test_create_hunt(
        self,
        client: TestClient,
        auth_token: auth.Token,
    ):
        response = client.post(
            "/hunts/",
            json={
                "name": "New Hunt",
                "description": "Created in test",
                "query": "domain:evil.com",
                "hunt_type": "opensearch",
                "index_target": "attributes",
                "status": "active",
            },
            headers={"Authorization": "Bearer " + auth_token},
        )
        data = response.json()

        assert response.status_code == status.HTTP_201_CREATED
        assert data["id"] is not None
        assert data["name"] == "New Hunt"
        assert data["query"] == "domain:evil.com"
        assert data["hunt_type"] == "opensearch"
        assert data["index_target"] == "attributes"
        assert data["status"] == "active"

    @pytest.mark.parametrize("scopes", [[]])
    def test_create_hunt_unauthorized(
        self, client: TestClient, auth_token: auth.Token
    ):
        response = client.post(
            "/hunts/",
            json={
                "name": "New Hunt",
                "query": "domain:evil.com",
            },
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.parametrize("scopes", [["hunts:create"]])
    def test_create_hunt_incomplete(
        self, client: TestClient, auth_token: auth.Token
    ):
        response = client.post(
            "/hunts/",
            json={"name": "Missing query"},
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    # ── GET /hunts/{id} ──────────────────────────────────────────────────────

    @pytest.mark.parametrize("scopes", [["hunts:read"]])
    def test_get_hunt_by_id(
        self,
        client: TestClient,
        hunt_1: hunt_models.Hunt,
        auth_token: auth.Token,
    ):
        response = client.get(
            f"/hunts/{hunt_1.id}",
            headers={"Authorization": "Bearer " + auth_token},
        )
        data = response.json()

        assert response.status_code == status.HTTP_200_OK
        assert data["id"] == hunt_1.id
        assert data["name"] == hunt_1.name
        assert data["query"] == hunt_1.query

    @pytest.mark.parametrize("scopes", [["hunts:read"]])
    def test_get_hunt_by_id_not_found(
        self, client: TestClient, auth_token: auth.Token
    ):
        response = client.get(
            "/hunts/999999", headers={"Authorization": "Bearer " + auth_token}
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.parametrize("scopes", [[]])
    def test_get_hunt_by_id_unauthorized(
        self,
        client: TestClient,
        hunt_1: hunt_models.Hunt,
        auth_token: auth.Token,
    ):
        response = client.get(
            f"/hunts/{hunt_1.id}",
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    # ── PATCH /hunts/{id} ────────────────────────────────────────────────────

    @pytest.mark.parametrize("scopes", [["hunts:update"]])
    def test_update_hunt(
        self,
        client: TestClient,
        hunt_1: hunt_models.Hunt,
        auth_token: auth.Token,
    ):
        response = client.patch(
            f"/hunts/{hunt_1.id}",
            json={"name": "Updated Hunt", "status": "paused"},
            headers={"Authorization": "Bearer " + auth_token},
        )
        data = response.json()

        assert response.status_code == status.HTTP_200_OK
        assert data["id"] == hunt_1.id
        assert data["name"] == "Updated Hunt"
        assert data["status"] == "paused"

    @pytest.mark.parametrize("scopes", [["hunts:update"]])
    def test_update_hunt_not_found(
        self, client: TestClient, auth_token: auth.Token
    ):
        response = client.patch(
            "/hunts/999999",
            json={"name": "Updated"},
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.parametrize("scopes", [[]])
    def test_update_hunt_unauthorized(
        self,
        client: TestClient,
        hunt_1: hunt_models.Hunt,
        auth_token: auth.Token,
    ):
        response = client.patch(
            f"/hunts/{hunt_1.id}",
            json={"name": "Updated"},
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    # ── GET /hunts/{id}/results ──────────────────────────────────────────────

    @pytest.mark.parametrize("scopes", [["hunts:read"]])
    def test_get_hunt_results_no_results(
        self,
        client: TestClient,
        hunt_1: hunt_models.Hunt,
        auth_token: auth.Token,
    ):
        response = client.get(
            f"/hunts/{hunt_1.id}/results",
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.json()["detail"] == "No results available yet"

    @pytest.mark.parametrize("scopes", [["hunts:read"]])
    def test_get_hunt_results_hunt_not_found(
        self, client: TestClient, auth_token: auth.Token
    ):
        response = client.get(
            "/hunts/999999/results",
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.parametrize("scopes", [[]])
    def test_get_hunt_results_unauthorized(
        self,
        client: TestClient,
        hunt_1: hunt_models.Hunt,
        auth_token: auth.Token,
    ):
        response = client.get(
            f"/hunts/{hunt_1.id}/results",
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    # ── GET /hunts/{id}/history ──────────────────────────────────────────────

    @pytest.mark.parametrize("scopes", [["hunts:read"]])
    def test_get_hunt_history(
        self,
        client: TestClient,
        hunt_1: hunt_models.Hunt,
        hunt_run_history_1: hunt_models.HuntRunHistory,
        auth_token: auth.Token,
    ):
        response = client.get(
            f"/hunts/{hunt_1.id}/history",
            headers={"Authorization": "Bearer " + auth_token},
        )
        data = response.json()

        assert response.status_code == status.HTTP_200_OK
        assert len(data) == 1
        assert data[0]["match_count"] == hunt_run_history_1.match_count

    @pytest.mark.parametrize("scopes", [["hunts:read"]])
    def test_get_hunt_history_hunt_not_found(
        self, client: TestClient, auth_token: auth.Token
    ):
        response = client.get(
            "/hunts/999999/history",
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.parametrize("scopes", [[]])
    def test_get_hunt_history_unauthorized(
        self,
        client: TestClient,
        hunt_1: hunt_models.Hunt,
        auth_token: auth.Token,
    ):
        response = client.get(
            f"/hunts/{hunt_1.id}/history",
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    # ── POST /hunts/{id}/run ─────────────────────────────────────────────────

    @pytest.mark.parametrize("scopes", [["hunts:run"]])
    def test_run_hunt(
        self,
        client: TestClient,
        hunt_1: hunt_models.Hunt,
        auth_token: auth.Token,
    ):
        mock_result = {
            "hunt": hunt_schemas.Hunt.model_validate(hunt_1).model_dump(),
            "total": 2,
            "hits": [
                {"value": "1.2.3.4", "type": "ip-dst"},
                {"value": "5.6.7.8", "type": "ip-dst"},
            ],
        }
        with patch("app.repositories.hunts._run_hunt", return_value=mock_result):
            response = client.post(
                f"/hunts/{hunt_1.id}/run",
                headers={"Authorization": "Bearer " + auth_token},
            )
        data = response.json()

        assert response.status_code == status.HTTP_200_OK
        assert data["total"] == 2
        assert len(data["hits"]) == 2
        assert data["hunt"]["id"] == hunt_1.id

    @pytest.mark.parametrize("scopes", [["hunts:run"]])
    def test_run_hunt_not_found(
        self, client: TestClient, auth_token: auth.Token
    ):
        response = client.post(
            "/hunts/999999/run",
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.parametrize("scopes", [[]])
    def test_run_hunt_unauthorized(
        self,
        client: TestClient,
        hunt_1: hunt_models.Hunt,
        auth_token: auth.Token,
    ):
        response = client.post(
            f"/hunts/{hunt_1.id}/run",
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    # ── DELETE /hunts/{id}/history ───────────────────────────────────────────

    @pytest.mark.parametrize("scopes", [["hunts:delete"]])
    def test_delete_hunt_history(
        self,
        client: TestClient,
        hunt_1: hunt_models.Hunt,
        hunt_run_history_1: hunt_models.HuntRunHistory,
        auth_token: auth.Token,
        db: Session,
    ):
        with patch("app.repositories.hunts.get_redis_client") as mock_redis:
            response = client.delete(
                f"/hunts/{hunt_1.id}/history",
                headers={"Authorization": "Bearer " + auth_token},
            )

        assert response.status_code == status.HTTP_204_NO_CONTENT

        remaining = (
            db.query(hunt_models.HuntRunHistory)
            .filter(hunt_models.HuntRunHistory.hunt_id == hunt_1.id)
            .all()
        )
        assert remaining == []

        mock_redis.return_value.delete.assert_any_call(f"hunt:history:{hunt_1.id}")
        mock_redis.return_value.delete.assert_any_call(f"hunt:results:{hunt_1.id}")

    @pytest.mark.parametrize("scopes", [["hunts:delete"]])
    def test_delete_hunt_history_not_found(
        self, client: TestClient, auth_token: auth.Token
    ):
        response = client.delete(
            "/hunts/999999/history",
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.parametrize("scopes", [[]])
    def test_delete_hunt_history_unauthorized(
        self,
        client: TestClient,
        hunt_1: hunt_models.Hunt,
        auth_token: auth.Token,
    ):
        response = client.delete(
            f"/hunts/{hunt_1.id}/history",
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    # ── DELETE /hunts/{id} ───────────────────────────────────────────────────

    @pytest.mark.parametrize("scopes", [[]])
    def test_delete_hunt_unauthorized(
        self,
        client: TestClient,
        hunt_1: hunt_models.Hunt,
        auth_token: auth.Token,
    ):
        response = client.delete(
            f"/hunts/{hunt_1.id}",
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.parametrize("scopes", [["hunts:delete"]])
    def test_delete_hunt_not_found(
        self, client: TestClient, auth_token: auth.Token
    ):
        response = client.delete(
            "/hunts/999999",
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.parametrize("scopes", [["hunts:delete"]])
    def test_delete_hunt(
        self,
        client: TestClient,
        hunt_1: hunt_models.Hunt,
        auth_token: auth.Token,
        db: Session,
    ):
        with patch("app.repositories.tasks.delete_scheduled_tasks_for_hunt"):
            response = client.delete(
                f"/hunts/{hunt_1.id}",
                headers={"Authorization": "Bearer " + auth_token},
            )

        assert response.status_code == status.HTTP_204_NO_CONTENT

        deleted = (
            db.query(hunt_models.Hunt)
            .filter(hunt_models.Hunt.id == hunt_1.id)
            .first()
        )
        assert deleted is None
