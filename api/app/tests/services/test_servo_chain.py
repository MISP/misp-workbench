"""Unit tests for the servo -> OpenSearch pipeline compiler.

OpenSearch is mocked throughout: the chain builder is pure logic over the DB
rows, and `sync` only needs to be observed through the calls it makes.
"""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from opensearchpy.exceptions import NotFoundError, RequestError

from app.models import servo as servo_models
from app.services.tech_lab.servos import chain


def make_servo(slug, position=0, enabled=True, processors=None, servo_id=None):
    return servo_models.Servo(
        id=servo_id,
        user_id=1,
        name=slug,
        slug=slug,
        description=None,
        processors=processors or [{"set": {"field": "a", "value": "b"}}],
        target_index=chain.TARGET_INDEX,
        enabled=enabled,
        position=position,
        created_at=datetime.now(timezone.utc),
    )


class FakeSession:
    """Just enough Session to satisfy the chain module's `select(...)` calls."""

    def __init__(self, servos):
        self._servos = servos
        self.committed = False

    def scalars(self, statement):
        # The two queries differ only by the enabled filter; reading the
        # compiled SQL keeps this honest without a real DB.
        sql = str(statement)
        rows = self._servos
        if "enabled IS true" in sql or "enabled IS 1" in sql:
            rows = [s for s in rows if s.enabled]
        result = MagicMock()
        result.all.return_value = sorted(rows, key=lambda s: (s.position, s.id or 0))
        return result

    def commit(self):
        self.committed = True


class TestBuildChain:
    def test_orders_by_position(self):
        db = FakeSession(
            [
                make_servo("b", position=2, servo_id=2),
                make_servo("a", position=1, servo_id=1),
            ]
        )
        body = chain.build_chain(db)
        names = [p["pipeline"]["name"] for p in body["processors"]]
        assert names == ["servo_a", "servo_b"]

    def test_disabled_servos_are_left_out(self):
        db = FakeSession(
            [
                make_servo("on", position=0, servo_id=1),
                make_servo("off", position=1, enabled=False, servo_id=2),
            ]
        )
        names = [p["pipeline"]["name"] for p in chain.build_chain(db)["processors"]]
        assert names == ["servo_on"]

    def test_every_entry_carries_an_on_failure_handler(self):
        # A servo that throws must not stop the attribute from being indexed.
        db = FakeSession([make_servo("risky", servo_id=1)])
        entry = chain.build_chain(db)["processors"][0]["pipeline"]
        assert entry["on_failure"][0]["append"]["field"] == chain.SERVO_ERRORS_FIELD
        assert "servo_risky" in entry["on_failure"][0]["append"]["value"]
        assert "_ingest.on_failure_message" in entry["on_failure"][0]["append"]["value"]

    def test_empty_when_nothing_is_enabled(self):
        assert chain.build_chain(FakeSession([]))["processors"] == []


class TestCompilePipeline:
    def test_uses_the_servo_description(self):
        db_servo = make_servo("x", servo_id=1)
        db_servo.description = "my description"
        assert chain.compile_pipeline(db_servo)["description"] == "my description"

    def test_falls_back_to_a_generated_description(self):
        body = chain.compile_pipeline(make_servo("x", servo_id=1))
        assert "x" in body["description"]


