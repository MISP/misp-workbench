from unittest.mock import MagicMock, patch

import pytest
from app.repositories import correlations as correlations_repository
from app.repositories.correlations import (
    build_chunk_correlation_docs,
    build_cidr_query,
    build_query,
    chunked,
    correlate_attribute,
    correlate_attribute_uuids,
    delete_attribute_correlations,
    delete_attributes_correlations,
    delete_correlations,
    delete_event_correlations,
    get_attributes_by_uuid,
    get_correlations,
    get_correlations_stats,
    get_top_correlated_events,
    get_total_correlations,
    index_correlation_docs,
    is_correlatable,
)
from app.schemas.correlation import CorrelationQueryParams
from fastapi import HTTPException
from opensearchpy.exceptions import NotFoundError

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

        should = query["query"]["bool"]["must"][0]["bool"]["should"]
        assert {"term": {"value.keyword": "1.2.3.4"}} in should
        assert {"terms": {"expanded.value_parts": ["1.2.3.4"]}} in should
        assert {"term": {"uuid.keyword": "uuid-1"}} in query["query"]["bool"]["must_not"]
        assert {"term": {"event_uuid": "event-1"}} in query["query"]["bool"]["must_not"]

    def test_term_match_drops_the_port_component(self):
        query = build_query(
            "uuid-1",
            "event-1",
            "1.2.3.4|443",
            "term",
            self._settings(),
            "ip-src|port",
        )

        should = query["query"]["bool"]["must"][0]["bool"]["should"]
        # the address correlates, the port does not
        assert {"terms": {"expanded.value_parts": ["1.2.3.4"]}} in should

    def test_term_match_covers_composite_components(self):
        query = build_query(
            "uuid-1", "event-1", "evil.com|1.2.3.4", "term", self._settings()
        )

        should = query["query"]["bool"]["must"][0]["bool"]["should"]
        # the whole value, and either component on its own
        assert {"term": {"value.keyword": "evil.com|1.2.3.4"}} in should
        assert {
            "terms": {"expanded.value_parts": ["evil.com", "1.2.3.4"]}
        } in should

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


class TestMinScore:
    def _settings(self, min_score=2):
        settings = MagicMock()
        settings.get_value.side_effect = lambda key, default: {
            "correlations.minScore": min_score,
        }.get(key, default)
        return settings

    def test_applied_to_approximate_matches(self):
        assert correlations_repository.min_score_for("fuzzy", self._settings()) == 2
        assert correlations_repository.min_score_for("prefix", self._settings()) == 2

    def test_not_applied_to_exact_matches(self):
        # a term or cidr hit is exact; its score says nothing about quality, so
        # a floor there would only drop correct correlations
        assert correlations_repository.min_score_for("term", self._settings()) is None
        assert correlations_repository.min_score_for("cidr", self._settings()) is None

    def test_zero_means_no_floor(self):
        assert correlations_repository.min_score_for("fuzzy", self._settings(0)) is None

    def test_reaches_the_search_body(self):
        mock_os = MagicMock()
        mock_os.msearch.return_value = {"responses": [{"hits": {"hits": []}}]}

        with patch(PATCH, return_value=mock_os):
            correlations_repository.run_correlation_msearch([({"query": {}}, 3)], 10)

        body = mock_os.msearch.call_args.kwargs["body"]
        assert body[1]["min_score"] == 3

    def test_absent_when_there_is_no_floor(self):
        mock_os = MagicMock()
        mock_os.msearch.return_value = {"responses": [{"hits": {"hits": []}}]}

        with patch(PATCH, return_value=mock_os):
            correlations_repository.run_correlation_msearch([({"query": {}}, None)], 10)

        assert "min_score" not in mock_os.msearch.call_args.kwargs["body"][1]


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
        assert {"term": {"event_uuid": "event-1"}} in query["query"]["bool"]["must_not"]


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


# ── chunked ───────────────────────────────────────────────────────────────────

