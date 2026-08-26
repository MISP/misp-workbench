"""Unit tests for the correlation wiring in ``app/repositories/attributes.py``."""

from unittest.mock import MagicMock, patch

from app.repositories import attributes as attributes_repository
from app.schemas import attribute as attribute_schemas

EVENT_UUID = "11111111-1111-1111-1111-111111111111"
ATTR_UUID = "22222222-2222-2222-2222-222222222222"

OS_PATCH = "app.repositories.attributes.get_opensearch_client"
TASKS_PATCH = "app.repositories.attributes.tasks"


def _attribute_create(**overrides):
    values = {
        "event_uuid": EVENT_UUID,
        "category": "Network activity",
        "type": "ip-src",
        "value": "1.2.3.4",
    }
    values.update(overrides)
    return attribute_schemas.AttributeCreate(**values)


def _indexed_attribute(**overrides):
    values = {
        "uuid": ATTR_UUID,
        "event_uuid": EVENT_UUID,
        "category": "Network activity",
        "type": "ip-src",
        "value": "1.2.3.4",
        "timestamp": 1,
    }
    values.update(overrides)
    return attribute_schemas.Attribute(**values)


class TestCreateAttributeCorrelation:
    def test_not_marked_bulk_by_default(self):
        with patch(OS_PATCH, return_value=MagicMock()), \
                patch(TASKS_PATCH) as tasks:
            attributes_repository.create_attribute(MagicMock(), _attribute_create())

        args = tasks.handle_created_attribute.delay.call_args.args
        assert args[3] is False

    def test_defers_inside_a_bulk_ingest(self):
        with patch(OS_PATCH, return_value=MagicMock()), \
                patch(TASKS_PATCH) as tasks, \
                attributes_repository.bulk_ingest() as batch:
            created = attributes_repository.create_attribute(
                MagicMock(), _attribute_create()
            )

        assert batch["created"] == [str(created.uuid)]
        assert batch["updated"] == []
        # the handler still runs for notifications, it just leaves correlating
        # and counting to the ingest
        args = tasks.handle_created_attribute.delay.call_args.args
        assert args[3] is True

    def test_the_context_does_not_leak(self):
        with patch(OS_PATCH, return_value=MagicMock()), patch(TASKS_PATCH):
            with attributes_repository.bulk_ingest():
                pass

        with patch(OS_PATCH, return_value=MagicMock()), \
                patch(TASKS_PATCH) as tasks:
            attributes_repository.create_attribute(MagicMock(), _attribute_create())

        assert tasks.handle_created_attribute.delay.call_args.args[3] is False


class TestUpdateAttributeCorrelation:
    def _patch_lookup(self, attribute=None):
        return patch.object(
            attributes_repository,
            "get_attribute_from_opensearch",
            return_value=attribute or _indexed_attribute(),
        )

    def test_value_change_triggers_recorrelation(self):
        patch_update = attribute_schemas.AttributeUpdate(value="5.6.7.8")

        with patch(OS_PATCH, return_value=MagicMock()), \
                patch(TASKS_PATCH) as tasks, self._patch_lookup():
            attributes_repository.update_attribute(
                MagicMock(), ATTR_UUID, patch_update
            )

        args = tasks.handle_updated_attribute.delay.call_args.args
        assert args[3] is True

    def test_unrelated_change_does_not_recorrelate(self):
        patch_update = attribute_schemas.AttributeUpdate(comment="just a note")

        with patch(OS_PATCH, return_value=MagicMock()), \
                patch(TASKS_PATCH) as tasks, self._patch_lookup():
            attributes_repository.update_attribute(
                MagicMock(), ATTR_UUID, patch_update
            )

        args = tasks.handle_updated_attribute.delay.call_args.args
        assert args[3] is False

    def test_defers_inside_a_bulk_ingest(self):
        patch_update = attribute_schemas.AttributeUpdate(value="5.6.7.8")

        with patch(OS_PATCH, return_value=MagicMock()), \
                patch(TASKS_PATCH) as tasks, self._patch_lookup(), \
                attributes_repository.bulk_ingest() as batch:
            attributes_repository.update_attribute(
                MagicMock(), ATTR_UUID, patch_update
            )

        assert batch["updated"] == [ATTR_UUID]
        assert batch["created"] == []
        args = tasks.handle_updated_attribute.delay.call_args.args
        assert args[3] is False
