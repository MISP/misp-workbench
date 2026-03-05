from unittest.mock import MagicMock, patch

import pytest
from app.auth import auth
from app.tests.api_tester import ApiTester
from fastapi import status
from fastapi.testclient import TestClient


OPENSEARCH_PATCH = "app.repositories.correlations.get_opensearch_client"

MOCK_SEARCH_RESPONSE = {
    "hits": {
        "total": {"value": 3},
        "max_score": 1.0,
        "hits": [
            {
                "_source": {
                    "source_attribute_uuid": "attr-001",
                    "source_event_uuid": "event-aaa",
                    "target_attribute_uuid": "attr-002",
                    "target_event_uuid": "event-bbb",
                    "match_type": "term",
                }
            },
        ],
    },
    "took": 5,
    "timed_out": False,
}

MOCK_TOP_EVENTS_RESPONSE = {
    "aggregations": {
        "by_target_event": {
            "buckets": [
                {"key": "event-bbb", "doc_count": 10},
                {"key": "event-ccc", "doc_count": 4},
            ]
        }
    }
}

MOCK_STATS_TOP_EVENTS_RESPONSE = {
    "aggregations": {
        "by_source_event": {
            "buckets": [
                {"key": "event-aaa", "doc_count": 15},
            ]
        }
    }
}

MOCK_STATS_TOP_ATTRIBUTES_RESPONSE = {
    "aggregations": {
        "by_target_attribute": {
            "buckets": [
                {
                    "key": "attr-002",
                    "doc_count": 8,
                    "top_attribute_info": {
                        "hits": {
                            "hits": [
                                {
                                    "_source": {
                                        "target_attribute_type": "ip-dst",
                                        "target_attribute_value": "1.2.3.4",
                                        "target_event_uuid": "event-bbb",
                                    }
                                }
                            ]
                        }
                    },
                }
            ]
        }
    }
}

MOCK_COUNT_RESPONSE = {"count": 42}


def make_opensearch_mock(search_return=None):
    mock = MagicMock()
    mock.search.return_value = search_return or MOCK_SEARCH_RESPONSE
    mock.count.return_value = MOCK_COUNT_RESPONSE
    return mock