class TestChunked:
    def test_splits_into_chunks(self):
        assert list(chunked(range(5), 2)) == [[0, 1], [2, 3], [4]]

    def test_streams_generators(self):
        assert list(chunked((n for n in range(3)), 5)) == [[0, 1, 2]]

    def test_empty_yields_nothing(self):
        assert list(chunked([], 3)) == []


# ── delete_attributes_correlations ────────────────────────────────────────────

class TestDeleteAttributesCorrelations:
    def test_deletes_both_directions(self):
        mock_os = MagicMock()

        with patch(PATCH, return_value=mock_os):
            assert delete_attribute_correlations("attr-aaa") is True

        call_kwargs = mock_os.delete_by_query.call_args.kwargs
        assert call_kwargs["index"] == "misp-attribute-correlations"
        should = call_kwargs["body"]["query"]["bool"]["should"]
        assert {"terms": {"source_attribute_uuid.keyword": ["attr-aaa"]}} in should
        assert {"terms": {"target_attribute_uuid.keyword": ["attr-aaa"]}} in should

    def test_batches_are_chunked(self):
        mock_os = MagicMock()
        uuids = [f"attr-{n}" for n in range(5)]

        with patch(PATCH, return_value=mock_os), \
                patch.object(correlations_repository, "DELETE_CHUNK_SIZE", 2):
            assert delete_attributes_correlations(uuids) is True

        assert mock_os.delete_by_query.call_count == 3

    def test_missing_index_is_not_an_error(self):
        mock_os = MagicMock()
        mock_os.delete_by_query.side_effect = NotFoundError(404, "no index", {})

        with patch(PATCH, return_value=mock_os):
            assert delete_attribute_correlations("attr-aaa") is True


# ── is_correlatable ───────────────────────────────────────────────────────────

class TestIsCorrelatable:
    def _doc(self, **overrides):
        source = {
            "value": "1.2.3.4",
            "event_uuid": "event-1",
            "type": "ip-src",
            "disable_correlation": False,
            "deleted": False,
        }
        source.update(overrides)
        return {"_id": "attr-1", "_source": source}

    def test_plain_attribute_is_correlatable(self):
        assert is_correlatable(self._doc()) is True

    def test_empty_value_is_not_correlatable(self):
        assert is_correlatable(self._doc(value="")) is False

    def test_missing_event_uuid_is_not_correlatable(self):
        assert is_correlatable(self._doc(event_uuid=None)) is False

    def test_disabled_correlation_is_not_correlatable(self):
        assert is_correlatable(self._doc(disable_correlation=True)) is False

    def test_deleted_is_not_correlatable(self):
        assert is_correlatable(self._doc(deleted=True)) is False


def _attribute(uuid, value="1.2.3.4", event_uuid="event-1", score=None, **overrides):
    source = {
        "uuid": uuid,
        "value": value,
        "event_uuid": event_uuid,
        "type": "ip-src",
        "disable_correlation": False,
        "deleted": False,
    }
    source.update(overrides)
    doc = {"_id": uuid, "_source": source}
    if score is not None:
        doc["_score"] = score
    return doc


def _settings(match_types=None, **overrides):
    values = {"correlations.matchTypes": match_types or ["term"]}
    values.update(overrides)
    settings = MagicMock()
    settings.get_value.side_effect = lambda key, default: values.get(key, default)
    return settings


# ── build_chunk_correlation_docs ──────────────────────────────────────────────

