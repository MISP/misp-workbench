"""Unit tests for the live correlation wiring in ``app/worker/tasks.py``.

Covers the ``correlate_attribute`` task itself and the wiring that fires it
from the attribute ``handle_*`` tasks.
"""

from unittest.mock import MagicMock, patch

import pytest
from app.repositories import attributes as attributes_repository
from app.schemas import attribute as attribute_schemas
from app.worker import tasks as worker_tasks

ATTR_UUID = "22222222-2222-2222-2222-222222222222"
OBJ_UUID = "33333333-3333-3333-3333-333333333333"
EVENT_UUID = "11111111-1111-1111-1111-111111111111"


def _pydantic_like(data: dict):
    obj = MagicMock()
    obj.model_dump.return_value = data
    return obj


@pytest.fixture(autouse=True)
def _no_reactor_dispatch():
    """The reactor gate is irrelevant here, keep it closed."""
    with patch.object(
        worker_tasks.reactor_repository, "has_active_subscriber", return_value=False
    ):
        yield


def _patch_settings(correlate_on_change=True):
    settings = MagicMock()
    settings.get_value.side_effect = lambda key, default: (
        correlate_on_change if key == "correlations.correlateOnChange" else default
    )
    return patch.object(worker_tasks, "get_runtime_settings", return_value=settings)


class TestCorrelateAttributeTask:
    def test_delegates_to_repository(self):
        with _patch_settings(), patch.object(
            worker_tasks.correlations_repository,
            "correlate_attribute",
            return_value={"stored": 4},
        ) as correlate:
            assert worker_tasks.correlate_attribute(ATTR_UUID) is True

        assert correlate.call_args.args[1] == ATTR_UUID

    def test_skipped_when_disabled_by_runtime_setting(self):
        with _patch_settings(correlate_on_change=False), patch.object(
            worker_tasks.correlations_repository, "correlate_attribute"
        ) as correlate:
            assert worker_tasks.correlate_attribute(ATTR_UUID) is True

        correlate.assert_not_called()


class TestCorrelateAttributesTask:
    UUIDS = ["attr-1", "attr-2"]

    def test_delegates_to_repository(self):
        with _patch_settings(), patch.object(
            worker_tasks.correlations_repository,
            "correlate_attribute_uuids",
            return_value={"stored": 8},
        ) as correlate:
            assert worker_tasks.correlate_attributes(self.UUIDS, True) is True

        assert correlate.call_args.args[1] == self.UUIDS
        assert correlate.call_args.kwargs["rebuild"] is True

    def test_skipped_when_disabled_by_runtime_setting(self):
        with _patch_settings(correlate_on_change=False), patch.object(
            worker_tasks.correlations_repository, "correlate_attribute_uuids"
        ) as correlate:
            assert worker_tasks.correlate_attributes(self.UUIDS) is True

        correlate.assert_not_called()


class TestEnqueueDeferredCorrelations:
    def test_created_and_updated_are_enqueued_separately(self):
        batch = {"created": ["attr-1"], "updated": ["attr-2"]}

        with patch.object(worker_tasks.correlate_attributes, "delay") as delay:
            worker_tasks.enqueue_deferred_correlations(batch)

        assert delay.call_args_list[0].args == (["attr-1"], False)
        assert delay.call_args_list[1].args == (["attr-2"], True)

    def test_large_batches_are_chunked(self):
        batch = {"created": [f"attr-{n}" for n in range(5)], "updated": []}

        with patch.object(worker_tasks.correlate_attributes, "delay") as delay, \
                patch.object(worker_tasks, "CORRELATION_BATCH_SIZE", 2):
            worker_tasks.enqueue_deferred_correlations(batch)

        assert [len(call.args[0]) for call in delay.call_args_list] == [2, 2, 1]

    def test_nothing_collected_enqueues_nothing(self):
        with patch.object(worker_tasks.correlate_attributes, "delay") as delay:
            worker_tasks.enqueue_deferred_correlations({"created": [], "updated": []})

        delay.assert_not_called()


