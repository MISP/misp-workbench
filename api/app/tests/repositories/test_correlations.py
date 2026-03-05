from unittest.mock import MagicMock, patch

import pytest
from app.repositories.correlations import (
    build_cidr_query,
    build_query,
    delete_correlations,
    delete_event_correlations,
    get_correlations,
    get_correlations_stats,
    get_top_correlated_events,
    get_total_correlations,
)
from app.schemas.correlation import CorrelationQueryParams
from fastapi import HTTPException

PATCH = "app.repositories.correlations.get_opensearch_client"


# ── build_query ───────────────────────────────────────────────────────────────

class TestBuildQuery:
    def _settings(self, prefix_length=10, fuzziness="AUTO"):
        settings = MagicMock()
        settings.get_value.side_effect = lambda key, default: {
            "correlations.prefixLength": prefix_length,
            "correlations.fuzzynessAlgo": fuzziness,
        }.get(key, default)
        return settings

    def test_term_match(self):
        query = build_query("uuid-1", "event-1", "1.2.3.4", "term", self._settings())

        assert query["query"]["bool"]["must"] == [
            {"term": {"value.keyword": "1.2.3.4"}}
        ]
        assert {"term": {"uuid.keyword": "uuid-1"}} in query["query"]["bool"]["must_not"]
        assert {"term": {"event_uuid.keyword": "event-1"}} in query["query"]["bool"]["must_not"]

    def test_prefix_match(self):
        query = build_query("uuid-1", "event-1", "evil.example.com", "prefix", self._settings(prefix_length=5))

        must = query["query"]["bool"]["must"]
        assert len(must) == 1
        assert must[0]["prefix"]["value.keyword"] == "evil."

    def test_fuzzy_match(self):
        query = build_query("uuid-1", "event-1", "evil.com", "fuzzy", self._settings(fuzziness="AUTO"))

        must = query["query"]["bool"]["must"]
        assert len(must) == 1
        assert must[0]["fuzzy"]["value"]["value"] == "evil.com"
        assert must[0]["fuzzy"]["value"]["fuzziness"] == "AUTO"

    def test_unsupported_match_type_raises(self):
        with pytest.raises(ValueError, match="Unsupported match_type"):
            build_query("uuid-1", "event-1", "val", "unknown", self._settings())

    def test_none_uuid_raises(self):
        with pytest.raises(ValueError, match="uuid cannot be None"):
            build_query(None, "event-1", "val", "term", self._settings())

    def test_none_event_uuid_raises(self):
        with pytest.raises(ValueError, match="event_uuid cannot be None"):
            build_query("uuid-1", None, "val", "term", self._settings())


# ── build_cidr_query ──────────────────────────────────────────────────────────

class TestBuildCidrQuery:
    def _doc(self, type_, value):
        return {"_source": {"type": type_, "value": value}}

    def test_ip_src_cidr(self):
        doc = self._doc("ip-src", "192.168.1.0/24")
        query = build_cidr_query("uuid-1", "event-1", doc)

        assert query["query"]["bool"]["must"] == [{"term": {"expanded.ip": "192.168.1.0/24"}}]

    def test_ip_dst_cidr(self):
        doc = self._doc("ip-dst", "10.0.0.0/8")
        query = build_cidr_query("uuid-1", "event-1", doc)

        assert query["query"]["bool"]["must"] == [{"term": {"expanded.ip": "10.0.0.0/8"}}]

    def test_ip_src_port_extracts_cidr(self):
        doc = self._doc("ip-src|port", "192.168.1.0/24|80")
        query = build_cidr_query("uuid-1", "event-1", doc)

        assert query["query"]["bool"]["must"] == [{"term": {"expanded.ip": "192.168.1.0/24"}}]

    def test_domain_ip_extracts_cidr(self):
        doc = self._doc("domain|ip", "evil.com|10.0.0.0/8")
        query = build_cidr_query("uuid-1", "event-1", doc)

        assert query["query"]["bool"]["must"] == [{"term": {"expanded.ip": "10.0.0.0/8"}}]

    def test_no_cidr_slash_raises(self):
        doc = self._doc("ip-src", "192.168.1.1")  # no / → falls to else branch
        with pytest.raises(ValueError, match="Unsupported CIDR type"):
            build_cidr_query("uuid-1", "event-1", doc)

    def test_unsupported_type_raises(self):
        doc = self._doc("domain", "evil.com/24")
        with pytest.raises(ValueError, match="Unsupported CIDR type"):
            build_cidr_query("uuid-1", "event-1", doc)

    def test_must_not_excludes_self(self):
        doc = self._doc("ip-src", "10.0.0.0/8")
        query = build_cidr_query("uuid-1", "event-1", doc)

        assert {"term": {"uuid.keyword": "uuid-1"}} in query["query"]["bool"]["must_not"]
        assert {"term": {"event_uuid.keyword": "event-1"}} in query["query"]["bool"]["must_not"]