class TestBuildChunkCorrelationDocs:
    def _mock_os(self, responses):
        mock = MagicMock()
        mock.msearch.return_value = {
            "responses": [{"hits": {"hits": hits}} for hits in responses]
        }
        return mock

    def test_one_multi_search_for_the_whole_chunk(self):
        docs = [
            _attribute("attr-1", value="1.1.1.1"),
            _attribute("attr-2", value="2.2.2.2"),
        ]
        mock_os = self._mock_os([[], []])

        with patch(PATCH, return_value=mock_os):
            build_chunk_correlation_docs(docs, _settings(), bidirectional=True)

        mock_os.msearch.assert_called_once()
        # two queries, each one a header line plus a body line
        assert len(mock_os.msearch.call_args.kwargs["body"]) == 4

    def test_identical_queries_run_once(self):
        # same value in the same event: the query excludes the whole event, so
        # both attributes would search for exactly the same thing
        docs = [_attribute("attr-1"), _attribute("attr-2")]
        target = _attribute("attr-old", event_uuid="event-2", score=2.0)
        mock_os = self._mock_os([[target]])

        with patch(PATCH, return_value=mock_os):
            correlation_docs = build_chunk_correlation_docs(
                docs, _settings(), bidirectional=True
            )

        assert len(mock_os.msearch.call_args.kwargs["body"]) == 2
        # both attributes still get their correlations, in both directions
        assert {doc["_id"] for doc in correlation_docs} == {
            "attr-1|attr-old|term",
            "attr-old|attr-1|term",
            "attr-2|attr-old|term",
            "attr-old|attr-2|term",
        }

    def test_forward_only_when_not_bidirectional(self):
        docs = [_attribute("attr-1")]
        target = _attribute("attr-old", event_uuid="event-2", score=2.0)
        mock_os = self._mock_os([[target]])

        with patch(PATCH, return_value=mock_os):
            correlation_docs = build_chunk_correlation_docs(
                docs, _settings(), bidirectional=False
            )

        assert [doc["_id"] for doc in correlation_docs] == ["attr-1|attr-old|term"]

    def test_source_keeps_its_own_type(self):
        docs = [_attribute("attr-1", type="domain|ip", value="evil.com|1.1.1.1")]
        target = _attribute("attr-old", event_uuid="event-2", score=2.0)
        mock_os = self._mock_os([[target]])

        with patch(PATCH, return_value=mock_os):
            correlation_docs = build_chunk_correlation_docs(
                docs, _settings(), bidirectional=False
            )

        assert correlation_docs[0]["_source"]["source_attribute_type"] == "domain|ip"
        assert correlation_docs[0]["_source"]["target_attribute_type"] == "ip-src"

    def test_non_correlatable_docs_and_hits_are_skipped(self):
        docs = [_attribute("attr-1", deleted=True)]
        mock_os = self._mock_os([])

        with patch(PATCH, return_value=mock_os):
            assert build_chunk_correlation_docs(docs, _settings(), True) == []

        mock_os.msearch.assert_not_called()

    def test_failed_sub_search_is_logged_and_skipped(self):
        docs = [_attribute("attr-1")]
        mock_os = MagicMock()
        mock_os.msearch.return_value = {"responses": [{"error": "boom"}]}

        with patch(PATCH, return_value=mock_os):
            assert build_chunk_correlation_docs(docs, _settings(), True) == []


# ── index_correlation_docs ────────────────────────────────────────────────────

class TestIndexCorrelationDocs:
    def _docs(self):
        return [
            {"_index": "misp-attribute-correlations", "_id": "a|b|term", "_source": {}},
            {"_index": "misp-attribute-correlations", "_id": "b|a|term", "_source": {}},
        ]

    def test_writes_with_op_type_create(self):
        with patch(PATCH), patch(
            "app.repositories.correlations.opensearch_helpers.bulk",
            return_value=(2, []),
        ) as bulk:
            created = index_correlation_docs(self._docs())

        actions = bulk.call_args.args[1]
        assert all(action["_op_type"] == "create" for action in actions)
        assert len(created) == 2

    def test_existing_correlations_are_not_reported_as_created(self):
        errors = [{"create": {"_id": "a|b|term", "status": 409, "error": {}}}]

        with patch(PATCH), patch(
            "app.repositories.correlations.opensearch_helpers.bulk",
            return_value=(1, errors),
        ):
            created = index_correlation_docs(self._docs())

        assert [doc["_id"] for doc in created] == ["b|a|term"]

    def test_hard_failures_are_not_reported_as_created(self):
        errors = [{"create": {"_id": "a|b|term", "status": 500, "error": {}}}]

        with patch(PATCH), patch(
            "app.repositories.correlations.opensearch_helpers.bulk",
            return_value=(1, errors),
        ):
            created = index_correlation_docs(self._docs())

        assert [doc["_id"] for doc in created] == ["b|a|term"]


