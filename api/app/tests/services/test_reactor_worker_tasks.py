"""Unit tests for the reactor additions in ``app/worker/tasks.py``.

Covers the three payload helpers, the two new Celery tasks
(``reactor_dispatch`` and ``run_reactor_script``), and the wiring that
fires ``reactor_dispatch.delay`` from the existing ``handle_*`` tasks.
"""

from unittest.mock import MagicMock, patch

# Importing via the worker path resolves the runner ↔ context circular import
# that bites when tasks.py is loaded from a fresh module under test.
from app.worker import tasks as worker_tasks


EVENT_UUID = "11111111-1111-1111-1111-111111111111"
ATTR_UUID = "22222222-2222-2222-2222-222222222222"
OBJ_UUID = "33333333-3333-3333-3333-333333333333"


def _pydantic_like(data: dict):
    """Return a stand-in object whose ``model_dump(mode=...)`` returns ``data``."""
    obj = MagicMock()
    obj.model_dump.return_value = data
    return obj


# ──────────────────────────────────────────────────────────────────────────
# Payload helpers
# ──────────────────────────────────────────────────────────────────────────


class TestReactorEventPayload:
    def test_returns_uuid_only_when_event_missing(self):
        assert worker_tasks._reactor_event_payload(None, EVENT_UUID) == {
            "event_uuid": EVENT_UUID
        }

    def test_dumps_pydantic_model_and_overrides_uuid(self):
        os_event = _pydantic_like({"info": "phishing", "event_uuid": "stale"})
        result = worker_tasks._reactor_event_payload(os_event, EVENT_UUID)
        os_event.model_dump.assert_called_once_with(mode="json")
        assert result == {"info": "phishing", "event_uuid": EVENT_UUID}

    def test_falls_back_to_dict_for_plain_mappings(self):
        plain = {"info": "phishing"}
        result = worker_tasks._reactor_event_payload(plain, EVENT_UUID)
        assert result == {"info": "phishing", "event_uuid": EVENT_UUID}


class TestReactorAttributePayload:
    def test_handles_missing_attribute(self):
        result = worker_tasks._reactor_attribute_payload(
            None, ATTR_UUID, OBJ_UUID, EVENT_UUID
        )
        assert result == {
            "attribute_uuid": ATTR_UUID,
            "object_uuid": OBJ_UUID,
            "event_uuid": EVENT_UUID,
        }

    def test_dumps_pydantic_model(self):
        os_attr = _pydantic_like({"type": "ip-src", "value": "1.2.3.4"})
        result = worker_tasks._reactor_attribute_payload(
            os_attr, ATTR_UUID, OBJ_UUID, EVENT_UUID
        )
        assert result["type"] == "ip-src"
        assert result["value"] == "1.2.3.4"
        assert result["attribute_uuid"] == ATTR_UUID
        assert result["object_uuid"] == OBJ_UUID
        assert result["event_uuid"] == EVENT_UUID

    def test_propagates_none_event_and_object_uuids(self):
        os_attr = _pydantic_like({"type": "url"})
        result = worker_tasks._reactor_attribute_payload(os_attr, ATTR_UUID, None, None)
        assert result["object_uuid"] is None
        assert result["event_uuid"] is None


class TestReactorObjectPayload:
    def test_handles_missing_object(self):
        result = worker_tasks._reactor_object_payload(None, OBJ_UUID, EVENT_UUID)
        assert result == {"object_uuid": OBJ_UUID, "event_uuid": EVENT_UUID}

    def test_dumps_pydantic_model(self):
        os_obj = _pydantic_like({"name": "file", "meta_category": "file"})
        result = worker_tasks._reactor_object_payload(os_obj, OBJ_UUID, EVENT_UUID)
        assert result == {
            "name": "file",
            "meta_category": "file",
            "object_uuid": OBJ_UUID,
            "event_uuid": EVENT_UUID,
        }


# ──────────────────────────────────────────────────────────────────────────
# Celery tasks
# ──────────────────────────────────────────────────────────────────────────


class TestReactorDispatchTask:
    def test_invokes_repository_dispatch(self):
        payload = {"event_uuid": EVENT_UUID, "info": "phish"}
        with patch.object(
            worker_tasks.reactor_repository, "dispatch_triggered_scripts"
        ) as dispatch:
            assert worker_tasks.reactor_dispatch("event", "created", payload) is True
        dispatch.assert_called_once()
        args, _ = dispatch.call_args
        # (db, resource_type, action, payload)
        assert args[1:] == ("event", "created", payload)


class TestRunReactorScriptTask:
    def test_invokes_runner_with_run_id(self):
        with patch.object(worker_tasks.reactor_runner, "run_script") as run_script:
            assert worker_tasks.run_reactor_script(99) is True
        run_script.assert_called_once()
        args, _ = run_script.call_args
        # (db, run_id)
        assert args[1] == 99