class TestCorrelationsResource(ApiTester):
    # ── GET /correlations/ ────────────────────────────────────────────────────

    @pytest.mark.parametrize("scopes", [["correlations:read"]])
    def test_get_correlations(self, client: TestClient, auth_token: auth.Token):
        with patch(OPENSEARCH_PATCH, return_value=make_opensearch_mock()):
            response = client.get(
                "/correlations/", headers={"Authorization": "Bearer " + auth_token}
            )
        data = response.json()

        assert response.status_code == status.HTTP_200_OK
        assert data["total"] == 3
        assert data["page"] == 1
        assert data["size"] == 10
        assert data["timed_out"] is False
        assert len(data["results"]) == 1

    @pytest.mark.parametrize("scopes", [[]])
    def test_get_correlations_unauthorized(
        self, client: TestClient, auth_token: auth.Token
    ):
        response = client.get(
            "/correlations/", headers={"Authorization": "Bearer " + auth_token}
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.parametrize("scopes", [["correlations:read"]])
    def test_get_correlations_filter_by_source_attribute_uuid(
        self, client: TestClient, auth_token: auth.Token
    ):
        mock_os = make_opensearch_mock()
        with patch(OPENSEARCH_PATCH, return_value=mock_os):
            response = client.get(
                "/correlations/",
                params={"source_attribute_uuid": "attr-001"},
                headers={"Authorization": "Bearer " + auth_token},
            )

        assert response.status_code == status.HTTP_200_OK
        call_body = mock_os.search.call_args.kwargs["body"]
        assert {
            "term": {"source_attribute_uuid.keyword": "attr-001"}
        } in call_body["query"]["bool"]["must"]

    @pytest.mark.parametrize("scopes", [["correlations:read"]])
    def test_get_correlations_filter_by_source_event_uuid(
        self, client: TestClient, auth_token: auth.Token
    ):
        mock_os = make_opensearch_mock()
        with patch(OPENSEARCH_PATCH, return_value=mock_os):
            response = client.get(
                "/correlations/",
                params={"source_event_uuid": "event-aaa"},
                headers={"Authorization": "Bearer " + auth_token},
            )

        assert response.status_code == status.HTTP_200_OK
        call_body = mock_os.search.call_args.kwargs["body"]
        assert {
            "term": {"source_event_uuid.keyword": "event-aaa"}
        } in call_body["query"]["bool"]["must"]

    @pytest.mark.parametrize("scopes", [["correlations:read"]])
    def test_get_correlations_filter_by_match_type(
        self, client: TestClient, auth_token: auth.Token
    ):
        mock_os = make_opensearch_mock()
        with patch(OPENSEARCH_PATCH, return_value=mock_os):
            response = client.get(
                "/correlations/",
                params={"match_type": "term"},
                headers={"Authorization": "Bearer " + auth_token},
            )

        assert response.status_code == status.HTTP_200_OK
        call_body = mock_os.search.call_args.kwargs["body"]
        assert {"term": {"match_type.keyword": "term"}} in call_body["query"]["bool"]["must"]

    @pytest.mark.parametrize("scopes", [["correlations:read"]])
    def test_get_correlations_no_filters_uses_match_all(
        self, client: TestClient, auth_token: auth.Token
    ):
        mock_os = make_opensearch_mock()
        with patch(OPENSEARCH_PATCH, return_value=mock_os):
            response = client.get(
                "/correlations/",
                headers={"Authorization": "Bearer " + auth_token},
            )

        assert response.status_code == status.HTTP_200_OK
        call_body = mock_os.search.call_args.kwargs["body"]
        assert "match_all" in call_body["query"]

    @pytest.mark.parametrize("scopes", [["correlations:read"]])
    def test_get_correlations_pagination(
        self, client: TestClient, auth_token: auth.Token
    ):
        mock_os = make_opensearch_mock()
        with patch(OPENSEARCH_PATCH, return_value=mock_os):
            response = client.get(
                "/correlations/",
                params={"page": 3, "size": 20},
                headers={"Authorization": "Bearer " + auth_token},
            )
        data = response.json()

        assert response.status_code == status.HTTP_200_OK
        assert data["page"] == 3
        assert data["size"] == 20
        call_body = mock_os.search.call_args.kwargs["body"]
        assert call_body["from"] == 40  # (page-1) * size
        assert call_body["size"] == 20

    # ── GET /correlations/events/{uuid}/top ───────────────────────────────────

    @pytest.mark.parametrize("scopes", [["correlations:read"]])
    def test_get_top_correlated_events(
        self, client: TestClient, auth_token: auth.Token
    ):
        mock_os = make_opensearch_mock(MOCK_TOP_EVENTS_RESPONSE)
        with patch(OPENSEARCH_PATCH, return_value=mock_os):
            response = client.get(
                "/correlations/events/event-aaa/top",
                headers={"Authorization": "Bearer " + auth_token},
            )
        data = response.json()

        assert response.status_code == status.HTTP_200_OK
        assert len(data) == 2
        assert data[0]["key"] == "event-bbb"
        assert data[0]["doc_count"] == 10

    @pytest.mark.parametrize("scopes", [["correlations:read"]])
    def test_get_top_correlated_events_filters_by_uuid(
        self, client: TestClient, auth_token: auth.Token
    ):
        mock_os = make_opensearch_mock(MOCK_TOP_EVENTS_RESPONSE)
        with patch(OPENSEARCH_PATCH, return_value=mock_os):
            response = client.get(
                "/correlations/events/event-aaa/top",
                headers={"Authorization": "Bearer " + auth_token},
            )

        assert response.status_code == status.HTTP_200_OK
        call_body = mock_os.search.call_args.kwargs["body"]
        assert call_body["query"]["term"]["source_event_uuid.keyword"] == "event-aaa"

    @pytest.mark.parametrize("scopes", [[]])
    def test_get_top_correlated_events_unauthorized(
        self, client: TestClient, auth_token: auth.Token
    ):
        response = client.get(
            "/correlations/events/event-aaa/top",
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    # ── GET /correlations/stats ───────────────────────────────────────────────

    @pytest.mark.parametrize("scopes", [["correlations:read"]])
    def test_get_correlations_stats(
        self, client: TestClient, auth_token: auth.Token
    ):
        mock_os = make_opensearch_mock()
        mock_os.search.side_effect = [
            MOCK_STATS_TOP_EVENTS_RESPONSE,
            MOCK_STATS_TOP_ATTRIBUTES_RESPONSE,
        ]
        with patch(OPENSEARCH_PATCH, return_value=mock_os):
            response = client.get(
                "/correlations/stats",
                headers={"Authorization": "Bearer " + auth_token},
            )
        data = response.json()

        assert response.status_code == status.HTTP_200_OK
        assert data["total_correlations"] == 42
        assert len(data["top_correlated_events"]) == 1
        assert data["top_correlated_events"][0]["key"] == "event-aaa"
        assert len(data["top_correlated_attributes"]) == 1
        assert data["top_correlated_attributes"][0]["key"] == "attr-002"

    @pytest.mark.parametrize("scopes", [[]])
    def test_get_correlations_stats_unauthorized(
        self, client: TestClient, auth_token: auth.Token
    ):
        response = client.get(
            "/correlations/stats",
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    # ── DELETE /correlations/ ─────────────────────────────────────────────────

    @pytest.mark.parametrize("scopes", [["correlations:delete"]])
    def test_delete_correlations(
        self, client: TestClient, auth_token: auth.Token
    ):
        mock_os = make_opensearch_mock()
        mock_os.indices.get_mapping.return_value = {
            "misp-attribute-correlations": {"mappings": {}}
        }
        with patch(OPENSEARCH_PATCH, return_value=mock_os):
            response = client.delete(
                "/correlations/",
                headers={"Authorization": "Bearer " + auth_token},
            )
        data = response.json()

        assert response.status_code == status.HTTP_200_OK
        assert data["message"] == "Correlations index deleted successfully."
        mock_os.indices.delete.assert_called_once_with(
            index="misp-attribute-correlations"
        )
        mock_os.indices.create.assert_called_once()

    @pytest.mark.parametrize("scopes", [[]])
    def test_delete_correlations_unauthorized(
        self, client: TestClient, auth_token: auth.Token
    ):
        response = client.delete(
            "/correlations/",
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