# ── correlate_attribute ───────────────────────────────────────────────────────

class TestCorrelateAttribute:
    ATTR_UUID = "attr-new"

    def _mock_os(
        self, doc, hits, event_disable_correlation=False, known_ids=()
    ):
        mock = MagicMock()

        def get(index, id, **kwargs):
            if index == "misp-events":
                return {"_source": {"disable_correlation": event_disable_correlation}}
            return doc

        mock.get.side_effect = get
        mock.search.return_value = {
            "hits": {"hits": [{"_id": _id} for _id in known_ids]}
        }
        mock.msearch.return_value = {"responses": [{"hits": {"hits": hits}}]}
        return mock

    def _patch_bulk(self, created=2):
        return patch(
            "app.repositories.correlations.opensearch_helpers.bulk",
            return_value=(created, []),
        )

    def test_stores_both_directions_and_notifies(self):
        doc = _attribute(self.ATTR_UUID)
        hit = _attribute("attr-old", event_uuid="event-2", score=3.0)
        mock_os = self._mock_os(doc, [hit])

        with patch(PATCH, return_value=mock_os), self._patch_bulk(), \
                patch("app.repositories.correlations.tasks") as mock_tasks:
            result = correlate_attribute(_settings(), self.ATTR_UUID)

        assert result == {"stored": 2}
        # one batched notification task carrying both directions
        mock_tasks.handle_created_correlations.delay.assert_called_once()
        payloads = mock_tasks.handle_created_correlations.delay.call_args.args[0]
        assert {payload["source_attribute_uuid"] for payload in payloads} == {
            self.ATTR_UUID,
            "attr-old",
        }

    def test_stale_correlations_are_dropped_first(self):
        doc = _attribute(self.ATTR_UUID)
        mock_os = self._mock_os(doc, [])

        with patch(PATCH, return_value=mock_os), self._patch_bulk(0), \
                patch("app.repositories.correlations.tasks"):
            result = correlate_attribute(_settings(), self.ATTR_UUID)

        assert result == {"stored": 0}
        assert mock_os.delete_by_query.called

    def test_attribute_with_correlation_disabled_is_skipped(self):
        doc = _attribute(self.ATTR_UUID, disable_correlation=True)
        mock_os = self._mock_os(doc, [])

        with patch(PATCH, return_value=mock_os), \
                patch("app.repositories.correlations.tasks"):
            result = correlate_attribute(_settings(), self.ATTR_UUID)

        assert result == {"stored": 0}
        # stale correlations are still cleaned up, but no matching runs
        assert mock_os.delete_by_query.called
        mock_os.msearch.assert_not_called()

    def test_event_with_correlation_disabled_is_skipped(self):
        doc = _attribute(self.ATTR_UUID)
        mock_os = self._mock_os(doc, [], event_disable_correlation=True)

        with patch(PATCH, return_value=mock_os), \
                patch("app.repositories.correlations.tasks"):
            result = correlate_attribute(_settings(), self.ATTR_UUID)

        assert result == {"stored": 0}
        mock_os.msearch.assert_not_called()

    def test_unindexed_attribute_is_a_noop(self):
        mock_os = MagicMock()
        mock_os.get.side_effect = NotFoundError(404, "not found", {})

        with patch(PATCH, return_value=mock_os):
            result = correlate_attribute(_settings(), self.ATTR_UUID)

        assert result == {"stored": 0}
        assert not mock_os.delete_by_query.called

    def test_rebuilt_correlations_are_not_notified_again(self):
        doc = _attribute(self.ATTR_UUID)
        hit = _attribute("attr-old", event_uuid="event-2", score=3.0)
        mock_os = self._mock_os(
            doc, [hit], known_ids=[f"{self.ATTR_UUID}|attr-old|term"]
        )

        with patch(PATCH, return_value=mock_os), self._patch_bulk(), \
                patch("app.repositories.correlations.tasks") as mock_tasks:
            result = correlate_attribute(_settings(), self.ATTR_UUID)

        assert result == {"stored": 2}
        # only the reverse direction is new
        payloads = mock_tasks.handle_created_correlations.delay.call_args.args[0]
        assert [payload["source_attribute_uuid"] for payload in payloads] == ["attr-old"]


