"""Unit tests for sends to sinks from code (no database, no network)."""

from types import SimpleNamespace
from unittest.mock import patch

import pytest

from app.repositories import sinks as sinks_repository
from app.services.sinks import send


def sink(**filters):
    return SimpleNamespace(
        id=1, name="s", type="webhook", config={"url": "http://x"}, filters=filters
    )


class TestEffectiveFilters:
    def test_applied_by_default(self):
        filters = {
            "to_ids_only": True,
            "types": ["ip-dst"],
            "exclude_tags": ["tlp:red"],
        }
        assert sinks_repository.effective_filters(sink(**filters)) == filters

    def test_opt_out_keeps_exclusions(self):
        effective = sinks_repository.effective_filters(
            sink(
                to_ids_only=True,
                types=["ip-dst"],
                tags=["tlp:green"],
                exclude_tags=["tlp:red"],
                exclude_warninglisted=True,
            ),
            apply_filters=False,
        )
        assert effective == {
            "to_ids_only": False,
            "types": [],
            "tags": [],
            "exclude_tags": ["tlp:red"],
            "exclude_warninglisted": True,
        }


class TestRecords:
    def test_clean_record(self):
        record = send._clean_record(
            {
                "value": "198.51.100.7",
                "type": "ip-dst",
                "tags": ["tlp:green"],
                "comment": "c2",
            }
        )
        assert record["value"] == "198.51.100.7"
        assert record["to_ids"] is True
        assert record["tags"] == ["tlp:green"]
        assert record["event"]["tags"] == []

    @pytest.mark.parametrize(
        "bad",
        [
            "not a dict",
            {"type": "ip-dst"},
            {"value": "x"},
            {"value": "", "type": "ip-dst"},
            {"value": "x", "type": "ip-dst", "config": {"url": "http://evil"}},
        ],
    )
    def test_invalid_records(self, bad):
        with pytest.raises(send.SinkSendError):
            send._clean_record(bad)

    def test_long_fields_are_truncated(self):
        record = send._clean_record({"value": "a" * 10_000, "type": "text"})
        assert len(record["value"]) == send.MAX_FIELD_LENGTH

    def test_deliver_records_applies_filters_and_exclusions(self):
        records = [
            send._clean_record({"value": "a", "type": "ip-dst", "tags": ["tlp:green"]}),
            send._clean_record({"value": "b", "type": "domain", "tags": ["tlp:green"]}),
            send._clean_record({"value": "c", "type": "ip-dst", "tags": ["tlp:red"]}),
        ]
        sent = []

        class Transport:
            def send(self, batch):
                sent.extend(r["value"] for r in batch)

            def close(self):
                pass

        s = sink(types=["ip-dst"], exclude_tags=["tlp:red"])
        with patch.object(sinks_repository, "open_transport", return_value=Transport()):
            count = sinks_repository.deliver_records(s, records)
            assert count == 1
            assert sent == ["a"]
            sent.clear()
            # Selection skipped, exclusion kept.
            count = sinks_repository.deliver_records(s, records, apply_filters=False)
            assert count == 2
            assert sent == ["a", "b"]


def test_attribute_uuids_accepts_dicts_and_dedupes():
    assert send._attribute_uuids(["u1", {"uuid": "u2"}, "u1"]) == ["u1", "u2"]
    with pytest.raises(send.SinkSendError):
        send._attribute_uuids([{"value": "no uuid"}])
