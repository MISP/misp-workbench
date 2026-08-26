"""Unit tests for the correlation wiring in ``app/repositories/attributes.py``."""

from unittest.mock import MagicMock, patch

from app.repositories import attributes as attributes_repository
from app.schemas import attribute as attribute_schemas
from fastapi_pagination import Page

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
        # no per attribute task: notifications and reactor dispatch are handed
        # over in the batch as well
        tasks.handle_created_attribute.delay.assert_not_called()
        assert batch["handled"] == [[str(created.uuid), None, EVENT_UUID]]

    def test_ingest_does_not_refresh_per_attribute(self):
        client = MagicMock()

        with patch(OS_PATCH, return_value=client), patch(TASKS_PATCH), \
                attributes_repository.bulk_ingest():
            attributes_repository.create_attribute(MagicMock(), _attribute_create())

        assert client.index.call_args.kwargs["refresh"] is False
        # ... and the index is made searchable once on the way out
        client.indices.refresh.assert_called_once_with(index="misp-attributes")

    def test_single_create_refreshes_straight_away(self):
        client = MagicMock()

        with patch(OS_PATCH, return_value=client), patch(TASKS_PATCH):
            attributes_repository.create_attribute(MagicMock(), _attribute_create())

        assert client.index.call_args.kwargs["refresh"] is True

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


class TestEnrichPageWithCorrelations:
    def _page(self, *attributes):
        return Page(
            items=list(attributes),
            total=len(attributes),
            page=1,
            size=10,
            pages=1,
        )

    def _bucketed(self, total, attached):
        return {
            "aggregations": {
                "by_attribute": {
                    "buckets": [
                        {
                            "key": ATTR_UUID,
                            "doc_count": total,
                            "correlations": {
                                "hits": {
                                    "hits": [
                                        {"_source": {"target_attribute_uuid": str(n)}}
                                        for n in range(attached)
                                    ]
                                }
                            },
                        }
                    ]
                }
            }
        }

    def test_reports_the_total_alongside_what_it_attached(self):
        client = MagicMock()
        client.search.return_value = self._bucketed(total=4312, attached=100)

        with patch(OS_PATCH, return_value=client):
            page = attributes_repository.enrich_attributes_page_with_correlations(
                self._page(_indexed_attribute())
            )

        attribute = page.items[0]
        # bounded per attribute, but the real total is not hidden
        assert len(attribute.correlations) == 100
        assert attribute.correlation_count == 4312

    def test_buckets_per_attribute_instead_of_a_flat_window(self):
        client = MagicMock()
        client.search.return_value = self._bucketed(total=1, attached=1)

        with patch(OS_PATCH, return_value=client):
            attributes_repository.enrich_attributes_page_with_correlations(
                self._page(_indexed_attribute())
            )

        body = client.search.call_args.kwargs["body"]
        assert body["size"] == 0
        assert "by_attribute" in body["aggs"]
        # nothing relies on the 10000 hit window any more
        assert (
            body["aggs"]["by_attribute"]["aggs"]["correlations"]["top_hits"]["size"]
            == attributes_repository.CORRELATIONS_PER_ATTRIBUTE
        )

    def test_attribute_without_correlations_reads_zero(self):
        client = MagicMock()
        client.search.return_value = {
            "aggregations": {"by_attribute": {"buckets": []}}
        }

        with patch(OS_PATCH, return_value=client):
            page = attributes_repository.enrich_attributes_page_with_correlations(
                self._page(_indexed_attribute())
            )

        assert page.items[0].correlations == []
        assert page.items[0].correlation_count == 0

    def test_empty_page_is_left_alone(self):
        client = MagicMock()

        with patch(OS_PATCH, return_value=client):
            attributes_repository.enrich_attributes_page_with_correlations(self._page())

        client.search.assert_not_called()