# ── get_attributes_by_uuid ────────────────────────────────────────────────────

class TestGetAttributesByUuid:
    def test_reads_attributes_with_one_mget_per_chunk(self):
        mock_os = MagicMock()
        mock_os.mget.side_effect = [
            {
                "docs": [
                    {**_attribute("attr-1"), "found": True},
                    {**_attribute("attr-2"), "found": True},
                ]
            },
            {"docs": [{"_id": "attr-3", "found": False}]},
        ]

        with patch(PATCH, return_value=mock_os), \
                patch.object(correlations_repository, "MGET_CHUNK_SIZE", 2):
            docs = list(get_attributes_by_uuid(["attr-1", "attr-2", "attr-3"]))

        assert mock_os.mget.call_count == 2
        assert [doc["_id"] for doc in docs] == ["attr-1", "attr-2"]


# ── correlate_attribute_uuids ─────────────────────────────────────────────────

class TestCorrelateAttributeUuids:
    def _mock_os(self, docs, hits):
        mock = MagicMock()
        mock.mget.return_value = {"docs": [{**doc, "found": True} for doc in docs]}
        mock.get.return_value = {"_source": {"disable_correlation": False}}

        def msearch(body):
            # one response per query, and a query is a header plus a body line
            return {"responses": [{"hits": {"hits": hits}}] * (len(body) // 2)}

        mock.msearch.side_effect = msearch
        return mock

    def test_empty_batch_is_a_noop(self):
        mock_os = MagicMock()

        with patch(PATCH, return_value=mock_os):
            assert correlate_attribute_uuids(_settings(), []) == {"stored": 0}

        assert not mock_os.mget.called

    def test_correlates_the_whole_batch(self):
        docs = [_attribute("attr-1"), _attribute("attr-2", event_uuid="event-2")]
        hit = _attribute("attr-old", event_uuid="event-3", score=1.0)
        mock_os = self._mock_os(docs, [hit])

        with patch(PATCH, return_value=mock_os), \
                patch(
                    "app.repositories.correlations.opensearch_helpers.bulk",
                    return_value=(4, []),
                ), \
                patch("app.repositories.correlations.tasks"):
            result = correlate_attribute_uuids(_settings(), ["attr-1", "attr-2"])

        assert result["stored"] == 4
        # created attributes have nothing stale to drop
        assert not mock_os.delete_by_query.called

    def test_rebuild_drops_existing_correlations_first(self):
        docs = [_attribute("attr-1")]
        mock_os = self._mock_os(docs, [])

        with patch(PATCH, return_value=mock_os), \
                patch(
                    "app.repositories.correlations.opensearch_helpers.bulk",
                    return_value=(0, []),
                ), \
                patch("app.repositories.correlations.tasks"):
            correlate_attribute_uuids(_settings(), ["attr-1"], rebuild=True)

        assert mock_os.delete_by_query.called

    def test_attributes_of_uncorrelated_events_are_skipped(self):
        docs = [_attribute("attr-1")]
        mock_os = self._mock_os(docs, [])
        mock_os.get.return_value = {"_source": {"disable_correlation": True}}

        with patch(PATCH, return_value=mock_os), \
                patch("app.repositories.correlations.tasks"):
            result = correlate_attribute_uuids(_settings(), ["attr-1"])

        assert result == {"stored": 0}
        mock_os.msearch.assert_not_called()
