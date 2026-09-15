"""API tests for the Tech Lab — Transformation Servos router.

OpenSearch is mocked: these tests are about the router's contract (scopes,
validation, classification), and a real cluster would leave stray pipelines
behind for the next run.
"""

from unittest.mock import MagicMock, patch

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from opensearchpy.exceptions import RequestError

from app.auth import auth
from app.models import servo as servo_models
from app.tests.api_tester import ApiTester

URL_PROCESSORS = [
    {"grok": {"field": "value", "patterns": ["%{IPORHOST:expanded.url.domain}"]}}
]

SYSTEM_PIPELINES = {
    "misp-attributes_default": {
        "description": "Normalization pipeline wrapper",
        "processors": [{"pipeline": {"name": "misp-attributes_ip_extraction"}}],
    },
    "misp-attributes_ip_geoip": {
        "description": "Enrich IP with GeoIP",
        "processors": [{"geoip": {"field": "expanded.ip"}}],
    },
}


@pytest.fixture(autouse=True)
def _opensearch():
    """Stub the cluster. `get_pipeline` answers with the shipped system
    pipelines plus whatever the test under way has 'created'."""
    created: dict[str, dict] = {}

    def put_pipeline(id, body):  # noqa: A002 - matches the opensearch-py kwarg
        created[id] = body
        return {"acknowledged": True}

    def delete_pipeline(id):  # noqa: A002
        created.pop(id, None)
        return {"acknowledged": True}

    def get_pipeline(id=None):  # noqa: A002
        everything = {**SYSTEM_PIPELINES, **created}
        if id is None:
            return everything
        return {id: everything[id]} if id in everything else {}

    client = MagicMock()
    client.ingest.put_pipeline.side_effect = put_pipeline
    client.ingest.delete_pipeline.side_effect = delete_pipeline
    client.ingest.get_pipeline.side_effect = get_pipeline
    client.ingest.simulate.return_value = {
        "docs": [{"doc": {"_source": {"value": "1.2.3.4", "expanded": {}}}}]
    }

    with patch(
        "app.services.tech_lab.servos.chain.OpenSearchClient", client
    ) as patched:
        yield patched


@pytest.fixture(autouse=True)
def _no_leftover_servos(db):
    """ApiTester's cleanup is class-scoped, so without this a servo created by
    one test would still be there for the next one (and a crashed earlier run
    would leak into this one)."""
    db.rollback()
    db.query(servo_models.Servo).delete(synchronize_session=False)
    db.commit()
    yield


