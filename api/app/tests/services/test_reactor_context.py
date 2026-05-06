"""Unit tests for the reactor ``ctx`` SDK exposed to user scripts."""

import logging
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

# Import via the worker path first to fully resolve the runner ↔ context cycle
# before the direct context import below.
from app.repositories import reactor as _reactor_repository  # noqa: F401
from app.services.tech_lab.reactor import context as context_module
from app.services.tech_lab.reactor.context import (
    ReactorContext,
    ReactorWriteQuotaExceeded,
)


def _make_script(*, max_writes: int = 10, user_id: int = 7, script_id: int = 1, name: str = "demo"):
    script = MagicMock()
    script.id = script_id
    script.user_id = user_id
    script.name = name
    script.max_writes = max_writes
    return script


def _make_run(run_id: int = 42):
    run = MagicMock()
    run.id = run_id
    return run


def _make_ctx(*, max_writes: int = 10):
    db = MagicMock()
    script = _make_script(max_writes=max_writes)
    run = _make_run()
    return ReactorContext(db, script, run), db, script, run


class TestIntrospection:
    def test_exposes_run_and_script_ids(self):
        ctx, _, script, run = _make_ctx()
        assert ctx.run_id == run.id
        assert ctx.script_id == script.id


class TestReads:
    def test_get_event_returns_dict_from_pydantic_result(self):
        ctx, _, _, _ = _make_ctx()
        event_uuid = str(uuid4())
        fake = MagicMock()
        fake.model_dump.return_value = {"uuid": event_uuid, "info": "hello"}
        with patch.object(
            context_module.events_repository,
            "get_event_from_opensearch",
            return_value=fake,
        ) as get_event:
            result = ctx.get_event(event_uuid)
        get_event.assert_called_once()
        # arg should be a UUID instance derived from the string.
        (called_uuid,), _ = get_event.call_args
        assert str(called_uuid) == event_uuid
        fake.model_dump.assert_called_once_with(mode="json")
        assert result == {"uuid": event_uuid, "info": "hello"}

    def test_get_event_returns_none_when_missing(self):
        ctx, _, _, _ = _make_ctx()
        with patch.object(
            context_module.events_repository,
            "get_event_from_opensearch",
            return_value=None,
        ):
            assert ctx.get_event(str(uuid4())) is None

    def test_get_attribute_returns_dict(self):
        ctx, _, _, _ = _make_ctx()
        attr_uuid = str(uuid4())
        fake = MagicMock()
        fake.model_dump.return_value = {"uuid": attr_uuid, "type": "ip-src"}
        with patch.object(
            context_module.attributes_repository,
            "get_attribute_from_opensearch",
            return_value=fake,
        ):
            assert ctx.get_attribute(attr_uuid) == {"uuid": attr_uuid, "type": "ip-src"}

    def test_get_attribute_returns_none_when_missing(self):
        ctx, _, _, _ = _make_ctx()
        with patch.object(
            context_module.attributes_repository,
            "get_attribute_from_opensearch",
            return_value=None,
        ):
            assert ctx.get_attribute(str(uuid4())) is None

    def test_get_object_returns_dict(self):
        ctx, _, _, _ = _make_ctx()
        obj_uuid = str(uuid4())
        fake = MagicMock()
        fake.model_dump.return_value = {"uuid": obj_uuid, "name": "file"}
        with patch.object(
            context_module.objects_repository,
            "get_object_from_opensearch",
            return_value=fake,
        ):
            assert ctx.get_object(obj_uuid) == {"uuid": obj_uuid, "name": "file"}

    def test_get_object_returns_none_when_missing(self):
        ctx, _, _, _ = _make_ctx()
        with patch.object(
            context_module.objects_repository,
            "get_object_from_opensearch",
            return_value=None,
        ):
            assert ctx.get_object(str(uuid4())) is None

    def test_reads_do_not_count_against_quota(self):
        ctx, _, _, _ = _make_ctx(max_writes=0)
        with patch.object(
            context_module.events_repository,
            "get_event_from_opensearch",
            return_value=None,
        ), patch.object(
            context_module.attributes_repository,
            "get_attribute_from_opensearch",
            return_value=None,
        ), patch.object(
            context_module.objects_repository,
            "get_object_from_opensearch",
            return_value=None,
        ):
            # max_writes=0 would blow up immediately if reads counted as writes.
            ctx.get_event(str(uuid4()))
            ctx.get_attribute(str(uuid4()))
            ctx.get_object(str(uuid4()))


