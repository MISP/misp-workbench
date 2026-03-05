from unittest.mock import MagicMock, patch

import pytest
from app.auth import auth
from app.tests.api_tester import ApiTester
from fastapi import status
from fastapi.testclient import TestClient


OPENSEARCH_PATCH = "app.repositories.sightings.get_opensearch_client"
TASKS_PATCH = "app.repositories.sightings.tasks.handle_created_sighting"

MOCK_SEARCH_RESPONSE = {
    "hits": {
        "total": {"value": 2},
        "max_score": 1.5,
        "hits": [
            {"_source": {"value": "1.2.3.4", "type": "positive", "attribute_uuid": "abc-123"}},
            {"_source": {"value": "5.6.7.8", "type": "positive", "attribute_uuid": "def-456"}},
        ],
    },
    "took": 3,
    "timed_out": False,
}

MOCK_HISTOGRAM_RESPONSE = {
    "aggregations": {
        "sightings_over_time": {
            "buckets": [
                {"key_as_string": "2024-01-01T00:00:00.000Z", "key": 1704067200000, "doc_count": 3},
                {"key_as_string": "2024-01-01T01:00:00.000Z", "key": 1704070800000, "doc_count": 7},
            ]
        }
    }
}

MOCK_STATS_RESPONSE = {"hits": {"total": {"value": 10}}}
MOCK_PREV_STATS_RESPONSE = {"hits": {"total": {"value": 5}}}


def make_opensearch_mock(search_return=None):
    mock = MagicMock()
    mock.search.return_value = search_return or MOCK_SEARCH_RESPONSE
    return mock