class TestServosRouter(ApiTester):
    # ── POST /tech-lab/servos/ ───────────────────────────────────────────────

    @pytest.mark.parametrize("scopes", [["servos:create"]])
    def test_create_servo(self, client: TestClient, auth_token: auth.Token):
        response = client.post(
            "/tech-lab/servos/",
            json={
                "slug": "url_parts",
                "name": "URL parts",
                "description": "Split urls into their components",
                "processors": URL_PROCESSORS,
            },
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert response.status_code == status.HTTP_201_CREATED, response.text
        data = response.json()
        assert data["slug"] == "url_parts"
        assert data["enabled"] is True
        assert data["target_index"] == "misp-attributes"
        assert data["last_synced_at"] is not None

    @pytest.mark.parametrize("scopes", [["servos:create"]])
    def test_create_servo_rejects_a_duplicate_slug(
        self, client: TestClient, auth_token: auth.Token
    ):
        payload = {"slug": "dupe", "name": "Dupe", "processors": URL_PROCESSORS}
        headers = {"Authorization": "Bearer " + auth_token}
        assert (
            client.post("/tech-lab/servos/", json=payload, headers=headers).status_code
            == status.HTTP_201_CREATED
        )
        response = client.post("/tech-lab/servos/", json=payload, headers=headers)
        assert response.status_code == status.HTTP_409_CONFLICT

    @pytest.mark.parametrize("scopes", [["servos:create"]])
    def test_create_servo_rejects_the_system_prefix(
        self, client: TestClient, auth_token: auth.Token
    ):
        # A servo must never be able to shadow a shipped pipeline.
        response = client.post(
            "/tech-lab/servos/",
            json={
                "slug": "misp-attributes_ip_geoip",
                "name": "Impostor",
                "processors": URL_PROCESSORS,
            },
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.parametrize("scopes", [["servos:create"]])
    def test_create_servo_rejects_empty_processors(
        self, client: TestClient, auth_token: auth.Token
    ):
        response = client.post(
            "/tech-lab/servos/",
            json={"slug": "empty", "name": "Empty", "processors": []},
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.parametrize("scopes", [["servos:create"]])
    def test_create_servo_surfaces_the_opensearch_reason(
        self, client: TestClient, auth_token: auth.Token, _opensearch
    ):
        _opensearch.ingest.simulate.side_effect = RequestError(
            400,
            "parse_exception",
            {"error": {"reason": "No processor type exists with name [nope]"}},
        )
        response = client.post(
            "/tech-lab/servos/",
            json={
                "slug": "broken",
                "name": "Broken",
                "processors": [{"nope": {"field": "value"}}],
            },
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert "No processor type exists" in response.json()["detail"]

    @pytest.mark.parametrize("scopes", [["servos:read"]])
    def test_create_servo_requires_the_create_scope(
        self, client: TestClient, auth_token: auth.Token
    ):
        response = client.post(
            "/tech-lab/servos/",
            json={"slug": "nope", "name": "Nope", "processors": URL_PROCESSORS},
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    # ── GET /tech-lab/servos/ ────────────────────────────────────────────────

    @pytest.mark.parametrize("scopes", [["servos:create", "servos:read"]])
    def test_list_servos(self, client: TestClient, auth_token: auth.Token):
        headers = {"Authorization": "Bearer " + auth_token}
        client.post(
            "/tech-lab/servos/",
            json={"slug": "listed", "name": "Listed", "processors": URL_PROCESSORS},
            headers=headers,
        )
        response = client.get("/tech-lab/servos/", headers=headers)
        assert response.status_code == status.HTTP_200_OK, response.text
        assert [s["slug"] for s in response.json()["items"]] == ["listed"]

    @pytest.mark.parametrize("scopes", [["servos:create", "servos:read"]])
    def test_get_servo_by_id(self, client: TestClient, auth_token: auth.Token):
        headers = {"Authorization": "Bearer " + auth_token}
        created = client.post(
            "/tech-lab/servos/",
            json={"slug": "fetched", "name": "Fetched", "processors": URL_PROCESSORS},
            headers=headers,
        ).json()
        response = client.get(f"/tech-lab/servos/{created['id']}", headers=headers)
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["slug"] == "fetched"

    @pytest.mark.parametrize("scopes", [["servos:read"]])
    def test_get_unknown_servo_is_404(self, client: TestClient, auth_token: auth.Token):
        response = client.get(
            "/tech-lab/servos/999999",
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    # ── PATCH / DELETE ───────────────────────────────────────────────────────

    @pytest.mark.parametrize("scopes", [["servos:create", "servos:update"]])
    def test_disabling_a_servo_drops_its_pipeline(
        self, client: TestClient, auth_token: auth.Token, _opensearch
    ):
        headers = {"Authorization": "Bearer " + auth_token}
        created = client.post(
            "/tech-lab/servos/",
            json={"slug": "toggled", "name": "Toggled", "processors": URL_PROCESSORS},
            headers=headers,
        ).json()

        response = client.patch(
            f"/tech-lab/servos/{created['id']}",
            json={"enabled": False},
            headers=headers,
        )
        assert response.status_code == status.HTTP_200_OK, response.text
        assert response.json()["enabled"] is False
        _opensearch.ingest.delete_pipeline.assert_any_call(id="servo_toggled")

    @pytest.mark.parametrize("scopes", [["servos:create", "servos:delete"]])
    def test_delete_servo(
        self, client: TestClient, auth_token: auth.Token, _opensearch
    ):
        headers = {"Authorization": "Bearer " + auth_token}
        created = client.post(
            "/tech-lab/servos/",
            json={"slug": "doomed", "name": "Doomed", "processors": URL_PROCESSORS},
            headers=headers,
        ).json()

        response = client.delete(f"/tech-lab/servos/{created['id']}", headers=headers)
        assert response.status_code == status.HTTP_204_NO_CONTENT
        _opensearch.ingest.delete_pipeline.assert_any_call(id="servo_doomed")

    @pytest.mark.parametrize("scopes", [["servos:read"]])
    def test_delete_servo_requires_the_delete_scope(
        self, client: TestClient, auth_token: auth.Token
    ):
        response = client.delete(
            "/tech-lab/servos/1", headers={"Authorization": "Bearer " + auth_token}
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    # ── Pipeline inventory ───────────────────────────────────────────────────

    @pytest.mark.parametrize("scopes", [["servos:create", "servos:read"]])
    def test_pipeline_inventory_classifies_each_entry(
        self, client: TestClient, auth_token: auth.Token
    ):
        headers = {"Authorization": "Bearer " + auth_token}
        client.post(
            "/tech-lab/servos/",
            json={"slug": "mine", "name": "Mine", "processors": URL_PROCESSORS},
            headers=headers,
        )
        response = client.get("/tech-lab/servos/pipelines", headers=headers)
        assert response.status_code == status.HTTP_200_OK, response.text
        by_name = {p["name"]: p for p in response.json()}

        assert by_name["misp-attributes_default"]["kind"] == "system"
        assert by_name["misp-attributes_default"]["read_only"] is True
        # OpenSearch keeps no mtime for pipelines, so a system row has none.
        assert by_name["misp-attributes_default"]["updated_at"] is None
        # The wrapper's step reads as the pipeline it delegates to.
        assert by_name["misp-attributes_default"]["processor_types"] == [
            "pipeline:misp-attributes_ip_extraction"
        ]

        assert by_name["servo_mine"]["kind"] == "servo"
        assert by_name["servo_mine"]["read_only"] is False
        assert by_name["servo_mine"]["enabled"] is True
        assert by_name["servo_mine"]["updated_at"] is not None

    @pytest.mark.parametrize("scopes", [["servos:read"]])
    def test_pipeline_detail_returns_the_definition(
        self, client: TestClient, auth_token: auth.Token
    ):
        response = client.get(
            "/tech-lab/servos/pipelines/misp-attributes_ip_geoip",
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert response.status_code == status.HTTP_200_OK, response.text
        data = response.json()
        assert data["kind"] == "system"
        assert data["definition"]["processors"][0]["geoip"]["field"] == "expanded.ip"

    @pytest.mark.parametrize("scopes", [["servos:read"]])
    def test_unknown_pipeline_is_404(self, client: TestClient, auth_token: auth.Token):
        response = client.get(
            "/tech-lab/servos/pipelines/does-not-exist",
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.parametrize("scopes", [[]])
    def test_pipeline_inventory_requires_the_read_scope(
        self, client: TestClient, auth_token: auth.Token
    ):
        response = client.get(
            "/tech-lab/servos/pipelines",
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    # ── Templates + dry run ──────────────────────────────────────────────────

    @pytest.mark.parametrize("scopes", [["servos:read"]])
    def test_list_templates(self, client: TestClient, auth_token: auth.Token):
        response = client.get(
            "/tech-lab/servos/templates",
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert response.status_code == status.HTTP_200_OK, response.text
        slugs = {t["slug"] for t in response.json()}
        assert "url_parts" in slugs
        assert all(t["processors"] for t in response.json())

    @pytest.mark.parametrize("scopes", [["servos:create"]])
    def test_simulate_returns_the_transformed_document(
        self, client: TestClient, auth_token: auth.Token
    ):
        response = client.post(
            "/tech-lab/servos/simulate",
            json={"processors": URL_PROCESSORS, "docs": [{"value": "1.2.3.4"}]},
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert response.status_code == status.HTTP_200_OK, response.text
        assert response.json()["ok"] is True
        assert response.json()["docs"] == [{"value": "1.2.3.4", "expanded": {}}]

    @pytest.mark.parametrize("scopes", [["servos:create"]])
    def test_simulate_reports_a_bad_pipeline_without_failing_the_request(
        self, client: TestClient, auth_token: auth.Token, _opensearch
    ):
        _opensearch.ingest.simulate.side_effect = RequestError(
            400, "parse_exception", {"error": {"reason": "bad grok pattern"}}
        )
        response = client.post(
            "/tech-lab/servos/simulate",
            json={"processors": [{"grok": {"field": "value", "patterns": ["%{"]}}]},
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["ok"] is False
        assert response.json()["error"] == "bad grok pattern"

    # ── Reorder + errors ─────────────────────────────────────────────────────

    @pytest.mark.parametrize("scopes", [["servos:create", "servos:update"]])
    def test_reorder_sets_position_in_one_call(
        self, client: TestClient, auth_token: auth.Token
    ):
        headers = {"Authorization": "Bearer " + auth_token}
        created = [
            client.post(
                "/tech-lab/servos/",
                json={"slug": slug, "name": slug, "processors": URL_PROCESSORS},
                headers=headers,
            ).json()
            for slug in ("first", "second", "third")
        ]
        reversed_ids = [s["id"] for s in reversed(created)]

        response = client.post(
            "/tech-lab/servos/reorder",
            json={"servo_ids": reversed_ids},
            headers=headers,
        )
        assert response.status_code == status.HTTP_200_OK, response.text
        assert [s["slug"] for s in response.json()] == ["third", "second", "first"]
        assert [s["position"] for s in response.json()] == [0, 1, 2]

    @pytest.mark.parametrize("scopes", [["servos:update"]])
    def test_reorder_rejects_an_unknown_id(
        self, client: TestClient, auth_token: auth.Token
    ):
        # Renumbering a subset silently would be worse than refusing.
        response = client.post(
            "/tech-lab/servos/reorder",
            json={"servo_ids": [999999]},
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.parametrize("scopes", [["servos:read"]])
    def test_reorder_requires_the_update_scope(
        self, client: TestClient, auth_token: auth.Token
    ):
        response = client.post(
            "/tech-lab/servos/reorder",
            json={"servo_ids": [1]},
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.parametrize("scopes", [["servos:create", "servos:read"]])
    def test_a_drop_processor_is_flagged_on_the_servo(
        self, client: TestClient, auth_token: auth.Token
    ):
        headers = {"Authorization": "Bearer " + auth_token}
        plain = client.post(
            "/tech-lab/servos/",
            json={"slug": "keeps", "name": "Keeps", "processors": URL_PROCESSORS},
            headers=headers,
        ).json()
        dropper = client.post(
            "/tech-lab/servos/",
            json={
                "slug": "discards",
                "name": "Discards",
                "processors": [{"drop": {"if": "ctx.type == 'md5'"}}],
            },
            headers=headers,
        ).json()

        assert plain["drops_documents"] is False
        assert dropper["drops_documents"] is True

    @pytest.mark.parametrize("scopes", [["servos:read"]])
    def test_errors_endpoint_reports_failures_per_servo(
        self, client: TestClient, auth_token: auth.Token, _opensearch
    ):
        _opensearch.search.return_value = {
            "aggregations": {
                "servo_errors": {
                    "buckets": [{"key": "servo_boom: boom", "doc_count": 7}]
                }
            }
        }
        response = client.get(
            "/tech-lab/servos/errors",
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert response.status_code == status.HTTP_200_OK, response.text
        assert response.json()["servo_boom"]["count"] == 7
        assert response.json()["servo_boom"]["messages"][0]["message"] == "boom"

    @pytest.mark.parametrize("scopes", [[]])
    def test_errors_endpoint_requires_the_read_scope(
        self, client: TestClient, auth_token: auth.Token
    ):
        response = client.get(
            "/tech-lab/servos/errors",
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