class TestAddAttribute:
    def test_creates_attribute_and_records_audit(self):
        ctx, db, script, run = _make_ctx()
        event_uuid = str(uuid4())
        attr_uuid = uuid4()
        created = MagicMock(uuid=attr_uuid)
        created.model_dump.return_value = {"uuid": str(attr_uuid), "type": "ip-src"}
        with patch.object(
            context_module.attributes_repository,
            "create_attribute",
            return_value=created,
        ) as create_attr, patch.object(
            context_module.audit, "record"
        ) as audit_record:
            result = ctx.add_attribute(
                event_uuid=event_uuid,
                type="ip-src",
                value="1.2.3.4",
                comment="see report",
                to_ids=True,
            )

        assert result == {"uuid": str(attr_uuid), "type": "ip-src"}
        # Schema should be built with the supplied fields including overrides.
        (passed_db, passed_schema), _ = create_attr.call_args
        assert passed_db is db
        assert str(passed_schema.event_uuid) == event_uuid
        assert passed_schema.type == "ip-src"
        assert passed_schema.value == "1.2.3.4"
        assert passed_schema.category == "External analysis"
        assert passed_schema.comment == "see report"
        assert passed_schema.to_ids is True

        audit_record.assert_called_once()
        kwargs = audit_record.call_args.kwargs
        assert kwargs["action"] == "reactor.write.attribute.create"
        assert kwargs["resource_type"] == "attribute"
        assert kwargs["actor_user_id"] == script.user_id
        assert kwargs["actor_type"] == "reactor_script"
        assert kwargs["actor_credential_id"] == script.id
        meta = kwargs["metadata"]
        assert meta["event_uuid"] == event_uuid
        assert meta["attribute_uuid"] == str(attr_uuid)
        assert meta["run_id"] == run.id
        assert meta["script_id"] == script.id
        assert meta["script_name"] == script.name

    def test_uses_default_category_when_not_provided(self):
        ctx, _, _, _ = _make_ctx()
        event_uuid = str(uuid4())
        created = MagicMock(uuid=uuid4())
        created.model_dump.return_value = {}
        with patch.object(
            context_module.attributes_repository,
            "create_attribute",
            return_value=created,
        ) as create_attr, patch.object(context_module.audit, "record"):
            ctx.add_attribute(event_uuid=event_uuid, type="ip-src", value="1.2.3.4")

        passed_schema = create_attr.call_args.args[1]
        assert passed_schema.category == "External analysis"
        assert passed_schema.comment is None
        assert passed_schema.to_ids is None

    def test_counts_against_write_quota(self):
        ctx, _, _, _ = _make_ctx(max_writes=1)
        created = MagicMock(uuid=uuid4())
        created.model_dump.return_value = {}
        with patch.object(
            context_module.attributes_repository,
            "create_attribute",
            return_value=created,
        ), patch.object(context_module.audit, "record"):
            ctx.add_attribute(event_uuid=str(uuid4()), type="ip-src", value="1.2.3.4")
            with pytest.raises(ReactorWriteQuotaExceeded):
                ctx.add_attribute(event_uuid=str(uuid4()), type="ip-src", value="5.6.7.8")


