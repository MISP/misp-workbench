"""Unit tests for the CSV feed ingestion in ``app/worker/tasks.py``.

Covers the header handling of the ``fetch_csv_feed`` task.
"""

from unittest.mock import MagicMock, patch

from app.worker import tasks as worker_tasks

EVENT_UUID = "11111111-1111-1111-1111-111111111111"

CSV_LINES = ["value", "1.2.3.4", "5.6.7.8"]


def _csv_feed(header: bool):
    """Return a CSV feed whose rows are read from a local file."""
    db_feed = MagicMock()
    db_feed.settings = {"csvConfig": {"header": header, "delimiter": ","}}
    db_feed.input_source = "local"
    db_feed.name = "csv-feed"
    return db_feed


class TestFetchCsvFeedTask:
    """Only the header row may be skipped, every other row is ingested."""

    def _fetch(self, db_feed):
        db_event = MagicMock()
        db_event.uuid = EVENT_UUID

        with patch.object(worker_tasks, "Session"), \
                patch.object(worker_tasks.attributes_repository, "bulk_ingest"), \
                patch.object(worker_tasks.attributes_repository, "create_attribute"), \
                patch.object(worker_tasks.users_repository, "get_user_by_id"), \
                patch.object(worker_tasks.events_repository, "sync_event_counts"), \
                patch.object(
                    worker_tasks.feeds_repository,
                    "get_feed_by_id",
                    return_value=db_feed,
                ), \
                patch.object(
                    worker_tasks.feeds_repository,
                    "get_or_create_feed_event",
                    return_value=db_event,
                ), \
                patch.object(
                    worker_tasks.feeds_repository,
                    "fetch_csv_content_from_local",
                    return_value=CSV_LINES,
                ), \
                patch.object(
                    worker_tasks.feeds_repository,
                    "process_csv_feed_row",
                    side_effect=lambda row, settings: {
                        "type": "ip-src",
                        "value": row[0],
                    },
                ) as process_row:
            result = worker_tasks.fetch_csv_feed(1, 1)

        return result, process_row

    def test_skips_the_header_row_only(self):
        result, process_row = self._fetch(_csv_feed(header=True))

        assert result["message"] == (
            "CSV feed=csv-feed processed, 2 rows parsed, 2 attributes created, "
            "0 rows failed."
        )
        assert [call.args[0] for call in process_row.call_args_list] == [
            ["1.2.3.4"],
            ["5.6.7.8"],
        ]

    def test_keeps_every_row_when_there_is_no_header(self):
        result, process_row = self._fetch(_csv_feed(header=False))

        assert result["message"] == (
            "CSV feed=csv-feed processed, 3 rows parsed, 3 attributes created, "
            "0 rows failed."
        )
        assert process_row.call_count == 3

    def test_a_missing_header_key_is_treated_as_no_header(self):
        # a feed stored before the flag existed raised KeyError on the guard,
        # which sits outside the per-row try/except and so killed the whole task
        db_feed = _csv_feed(header=False)
        del db_feed.settings["csvConfig"]["header"]

        result, process_row = self._fetch(db_feed)

        assert result["message"] == (
            "CSV feed=csv-feed processed, 3 rows parsed, 3 attributes created, "
            "0 rows failed."
        )
        assert process_row.call_count == 3