class TestSync:
    def test_applies_enabled_servos_and_rewrites_the_chain(self):
        db = FakeSession(
            [make_servo("a", servo_id=1), make_servo("b", position=1, servo_id=2)]
        )
        with patch.object(chain, "OpenSearchClient") as client:
            client.ingest.get_pipeline.return_value = {}
            result = chain.sync(db)

        applied = [c.kwargs["id"] for c in client.ingest.put_pipeline.call_args_list]
        assert applied == ["servo_a", "servo_b", chain.CHAIN_PIPELINE]
        assert result["applied"] == ["servo_a", "servo_b"]
        assert db.committed

    def test_deletes_the_pipeline_of_a_disabled_servo(self):
        db = FakeSession([make_servo("gone", enabled=False, servo_id=1)])
        with patch.object(chain, "OpenSearchClient") as client:
            client.ingest.get_pipeline.return_value = {"servo_gone": {"processors": []}}
            result = chain.sync(db)

        client.ingest.delete_pipeline.assert_called_once_with(id="servo_gone")
        assert result["removed"] == ["servo_gone"]

    def test_leaves_servo_prefixed_pipelines_it_does_not_own_alone(self):
        # Someone else's servo_* pipeline is not ours to delete.
        db = FakeSession([])
        with patch.object(chain, "OpenSearchClient") as client:
            client.ingest.get_pipeline.return_value = {
                "servo_not_ours": {"processors": []}
            }
            result = chain.sync(db)

        client.ingest.delete_pipeline.assert_not_called()
        assert result["removed"] == []

    def test_sync_quietly_swallows_an_opensearch_failure(self):
        db = FakeSession([make_servo("a", servo_id=1)])
        with patch.object(chain, "OpenSearchClient") as client:
            client.ingest.put_pipeline.side_effect = RuntimeError("cluster down")
            chain.sync_quietly(db)  # must not raise: the API still has to boot


class TestClassify:
    @pytest.mark.parametrize(
        "name,expected",
        [
            ("misp-attributes_default", "system"),
            ("misp-attributes_servos", "system"),
            ("servo_url_parts", "servo"),
            ("logstash-pipeline", "external"),
        ],
    )
    def test_classify(self, name, expected):
        assert chain.classify(name) == expected


class TestProcessorTypes:
    def test_names_the_delegated_pipeline(self):
        definition = {
            "processors": [{"pipeline": {"name": "misp-attributes_ip_geoip"}}]
        }
        assert chain.processor_types(definition) == [
            "pipeline:misp-attributes_ip_geoip"
        ]

    def test_deduplicates_but_keeps_order(self):
        definition = {
            "processors": [{"set": {}}, {"grok": {}}, {"set": {}}, {"convert": {}}]
        }
        assert chain.processor_types(definition) == ["set", "grok", "convert"]


class TestSimulate:
    def test_a_rejected_pipeline_comes_back_as_an_error_not_an_exception(self):
        error = RequestError(
            400, "parse_exception", {"error": {"reason": "No processor type exists"}}
        )
        with patch.object(chain, "OpenSearchClient") as client:
            client.ingest.simulate.side_effect = error
            ok, docs, reason = chain.simulate([{"nope": {}}], [{"value": "x"}])

        assert ok is False
        assert docs == []
        assert reason == "No processor type exists"

    def test_returns_the_transformed_sources(self):
        with patch.object(chain, "OpenSearchClient") as client:
            client.ingest.simulate.return_value = {
                "docs": [{"doc": {"_source": {"value": "x", "expanded": {"a": 1}}}}]
            }
            ok, docs, reason = chain.simulate([{"set": {}}], [{"value": "x"}])

        assert ok is True
        assert docs == [{"value": "x", "expanded": {"a": 1}}]
        assert reason is None

    def test_a_per_document_error_fails_the_simulation(self):
        with patch.object(chain, "OpenSearchClient") as client:
            client.ingest.simulate.return_value = {
                "docs": [{"error": {"reason": "field [value] not present"}}]
            }
            ok, docs, reason = chain.simulate([{"set": {}}], [{}])

        assert ok is False
        assert "not present" in reason


class TestTemplates:
    def test_shipped_templates_are_well_formed(self):
        templates = chain.load_templates()
        assert {t["slug"] for t in templates} >= {
            "url_parts",
            "canonical_value",
            "dedup_fingerprint",
            "timestamp_normalization",
        }
        for template in templates:
            assert template["processors"], template["slug"]
            # The picker shows `summary`; it has to stay short enough to sit
            # on one line in a dropdown item.
            assert template["summary"], template["slug"]
            assert len(template["summary"]) <= 60, template["slug"]
            assert template["description"], template["slug"]
            for processor in template["processors"]:
                assert len(processor) == 1, template["slug"]