# ──────────────────────────────────────────────────────────────────────────
# Dispatch wiring on the existing handle_* tasks
#
# The existing test in app/tests/api/test_reactor.py already covers
# handle_created_attribute. These tests cover the rest: events
# (created/updated/deleted/published/unpublished), attributes
# (updated/deleted), objects (created/updated/deleted), sightings, and
# correlations.
# ──────────────────────────────────────────────────────────────────────────


class TestEventHandlerWiring:
    def _patch_event_lookup(self, info: str = "phish"):
        """Patch the event opensearch lookup to return a stand-in model."""
        return patch.object(
            worker_tasks.events_repository,
            "get_event_from_opensearch",
            return_value=_pydantic_like({"info": info}),
        )

    def _patch_notifications(self):
        return patch.object(
            worker_tasks.notifications_repository,
            "create_event_notifications",
            return_value=None,
        )

    def test_handle_created_event_dispatches(self):
        with patch.object(worker_tasks.reactor_dispatch, "delay") as delay, \
                self._patch_event_lookup(), self._patch_notifications():
            worker_tasks.handle_created_event(EVENT_UUID)
        args, _ = delay.call_args
        assert args[0] == "event"
        assert args[1] == "created"
        assert args[2]["event_uuid"] == EVENT_UUID

    def test_handle_updated_event_dispatches(self):
        # handle_updated_event also touches OpenSearch directly to bump
        # ``timestamp`` — patch the client so no live call goes out.
        with patch.object(worker_tasks.reactor_dispatch, "delay") as delay, \
                patch.object(worker_tasks, "get_opensearch_client") as os_client, \
                self._patch_event_lookup(), self._patch_notifications():
            os_client.return_value = MagicMock()
            worker_tasks.handle_updated_event(EVENT_UUID)
        args, _ = delay.call_args
        assert args[:2] == ("event", "updated")
        assert args[2]["event_uuid"] == EVENT_UUID

    def test_handle_deleted_event_dispatches(self):
        with patch.object(worker_tasks.reactor_dispatch, "delay") as delay, \
                patch.object(worker_tasks, "delete_indexed_event"), \
                self._patch_event_lookup(), self._patch_notifications():
            worker_tasks.handle_deleted_event(EVENT_UUID)
        args, _ = delay.call_args
        assert args[:2] == ("event", "deleted")
        assert args[2]["event_uuid"] == EVENT_UUID

    def test_handle_published_event_dispatches(self):
        with patch.object(worker_tasks.reactor_dispatch, "delay") as delay, \
                self._patch_event_lookup(), self._patch_notifications():
            worker_tasks.handle_published_event(EVENT_UUID)
        assert delay.call_args.args[:2] == ("event", "published")

    def test_handle_unpublished_event_dispatches(self):
        with patch.object(worker_tasks.reactor_dispatch, "delay") as delay, \
                self._patch_event_lookup(), self._patch_notifications():
            worker_tasks.handle_unpublished_event(EVENT_UUID)
        assert delay.call_args.args[:2] == ("event", "unpublished")

    def test_skips_dispatch_when_event_missing(self):
        with patch.object(worker_tasks.reactor_dispatch, "delay") as delay, \
                patch.object(
                    worker_tasks.events_repository,
                    "get_event_from_opensearch",
                    return_value=None,
                ):
            worker_tasks.handle_created_event(EVENT_UUID)
        delay.assert_not_called()


class TestAttributeHandlerWiring:
    def _patch_attr_lookup(self):
        return patch.object(
            worker_tasks.attributes_repository,
            "get_attribute_from_opensearch",
            return_value=_pydantic_like({"type": "ip-src", "value": "1.2.3.4"}),
        )

    def _patch_notifications(self):
        return patch.object(
            worker_tasks.notifications_repository,
            "create_attribute_notifications",
            return_value=None,
        )

    def test_handle_updated_attribute_dispatches(self):
        with patch.object(worker_tasks.reactor_dispatch, "delay") as delay, \
                self._patch_attr_lookup(), self._patch_notifications():
            worker_tasks.handle_updated_attribute(ATTR_UUID, OBJ_UUID, EVENT_UUID)
        args, _ = delay.call_args
        assert args[:2] == ("attribute", "updated")
        assert args[2]["attribute_uuid"] == ATTR_UUID
        assert args[2]["object_uuid"] == OBJ_UUID
        assert args[2]["event_uuid"] == EVENT_UUID

    def test_handle_deleted_attribute_dispatches(self):
        # decrement_attribute_count fires when object_uuid is None and event is set,
        # so patch it out to keep the test pure.
        with patch.object(worker_tasks.reactor_dispatch, "delay") as delay, \
                patch.object(
                    worker_tasks.events_repository, "decrement_attribute_count"
                ), \
                self._patch_attr_lookup(), self._patch_notifications():
            worker_tasks.handle_deleted_attribute(ATTR_UUID, None, EVENT_UUID)
        args, _ = delay.call_args
        assert args[:2] == ("attribute", "deleted")
        assert args[2]["attribute_uuid"] == ATTR_UUID

    def test_skips_dispatch_when_attribute_missing(self):
        with patch.object(worker_tasks.reactor_dispatch, "delay") as delay, \
                patch.object(
                    worker_tasks.attributes_repository,
                    "get_attribute_from_opensearch",
                    return_value=None,
                ):
            worker_tasks.handle_updated_attribute(ATTR_UUID, None, None)
        delay.assert_not_called()


