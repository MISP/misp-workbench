"""Unit tests for the event attribute/object count reconciliation."""

from unittest.mock import MagicMock, patch

from app.repositories import events as events_repository
from opensearchpy.exceptions import NotFoundError

EVENT_UUID = "11111111-1111-1111-1111-111111111111"
PATCH = "app.repositories.events.get_opensearch_client"


def _client(attribute_count=7, object_count=2):
    client = MagicMock()
    client.count.side_effect = lambda index, body: {
        "misp-attributes": {"count": attribute_count},
        "misp-objects": {"count": object_count},
    }[index]
    return client


class TestSyncEventCounts:
    def test_writes_both_counts_from_the_index(self):
        client = _client()

        with patch(PATCH, return_value=client):
            result = events_repository.sync_event_counts(EVENT_UUID)

        assert result == {"attribute_count": 7, "object_count": 2}
        doc = client.update.call_args.kwargs["body"]["doc"]
        assert doc == {"attribute_count": 7, "object_count": 2}
        assert client.update.call_args.kwargs["id"] == EVENT_UUID

    def test_counts_attributes_inside_objects(self):
        client = _client()

        with patch(PATCH, return_value=client):
            events_repository.count_event_attributes(EVENT_UUID)

        # no object_uuid clause: an attribute inside an object counts too
        body = client.count.call_args.kwargs["body"]
        assert body["query"]["bool"]["must"] == [
            {"term": {"event_uuid": EVENT_UUID}}
        ]
        assert "object_uuid" not in str(body)

    def test_skips_soft_deleted(self):
        client = _client()

        with patch(PATCH, return_value=client):
            events_repository.count_event_attributes(EVENT_UUID)
            events_repository.count_event_objects(EVENT_UUID)

        for call in client.count.call_args_list:
            assert call.kwargs["body"]["query"]["bool"]["must_not"] == [
                {"term": {"deleted": True}}
            ]

    def test_missing_event_is_logged_not_raised(self):
        client = _client()
        client.update.side_effect = NotFoundError(404, "missing", {})

        with patch(PATCH, return_value=client):
            result = events_repository.sync_event_counts(EVENT_UUID)

        assert result == {"attribute_count": 7, "object_count": 2}
