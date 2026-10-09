"""Unit tests for translating MISP ``/sightings/add`` requests (no database)."""

from unittest.mock import patch

import pytest

from app.repositories import sightings as sightings_repository
from app.schemas.sighting import MispSightingAdd

ATTRIBUTE = {
    "uuid": "5f2c1e2a-0000-4000-8000-000000000001",
    "event_uuid": "5f2c1e2a-0000-4000-8000-0000000000e1",
    "value": "198.51.100.7",
}


def translate(attribute_ref=None, **body):
    return sightings_repository.sightings_from_misp(
        MispSightingAdd(**body), attribute_ref
    )


class TestSightingsFromMisp:
    def test_values_and_value(self):
        sightings = translate(values=["a.example", "b.example"], value="c.example")
        assert [s["value"] for s in sightings] == [
            "a.example",
            "b.example",
            "c.example",
        ]
        assert all(s["type"] == "positive" for s in sightings)

    @pytest.mark.parametrize(
        "given,stored",
        [
            (0, "positive"),
            ("1", "false-positive"),
            (2, "expiration"),
            ("false-positive", "false-positive"),
            (None, "positive"),
        ],
    )
    def test_types(self, given, stored):
        [sighting] = translate(value="x", type=given)
        assert sighting["type"] == stored

    def test_unknown_type(self):
        with pytest.raises(ValueError, match="unknown sighting type"):
            translate(value="x", type=7)

    def test_source_and_timestamp(self):
        [sighting] = translate(value="x", source="splunk-prod", timestamp=1700000000)
        assert sighting["observer"] == {"source": "splunk-prod"}
        assert sighting["timestamp"] == 1700000000

    def test_nothing_to_sight(self):
        with pytest.raises(ValueError, match="value, values, uuid or id"):
            translate(values=[" "])

    def test_attribute_by_uuid_or_url(self):
        with patch.object(
            sightings_repository, "_resolve_attribute", return_value=ATTRIBUTE
        ) as resolve:
            [by_body] = translate(uuid=ATTRIBUTE["uuid"], type=1)
            [by_url] = translate(attribute_ref="42")
        assert by_body == {
            "type": "false-positive",
            "value": "198.51.100.7",
            "attribute_uuid": ATTRIBUTE["uuid"],
            "event_uuid": ATTRIBUTE["event_uuid"],
        }
        assert by_url["value"] == "198.51.100.7"
        assert [c.args[0] for c in resolve.call_args_list] == [ATTRIBUTE["uuid"], "42"]

    def test_unknown_attribute(self):
        with patch.object(
            sightings_repository, "_resolve_attribute", return_value=None
        ):
            with pytest.raises(sightings_repository.SightingTargetNotFound):
                translate(uuid="nope")


class TestValueQuery:
    def test_long_values_use_the_text_field(self):
        long_value = "https://example.com/" + "a" * 300
        query = sightings_repository._value_query(["1.2.3.4", long_value])
        should = query["bool"]["should"]
        assert {"terms": {"value.keyword": ["1.2.3.4"]}} in should
        assert {"match_phrase": {"value": long_value}} in should

    def test_no_values_match_nothing(self):
        assert sightings_repository._value_query([])["bool"]["should"] == [
            {"match_none": {}}
        ]