class TestHandleCreatedCorrelations:
    CORRELATION = {
        "source_attribute_uuid": "src-attr",
        "source_event_uuid": "src-evt",
        "target_event_uuid": "tgt-evt",
        "target_attribute_uuid": "tgt-attr",
        "target_attribute_type": "ip-src",
        "target_attribute_value": "1.2.3.4",
    }

    def test_notifies_the_whole_batch_from_one_session(self):
        correlations = [self.CORRELATION, {**self.CORRELATION, "target_attribute_uuid": "other"}]

        with patch.object(
            worker_tasks.notifications_repository,
            "create_correlation_notifications_bulk",
            return_value=None,
        ) as notify:
            assert worker_tasks.handle_created_correlations(correlations) is True

        notify.assert_called_once()
        assert notify.call_args.args[2] == correlations

    def test_empty_batch_is_a_noop(self):
        with patch.object(
            worker_tasks.notifications_repository,
            "create_correlation_notifications_bulk",
        ) as notify:
            assert worker_tasks.handle_created_correlations([]) is True

        notify.assert_not_called()

    def test_single_correlation_handler_goes_through_the_batch_path(self):
        with patch.object(
            worker_tasks.notifications_repository,
            "create_correlation_notifications_bulk",
            return_value=None,
        ) as notify:
            worker_tasks.handle_created_correlation(**{
                "source_attribute_uuid": "src-attr",
                "source_event_uuid": "src-evt",
                "target_event_uuid": "tgt-evt",
                "target_attribute_uuid": "tgt-attr",
                "target_attribute_type": "ip-src",
                "target_attribute_value": "1.2.3.4",
            })

        assert notify.call_args.args[2] == [self.CORRELATION]


class TestCorrelationWiring:
    def _patch_attr_lookup(self):
        return patch.object(
            worker_tasks.attributes_repository,
            "get_attribute_from_opensearch",
            return_value=_pydantic_like({"type": "ip-src", "value": "1.2.3.4"}),
        )

    def _patch_missing_attr_lookup(self):
        return patch.object(
            worker_tasks.attributes_repository,
            "get_attribute_from_opensearch",
            return_value=None,
        )

    def _patch_notifications(self):
        return patch.object(
            worker_tasks.notifications_repository,
            "create_attribute_notifications",
            return_value=None,
        )

    def _patch_counts(self):
        return patch.object(worker_tasks.events_repository, "increment_attribute_count")

    def test_created_attribute_is_correlated(self):
        with patch.object(worker_tasks.correlate_attribute, "delay") as delay, \
                self._patch_counts(), \
                self._patch_attr_lookup(), self._patch_notifications():
            worker_tasks.handle_created_attribute(ATTR_UUID, OBJ_UUID, EVENT_UUID)

        delay.assert_called_once_with(ATTR_UUID)

    def test_created_attribute_skips_correlation_for_a_bulk_ingest(self):
        with patch.object(worker_tasks.correlate_attribute, "delay") as delay, \
                self._patch_counts(), \
                self._patch_attr_lookup(), self._patch_notifications():
            worker_tasks.handle_created_attribute(
                ATTR_UUID, OBJ_UUID, EVENT_UUID, bulk=True
            )

        delay.assert_not_called()

    def test_missing_attribute_is_not_correlated(self):
        with patch.object(worker_tasks.correlate_attribute, "delay") as delay, \
                self._patch_missing_attr_lookup(), \
                self._patch_notifications():
            worker_tasks.handle_created_attribute(ATTR_UUID, OBJ_UUID, None)

        delay.assert_not_called()

    def test_created_attribute_counts_towards_its_event(self):
        with patch.object(worker_tasks.correlate_attribute, "delay"), \
                self._patch_counts() as increment, \
                self._patch_attr_lookup(), self._patch_notifications():
            worker_tasks.handle_created_attribute(ATTR_UUID, OBJ_UUID, EVENT_UUID)

        # an attribute inside an object counts too, as in MISP
        increment.assert_called_once()
        assert increment.call_args.args[1] == EVENT_UUID

    def test_bulk_created_attribute_is_not_counted(self):
        with patch.object(worker_tasks.correlate_attribute, "delay"), \
                self._patch_counts() as increment, \
                self._patch_attr_lookup(), self._patch_notifications():
            worker_tasks.handle_created_attribute(
                ATTR_UUID, OBJ_UUID, EVENT_UUID, bulk=True
            )

        increment.assert_not_called()

    def test_deleted_object_attribute_is_uncounted(self):
        with patch.object(
            worker_tasks.correlations_repository, "delete_attribute_correlations"
        ), patch.object(
            worker_tasks.events_repository, "decrement_attribute_count"
        ) as decrement, \
                self._patch_attr_lookup(), self._patch_notifications():
            worker_tasks.handle_deleted_attribute(ATTR_UUID, OBJ_UUID, EVENT_UUID)

        decrement.assert_called_once()

    def test_updated_attribute_is_recorrelated(self):
        with patch.object(worker_tasks.correlate_attribute, "delay") as delay, \
                self._patch_attr_lookup(), self._patch_notifications():
            worker_tasks.handle_updated_attribute(
                ATTR_UUID, OBJ_UUID, EVENT_UUID, recorrelate=True
            )

        delay.assert_called_once_with(ATTR_UUID)

    def test_updated_attribute_skips_recorrelation_when_value_unchanged(self):
        with patch.object(worker_tasks.correlate_attribute, "delay") as delay, \
                self._patch_attr_lookup(), self._patch_notifications():
            worker_tasks.handle_updated_attribute(
                ATTR_UUID, OBJ_UUID, EVENT_UUID, recorrelate=False
            )

        delay.assert_not_called()

    def test_deleted_attribute_drops_its_correlations(self):
        with patch.object(
            worker_tasks.correlations_repository, "delete_attribute_correlations"
        ) as delete, \
                patch.object(worker_tasks.events_repository, "decrement_attribute_count"), \
                self._patch_attr_lookup(), self._patch_notifications():
            worker_tasks.handle_deleted_attribute(ATTR_UUID, None, EVENT_UUID)

        delete.assert_called_once_with(ATTR_UUID)