class TestDropsDocuments:
    @pytest.mark.parametrize(
        "processors,expected",
        [
            ([{"set": {"field": "a", "value": "b"}}], False),
            ([], False),
            ([{"drop": {}}], True),
            ([{"drop": {"if": "ctx.type == 'md5'"}}], True),
            # A drop can hide inside a nested processor list.
            ([{"foreach": {"field": "x", "processor": {"drop": {}}}}], True),
            ([{"grok": {"field": "v", "on_failure": [{"drop": {}}]}}], True),
            ([{"set": {"field": "a", "value": "b"}}, {"drop": {}}], True),
        ],
    )
    def test_detects_a_drop_anywhere(self, processors, expected):
        assert chain.drops_documents(processors) is expected


class TestErrorSummary:
    def _response(self, buckets):
        return {"aggregations": {"servo_errors": {"buckets": buckets}}}

    def test_groups_messages_under_their_servo(self):
        with patch.object(chain, "OpenSearchClient") as client:
            client.search.return_value = self._response(
                [
                    {"key": "servo_a: boom", "doc_count": 3},
                    {"key": "servo_a: other failure", "doc_count": 1},
                    {"key": "servo_b: nope", "doc_count": 2},
                ]
            )
            summary = chain.error_summary()

        assert summary["servo_a"]["count"] == 4
        assert summary["servo_b"]["count"] == 2
        # Most frequent message first, so the badge tooltip leads with it.
        assert [m["message"] for m in summary["servo_a"]["messages"]] == [
            "boom",
            "other failure",
        ]

    def test_missing_index_is_not_an_error(self):
        # A fresh install has no documents; the servo list must still render.
        with patch.object(chain, "OpenSearchClient") as client:
            client.search.side_effect = NotFoundError(404, "index_not_found", {})
            assert chain.error_summary() == {}


class TestBackfill:
    def test_no_filter_means_every_attribute(self):
        assert chain._backfill_query(None) == {"query": {"match_all": {}}}
        assert chain._backfill_query("   ") == {"query": {"match_all": {}}}

    def test_a_filter_becomes_a_query_string(self):
        assert chain._backfill_query("type:url") == {
            "query": {"query_string": {"query": "type:url"}}
        }

    def test_start_names_the_reset_pipeline_and_does_not_block(self):
        with patch.object(chain, "OpenSearchClient") as client:
            client.update_by_query.return_value = {"task": "node:42"}
            task_id = chain.start_backfill("type:url")

        assert task_id == "node:42"
        params = client.update_by_query.call_args.kwargs["params"]
        # The reset pipeline runs before the index's final pipeline and clears
        # the append-only error field, so a run reports only its own failures.
        assert params["pipeline"] == chain.RESET_PIPELINE
        # A rewrite of a large index must not hold the request open.
        assert params["wait_for_completion"] == "false"
        # One bad document must not abort the rest of the run.
        assert params["conflicts"] == "proceed"

    def test_status_while_running_reads_the_task_counters(self):
        with patch.object(chain, "OpenSearchClient") as client:
            client.tasks.get.return_value = {
                "completed": False,
                "task": {"status": {"total": 100, "updated": 40}},
            }
            status = chain.backfill_status("node:42")

        assert status["completed"] is False
        assert (status["total"], status["updated"]) == (100, 40)

    def test_status_when_done_reads_the_response(self):
        with patch.object(chain, "OpenSearchClient") as client:
            client.tasks.get.return_value = {
                "completed": True,
                "response": {"total": 100, "updated": 100, "failures": []},
            }
            status = chain.backfill_status("node:42")

        assert status["completed"] is True
        assert status["updated"] == 100
        assert status["failures"] == []

    def test_status_surfaces_failures(self):
        with patch.object(chain, "OpenSearchClient") as client:
            client.tasks.get.return_value = {
                "completed": True,
                "response": {
                    "total": 5,
                    "updated": 3,
                    "failures": [{"cause": "mapper_parsing_exception"}],
                },
            }
            status = chain.backfill_status("node:42")

        assert len(status["failures"]) == 1

    def test_a_forgotten_task_completes_rather_than_polling_for_ever(self):
        with patch.object(chain, "OpenSearchClient") as client:
            client.tasks.get.side_effect = NotFoundError(404, "not_found", {})
            status = chain.backfill_status("node:42")

        assert status["completed"] is True
        assert "no longer knows this task" in status["error"]