# ── get_correlations ──────────────────────────────────────────────────────────

class TestGetCorrelations:
    def _mock_os(self, total=5):
        mock = MagicMock()
        mock.search.return_value = {
            "hits": {"total": {"value": total}, "max_score": 1.0, "hits": []},
            "took": 3,
            "timed_out": False,
        }
        return mock

    def test_no_filters_uses_match_all(self):
        mock_os = self._mock_os()
        with patch(PATCH, return_value=mock_os):
            result = get_correlations(CorrelationQueryParams(), page=1, from_value=0, size=10)

        call_body = mock_os.search.call_args.kwargs["body"]
        assert "match_all" in call_body["query"]
        assert result["total"] == 5
        assert result["page"] == 1

    def test_source_attribute_uuid_filter(self):
        mock_os = self._mock_os()
        with patch(PATCH, return_value=mock_os):
            get_correlations(
                CorrelationQueryParams(source_attribute_uuid="attr-001"),
                page=1, from_value=0, size=10,
            )

        call_body = mock_os.search.call_args.kwargs["body"]
        assert {"term": {"source_attribute_uuid.keyword": "attr-001"}} in call_body["query"]["bool"]["must"]

    def test_source_event_uuid_filter(self):
        mock_os = self._mock_os()
        with patch(PATCH, return_value=mock_os):
            get_correlations(
                CorrelationQueryParams(source_event_uuid="event-aaa"),
                page=1, from_value=0, size=10,
            )

        call_body = mock_os.search.call_args.kwargs["body"]
        assert {"term": {"source_event_uuid.keyword": "event-aaa"}} in call_body["query"]["bool"]["must"]

    def test_target_attribute_uuid_filter(self):
        mock_os = self._mock_os()
        with patch(PATCH, return_value=mock_os):
            get_correlations(
                CorrelationQueryParams(target_attribute_uuid="attr-002"),
                page=1, from_value=0, size=10,
            )

        call_body = mock_os.search.call_args.kwargs["body"]
        assert {"term": {"target_attribute_uuid.keyword": "attr-002"}} in call_body["query"]["bool"]["must"]

    def test_target_event_uuid_filter(self):
        mock_os = self._mock_os()
        with patch(PATCH, return_value=mock_os):
            get_correlations(
                CorrelationQueryParams(target_event_uuid="event-bbb"),
                page=1, from_value=0, size=10,
            )

        call_body = mock_os.search.call_args.kwargs["body"]
        assert {"term": {"target_event_uuid.keyword": "event-bbb"}} in call_body["query"]["bool"]["must"]

    def test_match_type_filter(self):
        mock_os = self._mock_os()
        with patch(PATCH, return_value=mock_os):
            get_correlations(
                CorrelationQueryParams(match_type="term"),
                page=1, from_value=0, size=10,
            )

        call_body = mock_os.search.call_args.kwargs["body"]
        assert {"term": {"match_type.keyword": "term"}} in call_body["query"]["bool"]["must"]

    def test_multiple_filters_combined(self):
        mock_os = self._mock_os()
        with patch(PATCH, return_value=mock_os):
            get_correlations(
                CorrelationQueryParams(
                    source_event_uuid="event-aaa",
                    match_type="prefix",
                ),
                page=1, from_value=0, size=10,
            )

        call_body = mock_os.search.call_args.kwargs["body"]
        must = call_body["query"]["bool"]["must"]
        assert {"term": {"source_event_uuid.keyword": "event-aaa"}} in must
        assert {"term": {"match_type.keyword": "prefix"}} in must

    def test_pagination_sets_from_and_size(self):
        mock_os = self._mock_os()
        with patch(PATCH, return_value=mock_os):
            result = get_correlations(
                CorrelationQueryParams(), page=3, from_value=40, size=20
            )

        call_body = mock_os.search.call_args.kwargs["body"]
        assert call_body["from"] == 40
        assert call_body["size"] == 20
        assert result["page"] == 3
        assert result["size"] == 20


# ── get_top_correlated_events ─────────────────────────────────────────────────