class TestBulkIngestDefersCorrelation:
    """The ingest paths must hand their attributes to one batched task."""

    def _create_two_attributes(self):
        """Create attributes the way an ingest does, inside whatever context is active."""
        with patch("app.repositories.attributes.get_opensearch_client"), \
                patch("app.repositories.attributes.tasks"):
            for value in ("1.2.3.4", "5.6.7.8"):
                attributes_repository.create_attribute(
                    MagicMock(),
                    attribute_schemas.AttributeCreate(
                        event_uuid=EVENT_UUID,
                        category="Network activity",
                        type="ip-src",
                        value=value,
                    ),
                )

    def test_fetch_feed_event_enqueues_a_single_batch(self):
        def process_feed_event(db, event_uuid, feed, user):
            self._create_two_attributes()
            return {"result": "success"}

        with patch.object(worker_tasks, "Session"), \
                patch.object(worker_tasks.users_repository, "get_user_by_id"), \
                patch.object(worker_tasks.feeds_repository, "get_feed_by_id"), \
                patch.object(
                    worker_tasks.feeds_repository,
                    "process_feed_event",
                    side_effect=process_feed_event,
                ), \
                patch.object(worker_tasks.correlate_attributes, "delay") as delay:
            worker_tasks.fetch_feed_event(EVENT_UUID, 1, 1)

        delay.assert_called_once()
        attribute_uuids, rebuild = delay.call_args.args
        assert len(attribute_uuids) == 2
        assert rebuild is False

    def test_pull_event_enqueues_a_single_batch(self):
        def pull_event_by_uuid(db, event_uuid, server, user, settings):
            self._create_two_attributes()
            return None

        with patch.object(worker_tasks, "Session"), \
                patch.object(worker_tasks.users_repository, "get_user_by_id"), \
                patch.object(worker_tasks.servers_repository, "get_server_by_id"), \
                patch.object(
                    worker_tasks.servers_repository,
                    "pull_event_by_uuid",
                    side_effect=pull_event_by_uuid,
                ), \
                patch.object(worker_tasks.correlate_attributes, "delay") as delay:
            worker_tasks.pull_event_by_uuid(EVENT_UUID, 1, 1)

        delay.assert_called_once()
        assert len(delay.call_args.args[0]) == 2