class TestSightingsResource(ApiTester):
    # ── GET /sightings/ ───────────────────────────────────────────────────────

    @pytest.mark.parametrize("scopes", [["sightings:read"]])
    def test_get_sightings(self, client: TestClient, auth_token: auth.Token):
        with patch(OPENSEARCH_PATCH, return_value=make_opensearch_mock()):
            response = client.get(
                "/sightings/", headers={"Authorization": "Bearer " + auth_token}
            )
        data = response.json()

        assert response.status_code == status.HTTP_200_OK
        assert data["total"] == 2
        assert data["page"] == 1
        assert data["size"] == 10
        assert data["timed_out"] is False
        assert len(data["results"]) == 2

    @pytest.mark.parametrize("scopes", [[]])
    def test_get_sightings_unauthorized(self, client: TestClient, auth_token: auth.Token):
        response = client.get(
            "/sightings/", headers={"Authorization": "Bearer " + auth_token}
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.parametrize("scopes", [["sightings:read"]])
    def test_get_sightings_filter_by_attribute_uuid(
        self, client: TestClient, auth_token: auth.Token
    ):
        mock_os = make_opensearch_mock()
        with patch(OPENSEARCH_PATCH, return_value=mock_os):
            response = client.get(
                "/sightings/",
                params={"attribute_uuid": "abc-123"},
                headers={"Authorization": "Bearer " + auth_token},
            )

        assert response.status_code == status.HTTP_200_OK
        # verify the attribute_uuid filter was added to the query
        call_body = mock_os.search.call_args.kwargs["body"]
        assert {"term": {"attribute_uuid.keyword": "abc-123"}} in call_body["query"]["bool"]["must"]

    @pytest.mark.parametrize("scopes", [["sightings:read"]])
    def test_get_sightings_filter_by_type(
        self, client: TestClient, auth_token: auth.Token
    ):
        mock_os = make_opensearch_mock()
        with patch(OPENSEARCH_PATCH, return_value=mock_os):
            response = client.get(
                "/sightings/",
                params={"type": "positive"},
                headers={"Authorization": "Bearer " + auth_token},
            )

        assert response.status_code == status.HTTP_200_OK
        call_body = mock_os.search.call_args.kwargs["body"]
        assert {"term": {"type.keyword": "positive"}} in call_body["query"]["bool"]["must"]

    @pytest.mark.parametrize("scopes", [["sightings:read"]])
    def test_get_sightings_pagination(
        self, client: TestClient, auth_token: auth.Token
    ):
        mock_os = make_opensearch_mock()
        with patch(OPENSEARCH_PATCH, return_value=mock_os):
            response = client.get(
                "/sightings/",
                params={"page": 2, "size": 5},
                headers={"Authorization": "Bearer " + auth_token},
            )
        data = response.json()

        assert response.status_code == status.HTTP_200_OK
        assert data["page"] == 2
        assert data["size"] == 5
        call_body = mock_os.search.call_args.kwargs["body"]
        assert call_body["from"] == 5   # (page-1) * size
        assert call_body["size"] == 5

    # ── POST /sightings/ ──────────────────────────────────────────────────────

    @pytest.mark.parametrize("scopes", [["sightings:create"]])
    def test_create_sighting_single(
        self, client: TestClient, auth_token: auth.Token
    ):
        mock_os = make_opensearch_mock()
        with patch(OPENSEARCH_PATCH, return_value=mock_os), \
             patch(TASKS_PATCH) as mock_task:
            response = client.post(
                "/sightings/",
                json={"value": "1.2.3.4", "type": "positive"},
                headers={"Authorization": "Bearer " + auth_token},
            )
        data = response.json()

        assert response.status_code == status.HTTP_201_CREATED
        assert data["result"] == "Sighting created successfully"
        mock_os.index.assert_called_once()
        mock_task.delay.assert_called_once()

    @pytest.mark.parametrize("scopes", [["sightings:create"]])
    def test_create_sighting_sets_default_type(
        self, client: TestClient, auth_token: auth.Token
    ):
        mock_os = make_opensearch_mock()
        with patch(OPENSEARCH_PATCH, return_value=mock_os), \
             patch(TASKS_PATCH):
            response = client.post(
                "/sightings/",
                json={"value": "evil.com"},
                headers={"Authorization": "Bearer " + auth_token},
            )

        assert response.status_code == status.HTTP_201_CREATED
        indexed_body = mock_os.index.call_args.kwargs["body"]
        assert indexed_body["type"] == "positive"

    @pytest.mark.parametrize("scopes", [["sightings:create"]])
    def test_create_sightings_bulk(
        self, client: TestClient, auth_token: auth.Token
    ):
        mock_os = make_opensearch_mock()
        with patch(OPENSEARCH_PATCH, return_value=mock_os), \
             patch(TASKS_PATCH) as mock_task, \
             patch("app.repositories.sightings.opensearch_helpers.bulk", return_value=(2, [])):
            response = client.post(
                "/sightings/",
                json=[
                    {"value": "1.2.3.4", "type": "positive"},
                    {"value": "5.6.7.8", "type": "negative"},
                ],
                headers={"Authorization": "Bearer " + auth_token},
            )
        data = response.json()

        assert response.status_code == status.HTTP_201_CREATED
        assert data["result"] == "Sightings created successfully"
        assert mock_task.delay.call_count == 2

    @pytest.mark.parametrize("scopes", [["sightings:create"]])
    def test_create_sighting_missing_value(
        self, client: TestClient, auth_token: auth.Token
    ):
        response = client.post(
            "/sightings/",
            json={"type": "positive"},
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.parametrize("scopes", [[]])
    def test_create_sighting_unauthorized(
        self, client: TestClient, auth_token: auth.Token
    ):
        response = client.post(
            "/sightings/",
            json={"value": "1.2.3.4"},
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    # ── GET /sightings/histogram ──────────────────────────────────────────────

    @pytest.mark.parametrize("scopes", [["sightings:read"]])
    def test_get_sighting_histogram(
        self, client: TestClient, auth_token: auth.Token
    ):
        mock_os = make_opensearch_mock(MOCK_HISTOGRAM_RESPONSE)
        with patch(OPENSEARCH_PATCH, return_value=mock_os):
            response = client.get(
                "/sightings/histogram",
                params={"value": "1.2.3.4"},
                headers={"Authorization": "Bearer " + auth_token},
            )
        data = response.json()

        assert response.status_code == status.HTTP_200_OK
        assert "sightings_over_time" in data
        assert len(data["sightings_over_time"]["buckets"]) == 2
        assert data["sightings_over_time"]["buckets"][0]["doc_count"] == 3

    @pytest.mark.parametrize("scopes", [["sightings:read"]])
    def test_get_sighting_histogram_custom_period_and_interval(
        self, client: TestClient, auth_token: auth.Token
    ):
        mock_os = make_opensearch_mock(MOCK_HISTOGRAM_RESPONSE)
        with patch(OPENSEARCH_PATCH, return_value=mock_os):
            response = client.get(
                "/sightings/histogram",
                params={"value": "evil.com", "period": "30d", "interval": "1d"},
                headers={"Authorization": "Bearer " + auth_token},
            )

        assert response.status_code == status.HTTP_200_OK
        call_body = mock_os.search.call_args.kwargs["body"]
        agg = call_body["aggs"]["sightings_over_time"]["date_histogram"]
        assert agg["fixed_interval"] == "1d"
        assert "now-30d/d" in call_body["query"]["bool"]["must"][2]["range"]["@timestamp"]["gte"]

    @pytest.mark.parametrize("scopes", [["sightings:read"]])
    def test_get_sighting_histogram_missing_value(
        self, client: TestClient, auth_token: auth.Token
    ):
        response = client.get(
            "/sightings/histogram",
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.parametrize("scopes", [[]])
    def test_get_sighting_histogram_unauthorized(
        self, client: TestClient, auth_token: auth.Token
    ):
        response = client.get(
            "/sightings/histogram",
            params={"value": "1.2.3.4"},
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    # ── GET /sightings/stats ──────────────────────────────────────────────────

    @pytest.mark.parametrize("scopes", [["sightings:read"]])
    def test_get_sighting_stats(
        self, client: TestClient, auth_token: auth.Token
    ):
        mock_os = make_opensearch_mock()
        mock_os.search.side_effect = [MOCK_STATS_RESPONSE, MOCK_PREV_STATS_RESPONSE]
        with patch(OPENSEARCH_PATCH, return_value=mock_os):
            response = client.get(
                "/sightings/stats",
                params={"value": "1.2.3.4"},
                headers={"Authorization": "Bearer " + auth_token},
            )
        data = response.json()

        assert response.status_code == status.HTTP_200_OK
        assert data["total"] == 10
        assert data["previous_total"] == 5

    @pytest.mark.parametrize("scopes", [["sightings:read"]])
    def test_get_sighting_stats_missing_value(
        self, client: TestClient, auth_token: auth.Token
    ):
        response = client.get(
            "/sightings/stats",
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.parametrize("scopes", [[]])
    def test_get_sighting_stats_unauthorized(
        self, client: TestClient, auth_token: auth.Token
    ):
        response = client.get(
            "/sightings/stats",
            params={"value": "1.2.3.4"},
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