class TestTagEvent:
    def test_tags_event_when_found(self):
        ctx, db, script, _ = _make_ctx()
        event_uuid = str(uuid4())
        event = MagicMock()
        tag = MagicMock()
        with patch.object(
            context_module.events_repository,
            "get_event_from_opensearch",
            return_value=event,
        ), patch.object(
            context_module.tags_repository,
            "get_or_create_tag_by_name",
            return_value=tag,
        ) as get_tag, patch.object(
            context_module.tags_repository, "tag_event"
        ) as tag_event_call, patch.object(
            context_module.audit, "record"
        ) as audit_record:
            ctx.tag_event(event_uuid, "tlp:red")

        get_tag.assert_called_once_with(db, "tlp:red")
        tag_event_call.assert_called_once_with(db, event, tag)

        kwargs = audit_record.call_args.kwargs
        assert kwargs["action"] == "reactor.write.event.tag"
        assert kwargs["resource_type"] == "event"
        assert kwargs["actor_user_id"] == script.user_id
        assert kwargs["metadata"]["event_uuid"] == event_uuid
        assert kwargs["metadata"]["tag"] == "tlp:red"

    def test_raises_when_event_missing(self):
        ctx, _, _, _ = _make_ctx()
        with patch.object(
            context_module.events_repository,
            "get_event_from_opensearch",
            return_value=None,
        ), patch.object(context_module.audit, "record") as audit_record:
            with pytest.raises(ValueError, match="event .* not found"):
                ctx.tag_event(str(uuid4()), "tlp:red")
        audit_record.assert_not_called()

    def test_counts_against_quota_even_when_event_missing(self):
        # The write is "intent to mutate"; quota should be debited before lookup.
        ctx, _, _, _ = _make_ctx(max_writes=1)
        with patch.object(
            context_module.events_repository,
            "get_event_from_opensearch",
            return_value=None,
        ):
            with pytest.raises(ValueError):
                ctx.tag_event(str(uuid4()), "tlp:red")
            with pytest.raises(ReactorWriteQuotaExceeded):
                ctx.tag_event(str(uuid4()), "tlp:red")


class TestTagAttribute:
    def test_tags_attribute_when_found(self):
        ctx, db, script, _ = _make_ctx()
        attr_uuid = str(uuid4())
        attr = MagicMock()
        tag = MagicMock()
        with patch.object(
            context_module.attributes_repository,
            "get_attribute_from_opensearch",
            return_value=attr,
        ), patch.object(
            context_module.tags_repository,
            "get_or_create_tag_by_name",
            return_value=tag,
        ) as get_tag, patch.object(
            context_module.tags_repository, "tag_attribute"
        ) as tag_attr_call, patch.object(
            context_module.audit, "record"
        ) as audit_record:
            ctx.tag_attribute(attr_uuid, "osint:source-type=\"blog-post\"")

        get_tag.assert_called_once_with(db, "osint:source-type=\"blog-post\"")
        tag_attr_call.assert_called_once_with(db, attr, tag)

        kwargs = audit_record.call_args.kwargs
        assert kwargs["action"] == "reactor.write.attribute.tag"
        assert kwargs["resource_type"] == "attribute"
        assert kwargs["actor_user_id"] == script.user_id
        assert kwargs["metadata"]["attribute_uuid"] == attr_uuid
        assert kwargs["metadata"]["tag"] == "osint:source-type=\"blog-post\""

    def test_raises_when_attribute_missing(self):
        ctx, _, _, _ = _make_ctx()
        with patch.object(
            context_module.attributes_repository,
            "get_attribute_from_opensearch",
            return_value=None,
        ), patch.object(context_module.audit, "record") as audit_record:
            with pytest.raises(ValueError, match="attribute .* not found"):
                ctx.tag_attribute(str(uuid4()), "tlp:red")
        audit_record.assert_not_called()