class TestGetTopCorrelatedEvents:
    def test_returns_buckets(self):
        mock_os = MagicMock()
        mock_os.search.return_value = {
            "aggregations": {
                "by_target_event": {
                    "buckets": [
                        {"key": "event-bbb", "doc_count": 10},
                        {"key": "event-ccc", "doc_count": 4},
                    ]
                }
            }
        }

        with patch(PATCH, return_value=mock_os):
            result = get_top_correlated_events("event-aaa")

        assert len(result) == 2
        assert result[0]["key"] == "event-bbb"
        assert result[0]["doc_count"] == 10

    def test_filters_by_source_event_uuid(self):
        mock_os = MagicMock()
        mock_os.search.return_value = {"aggregations": {"by_target_event": {"buckets": []}}}

        with patch(PATCH, return_value=mock_os):
            get_top_correlated_events("event-aaa")

        call_body = mock_os.search.call_args.kwargs["body"]
        assert call_body["query"]["term"]["source_event_uuid.keyword"] == "event-aaa"

    def test_empty_aggregations_returns_empty_list(self):
        mock_os = MagicMock()
        mock_os.search.return_value = {}

        with patch(PATCH, return_value=mock_os):
            result = get_top_correlated_events("event-aaa")

        assert result == []


# ── get_total_correlations ────────────────────────────────────────────────────

class TestGetTotalCorrelations:
    def test_returns_count(self):
        mock_os = MagicMock()
        mock_os.count.return_value = {"count": 42}

        with patch(PATCH, return_value=mock_os):
            result = get_total_correlations()

        assert result == 42
        mock_os.count.assert_called_once_with(index="misp-attribute-correlations")


# ── get_correlations_stats ────────────────────────────────────────────────────

class TestGetCorrelationsStats:
    def test_returns_all_stats(self):
        mock_os = MagicMock()
        mock_os.search.side_effect = [
            # get_top_correlating_events
            {"aggregations": {"by_source_event": {"buckets": [{"key": "event-aaa", "doc_count": 15}]}}},
            # get_top_correlating_attributes
            {"aggregations": {"by_target_attribute": {"buckets": [{"key": "attr-001", "doc_count": 8}]}}},
        ]
        mock_os.count.return_value = {"count": 99}

        with patch(PATCH, return_value=mock_os):
            result = get_correlations_stats()

        assert result["total_correlations"] == 99
        assert len(result["top_correlated_events"]) == 1
        assert result["top_correlated_events"][0]["key"] == "event-aaa"
        assert len(result["top_correlated_attributes"]) == 1
        assert result["top_correlated_attributes"][0]["key"] == "attr-001"


# ── delete_correlations ───────────────────────────────────────────────────────

class TestDeleteCorrelations:
    def test_deletes_and_recreates_index(self):
        mock_os = MagicMock()
        mock_os.indices.get_mapping.return_value = {
            "misp-attribute-correlations": {"mappings": {"properties": {"value": {"type": "text"}}}}
        }

        with patch(PATCH, return_value=mock_os):
            result = delete_correlations()

        mock_os.indices.delete.assert_called_once_with(index="misp-attribute-correlations")
        mock_os.indices.create.assert_called_once()
        create_call = mock_os.indices.create.call_args
        assert create_call.kwargs["index"] == "misp-attribute-correlations"
        assert "mappings" in create_call.kwargs["body"]
        assert result["message"] == "Correlations index deleted successfully."

    def test_opensearch_error_raises_http_exception(self):
        mock_os = MagicMock()
        mock_os.indices.get_mapping.side_effect = Exception("connection refused")

        with patch(PATCH, return_value=mock_os):
            with pytest.raises(HTTPException) as exc_info:
                delete_correlations()

        assert exc_info.value.status_code == 500
        assert "connection refused" in exc_info.value.detail


# ── delete_event_correlations ─────────────────────────────────────────────────

class TestDeleteEventCorrelations:
    def test_deletes_by_event_uuid(self):
        mock_os = MagicMock()

        with patch(PATCH, return_value=mock_os):
            result = delete_event_correlations("event-aaa")

        call_kwargs = mock_os.delete_by_query.call_args.kwargs
        assert call_kwargs["index"] == "misp-attribute-correlations"
        should = call_kwargs["body"]["query"]["bool"]["should"]
        assert {"term": {"source_event_uuid.keyword": "event-aaa"}} in should
        assert {"term": {"target_event_uuid.keyword": "event-aaa"}} in should
        assert result["message"] == "Correlations for event event-aaa deleted successfully."

    def test_opensearch_error_raises_http_exception(self):
        mock_os = MagicMock()
        mock_os.delete_by_query.side_effect = Exception("timeout")

        with patch(PATCH, return_value=mock_os):
            with pytest.raises(HTTPException) as exc_info:
                delete_event_correlations("event-aaa")

        assert exc_info.value.status_code == 500
        assert "timeout" in exc_info.value.detail
