from unittest.mock import MagicMock, patch

import pytest
from app.auth import auth
from app.tests.api_tester import ApiTester
from fastapi import status
from fastapi.testclient import TestClient
from opensearchpy.exceptions import NotFoundError


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

MOCK_HISTOGRAM_RESPONSE = {
    "took": 2,
    "timed_out": False,
    "hits": {"total": {"value": 0}, "max_score": None, "hits": []},
    "aggregations": {
        "correlations_over_time": {
            "buckets": [
                {"key_as_string": "2026-04-25", "key": 1, "doc_count": 3},
                {"key_as_string": "2026-04-26", "key": 2, "doc_count": 7},
            ]
        }
    },
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

    # ── GET /correlations/search ──────────────────────────────────────────────

    @pytest.mark.parametrize("scopes", [["correlations:read"]])
    def test_search_correlations(self, client: TestClient, auth_token: auth.Token):
        mock_os = make_opensearch_mock()
        with patch(OPENSEARCH_PATCH, return_value=mock_os):
            response = client.get(
                "/correlations/search",
                params={"query": "1.2.3.4"},
                headers={"Authorization": "Bearer " + auth_token},
            )
        data = response.json()

        assert response.status_code == status.HTTP_200_OK
        assert data["total"] == 3
        assert data["page"] == 1
        assert data["size"] == 10
        assert len(data["results"]) == 1

        call_body = mock_os.search.call_args.kwargs["body"]
        assert call_body["query"]["query_string"]["query"] == "1.2.3.4"
        assert (
            call_body["query"]["query_string"]["default_field"]
            == "target_attribute_value"
        )
        assert call_body["sort"] == [{"@timestamp": {"order": "desc"}}]
        assert mock_os.search.call_args.kwargs["index"] == (
            "misp-attribute-correlations"
        )

    @pytest.mark.parametrize("scopes", [["correlations:read"]])
    def test_search_correlations_pagination_and_sort(
        self, client: TestClient, auth_token: auth.Token
    ):
        mock_os = make_opensearch_mock()
        with patch(OPENSEARCH_PATCH, return_value=mock_os):
            response = client.get(
                "/correlations/search",
                params={
                    "query": "*",
                    "page": 2,
                    "size": 25,
                    "sort_by": "_score",
                    "sort_order": "asc",
                },
                headers={"Authorization": "Bearer " + auth_token},
            )

        assert response.status_code == status.HTTP_200_OK
        call_body = mock_os.search.call_args.kwargs["body"]
        assert call_body["from"] == 25  # (page-1) * size
        assert call_body["size"] == 25
        assert call_body["sort"] == [{"_score": {"order": "asc"}}]

    @pytest.mark.parametrize("scopes", [["correlations:read"]])
    def test_search_correlations_invalid_sort_field(
        self, client: TestClient, auth_token: auth.Token
    ):
        response = client.get(
            "/correlations/search",
            params={"query": "*", "sort_by": "bogus"},
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.parametrize("scopes", [["correlations:read"]])
    def test_search_correlations_missing_query(
        self, client: TestClient, auth_token: auth.Token
    ):
        response = client.get(
            "/correlations/search",
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.parametrize("scopes", [["correlations:read"]])
    def test_search_correlations_index_missing_returns_empty(
        self, client: TestClient, auth_token: auth.Token
    ):
        mock_os = make_opensearch_mock()
        mock_os.search.side_effect = NotFoundError(
            404, "index_not_found_exception", {}
        )
        with patch(OPENSEARCH_PATCH, return_value=mock_os):
            response = client.get(
                "/correlations/search",
                params={"query": "*"},
                headers={"Authorization": "Bearer " + auth_token},
            )
        data = response.json()

        assert response.status_code == status.HTTP_200_OK
        assert data["total"] == 0
        assert data["results"] == []

    @pytest.mark.parametrize("scopes", [[]])
    def test_search_correlations_unauthorized(
        self, client: TestClient, auth_token: auth.Token
    ):
        response = client.get(
            "/correlations/search",
            params={"query": "*"},
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    # ── GET /correlations/histogram ───────────────────────────────────────────

    @pytest.mark.parametrize("scopes", [["correlations:read"]])
    def test_get_correlations_histogram(
        self, client: TestClient, auth_token: auth.Token
    ):
        mock_os = make_opensearch_mock(MOCK_HISTOGRAM_RESPONSE)
        with patch(OPENSEARCH_PATCH, return_value=mock_os):
            response = client.get(
                "/correlations/histogram",
                params={"query": "*"},
                headers={"Authorization": "Bearer " + auth_token},
            )
        data = response.json()

        assert response.status_code == status.HTTP_200_OK
        assert len(data["buckets"]) == 2
        assert data["buckets"][0]["doc_count"] == 3

        call_body = mock_os.search.call_args.kwargs["body"]
        assert call_body["size"] == 0
        assert (
            call_body["aggs"]["correlations_over_time"]["date_histogram"][
                "calendar_interval"
            ]
            == "1d"
        )
        assert (
            call_body["aggs"]["correlations_over_time"]["date_histogram"]["field"]
            == "@timestamp"
        )

    @pytest.mark.parametrize("scopes", [["correlations:read"]])
    def test_get_correlations_histogram_custom_interval(
        self, client: TestClient, auth_token: auth.Token
    ):
        mock_os = make_opensearch_mock(MOCK_HISTOGRAM_RESPONSE)
        with patch(OPENSEARCH_PATCH, return_value=mock_os):
            response = client.get(
                "/correlations/histogram",
                params={"query": "*", "interval": "1w"},
                headers={"Authorization": "Bearer " + auth_token},
            )

        assert response.status_code == status.HTTP_200_OK
        call_body = mock_os.search.call_args.kwargs["body"]
        assert (
            call_body["aggs"]["correlations_over_time"]["date_histogram"][
                "calendar_interval"
            ]
            == "1w"
        )

    @pytest.mark.parametrize("scopes", [["correlations:read"]])
    def test_get_correlations_histogram_invalid_interval(
        self, client: TestClient, auth_token: auth.Token
    ):
        response = client.get(
            "/correlations/histogram",
            params={"query": "*", "interval": "1y"},
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.parametrize("scopes", [["correlations:read"]])
    def test_get_correlations_histogram_index_missing_returns_empty(
        self, client: TestClient, auth_token: auth.Token
    ):
        mock_os = make_opensearch_mock()
        mock_os.search.side_effect = NotFoundError(
            404, "index_not_found_exception", {}
        )
        with patch(OPENSEARCH_PATCH, return_value=mock_os):
            response = client.get(
                "/correlations/histogram",
                params={"query": "*"},
                headers={"Authorization": "Bearer " + auth_token},
            )
        data = response.json()

        assert response.status_code == status.HTTP_200_OK
        assert data == {"buckets": []}

    @pytest.mark.parametrize("scopes", [[]])
    def test_get_correlations_histogram_unauthorized(
        self, client: TestClient, auth_token: auth.Token
    ):
        response = client.get(
            "/correlations/histogram",
            params={"query": "*"},
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

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