class TestEnrich:
    def test_runs_module_and_audits(self):
        ctx, db, script, _ = _make_ctx()
        with patch.object(
            context_module.modules_repository,
            "query_module",
            return_value={"results": [{"types": ["domain"], "values": ["evil.tld"]}]},
        ) as query_module, patch.object(
            context_module.audit, "record"
        ) as audit_record:
            result = ctx.enrich(
                value="1.2.3.4",
                type="ip-src",
                module="dns",
                config={"resolver": "1.1.1.1"},
            )

        assert result == {"results": [{"types": ["domain"], "values": ["evil.tld"]}]}
        (passed_db, passed_query), _ = query_module.call_args
        assert passed_db is db
        assert passed_query.module == "dns"
        assert passed_query.attribute == {"type": "ip-src", "value": "1.2.3.4", "uuid": ""}
        assert passed_query.config == {"resolver": "1.1.1.1"}

        kwargs = audit_record.call_args.kwargs
        assert kwargs["action"] == "reactor.write.module.enrich"
        assert kwargs["resource_type"] == "module"
        assert kwargs["actor_user_id"] == script.user_id
        assert kwargs["metadata"]["module"] == "dns"
        assert kwargs["metadata"]["type"] == "ip-src"
        assert kwargs["metadata"]["value"] == "1.2.3.4"

    def test_records_error_audit_and_reraises_on_failure(self):
        ctx, _, _, _ = _make_ctx()
        boom = RuntimeError("upstream down")
        with patch.object(
            context_module.modules_repository, "query_module", side_effect=boom
        ), patch.object(context_module.audit, "record") as audit_record:
            with pytest.raises(RuntimeError, match="upstream down"):
                ctx.enrich(value="1.2.3.4", type="ip-src", module="dns")

        audit_record.assert_called_once()
        kwargs = audit_record.call_args.kwargs
        assert kwargs["action"] == "reactor.write.module.enrich.error"
        assert kwargs["metadata"]["error"] == "upstream down"
        assert kwargs["metadata"]["module"] == "dns"

    def test_counts_against_quota(self):
        ctx, _, _, _ = _make_ctx(max_writes=0)
        with patch.object(
            context_module.modules_repository, "query_module", return_value={}
        ):
            with pytest.raises(ReactorWriteQuotaExceeded):
                ctx.enrich(value="1.2.3.4", type="ip-src", module="dns")


class TestListModules:
    def test_shapes_module_metadata(self):
        ctx, db, _, _ = _make_ctx()
        m = MagicMock()
        m.model_dump.return_value = {
            "name": "dns",
            "type": "expansion",
            "enabled": True,
            "misp_attributes": {"input": ["ip-src"], "output": ["domain"]},
            "meta": {"description": "Resolve via DNS"},
        }
        with patch.object(
            context_module.modules_repository, "get_modules", return_value=[m]
        ) as get_modules:
            result = ctx.list_modules()

        get_modules.assert_called_once_with(db, enabled=True)
        assert result == [
            {
                "name": "dns",
                "type": "expansion",
                "enabled": True,
                "input": ["ip-src"],
                "output": ["domain"],
                "description": "Resolve via DNS",
            }
        ]

    def test_passes_none_when_enabled_only_false(self):
        ctx, db, _, _ = _make_ctx()
        with patch.object(
            context_module.modules_repository, "get_modules", return_value=[]
        ) as get_modules:
            assert ctx.list_modules(enabled_only=False) == []
        get_modules.assert_called_once_with(db, enabled=None)

    def test_handles_missing_optional_fields(self):
        ctx, _, _, _ = _make_ctx()
        m = MagicMock()
        m.model_dump.return_value = {"name": "x", "type": "expansion", "enabled": False}
        with patch.object(
            context_module.modules_repository, "get_modules", return_value=[m]
        ):
            result = ctx.list_modules()
        assert result == [
            {
                "name": "x",
                "type": "expansion",
                "enabled": False,
                "input": [],
                "output": [],
                "description": None,
            }
        ]

    def test_does_not_count_against_quota(self):
        ctx, _, _, _ = _make_ctx(max_writes=0)
        with patch.object(
            context_module.modules_repository, "get_modules", return_value=[]
        ):
            ctx.list_modules()


class TestLog:
    def test_prints_and_logs(self, capsys, caplog):
        ctx, _, script, run = _make_ctx()
        with caplog.at_level(logging.INFO, logger=context_module.logger.name):
            ctx.log("hello", 42, {"k": "v"})
        out = capsys.readouterr().out
        assert "hello 42 {'k': 'v'}" in out
        assert any(
            f"reactor[{script.id}/run={run.id}] hello 42" in r.message
            for r in caplog.records
        )


class TestQuota:
    def test_account_write_increments_and_caps(self):
        ctx, _, _, _ = _make_ctx(max_writes=2)
        ctx._account_write()
        ctx._account_write()
        with pytest.raises(ReactorWriteQuotaExceeded) as exc:
            ctx._account_write()
        assert "max_writes=2" in str(exc.value)

    def test_zero_quota_blocks_first_write(self):
        ctx, _, _, _ = _make_ctx(max_writes=0)
        with pytest.raises(ReactorWriteQuotaExceeded):
            ctx._account_write()