class TestObjectHandlerWiring:
    def _patch_obj_lookup(self):
        return patch.object(
            worker_tasks.objects_repository,
            "get_object_from_opensearch",
            return_value=_pydantic_like({"name": "file"}),
        )

    def _patch_notifications(self):
        return patch.object(
            worker_tasks.notifications_repository,
            "create_object_notifications",
            return_value=None,
        )

    def test_handle_created_object_dispatches(self):
        with patch.object(worker_tasks.reactor_dispatch, "delay") as delay, \
                patch.object(
                    worker_tasks.events_repository, "increment_object_count"
                ), \
                self._patch_obj_lookup(), self._patch_notifications():
            worker_tasks.handle_created_object(OBJ_UUID, EVENT_UUID)
        args, _ = delay.call_args
        assert args[:2] == ("object", "created")
        assert args[2]["object_uuid"] == OBJ_UUID
        assert args[2]["event_uuid"] == EVENT_UUID

    def test_handle_updated_object_dispatches(self):
        with patch.object(worker_tasks.reactor_dispatch, "delay") as delay, \
                self._patch_obj_lookup(), self._patch_notifications():
            worker_tasks.handle_updated_object(OBJ_UUID, EVENT_UUID)
        assert delay.call_args.args[:2] == ("object", "updated")

    def test_handle_deleted_object_dispatches(self):
        with patch.object(worker_tasks.reactor_dispatch, "delay") as delay, \
                patch.object(
                    worker_tasks.events_repository, "decrement_object_count"
                ), \
                self._patch_obj_lookup(), self._patch_notifications():
            worker_tasks.handle_deleted_object(OBJ_UUID, EVENT_UUID)
        assert delay.call_args.args[:2] == ("object", "deleted")

    def test_skips_dispatch_when_object_missing(self):
        with patch.object(worker_tasks.reactor_dispatch, "delay") as delay, \
                patch.object(
                    worker_tasks.objects_repository,
                    "get_object_from_opensearch",
                    return_value=None,
                ):
            worker_tasks.handle_updated_object(OBJ_UUID, EVENT_UUID)
        delay.assert_not_called()


class TestSightingHandlerWiring:
    def test_handle_created_sighting_dispatches(self):
        # search_events drives the surrounding loop; force an empty result so
        # we don't need full attribute fixtures.
        with patch.object(worker_tasks.reactor_dispatch, "delay") as delay, \
                patch.object(
                    worker_tasks.events_repository,
                    "search_events",
                    return_value={"total": 0, "results": []},
                ):
            worker_tasks.handle_created_sighting(
                value="1.2.3.4",
                organisation="ACME",
                sighting_type="positive",
                timestamp=1234567890.0,
            )
        delay.assert_called_once()
        args, _ = delay.call_args
        assert args[:2] == ("sighting", "created")
        assert args[2] == {
            "value": "1.2.3.4",
            "type": "positive",
            "organisation": "ACME",
            "timestamp": 1234567890.0,
        }


class TestCorrelationHandlerWiring:
    def test_handle_created_correlation_dispatches(self):
        with patch.object(worker_tasks.reactor_dispatch, "delay") as delay, \
                patch.object(
                    worker_tasks.notifications_repository,
                    "create_correlation_notifications",
                    return_value=None,
                ):
            worker_tasks.handle_created_correlation(
                source_attribute_uuid="src-attr",
                source_event_uuid="src-evt",
                target_event_uuid="tgt-evt",
                target_attribute_uuid="tgt-attr",
                target_attribute_type="ip-src",
                target_attribute_value="1.2.3.4",
            )
        args, _ = delay.call_args
        assert args[:2] == ("correlation", "created")
        assert args[2] == {
            "source_attribute_uuid": "src-attr",
            "source_event_uuid": "src-evt",
            "target_event_uuid": "tgt-evt",
            "target_attribute_uuid": "tgt-attr",
            "target_attribute_type": "ip-src",
            "target_attribute_value": "1.2.3.4",
        }
