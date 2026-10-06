"""JA4+ correlation end to end: indexed through the real ingest pipeline,
matched by the real correlation queries, stored in the real index.

The unit tests in test_correlations.py check the queries that get built; this
checks that they find what the misp-attributes_ja4 pipeline actually stores,
and that the backfill brings attributes indexed before it up to date.
"""

import time
from unittest.mock import MagicMock, patch

import pytest
from app.repositories import correlations as correlations_repository
from app.services.opensearch import get_opensearch_client
from app.tests.api_tester import ApiTester

JA4 = "t13d1516h2_8daaf6152771_b186095e22b6"

# uuid -> (event, type, value, object relation)
ATTRIBUTES = {
    # the same JA4 in two events, cased differently
    "a0000000-0000-0000-0000-000000000001": ("event-a", "text", JA4, "ja4-fingerprint"),
    "a0000000-0000-0000-0000-000000000002": ("event-b", "text", JA4.upper(), None),
    # a JA4L in two events: too generic to recognise outside the object ...
    "a0000000-0000-0000-0000-000000000003": (
        "event-a",
        "text",
        "4289_64",
        "ja4-fingerprint",
    ),
    "a0000000-0000-0000-0000-000000000004": (
        "event-b",
        "text",
        "4289_64",
        "ja4-fingerprint",
    ),
    # ... so this plain text sharing its value must not correlate with it
    "a0000000-0000-0000-0000-000000000005": ("event-c", "text", "4289_64", None),
    # an ordinary attribute still correlates the ordinary way
    "a0000000-0000-0000-0000-000000000006": ("event-a", "domain", "evil.com", None),
    "a0000000-0000-0000-0000-000000000007": ("event-c", "domain", "evil.com", None),
}
UUIDS = list(ATTRIBUTES)


def _settings(match_types):
    settings = MagicMock()
    settings.get_value.side_effect = lambda key, default: (
        match_types if key == "correlations.matchTypes" else default
    )
    return settings


def index_attributes(**params):
    client = get_opensearch_client()
    for uuid, (event_uuid, attribute_type, value, relation) in ATTRIBUTES.items():
        doc = {
            "uuid": uuid,
            "event_uuid": event_uuid,
            "type": attribute_type,
            "value": value,
            "disable_correlation": False,
            "deleted": False,
        }
        if relation:
            doc["object_relation"] = relation
        client.index(index="misp-attributes", id=uuid, body=doc, params=params)
    client.indices.refresh(index="misp-attributes")


def correlate(match_types):
    correlations_repository.delete_attributes_correlations(UUIDS)
    with patch.object(correlations_repository, "dispatch_correlation_notifications"):
        correlations_repository.correlate_attribute_uuids(_settings(match_types), UUIDS)


def stored_correlations():
    """The stored correlations of ATTRIBUTES, keyed by (source, target) suffix."""
    response = get_opensearch_client().search(
        index="misp-attribute-correlations",
        body={
            "size": 100,
            "query": {"terms": {"source_attribute_uuid.keyword": UUIDS}},
        },
    )
    return {
        (
            hit["_source"]["source_attribute_uuid"][-1],
            hit["_source"]["target_attribute_uuid"][-1],
        ): hit["_source"]
        for hit in response["hits"]["hits"]
    }


JA4_PAIRS = {("1", "2"), ("2", "1"), ("3", "4"), ("4", "3"), ("6", "7"), ("7", "6")}


class TestJa4Correlations(ApiTester):
    @pytest.fixture(scope="class")
    def attributes(self, db):
        index_attributes()
        yield UUIDS
        # ApiTester leaves the correlations index alone
        correlations_repository.delete_attributes_correlations(UUIDS)

    def test_pipeline_indexes_the_fingerprints(self, attributes):
        doc = get_opensearch_client().get(index="misp-attributes", id=attributes[1])
        assert doc["_source"]["expanded"]["ja4"] == {"value": JA4, "variant": "JA4"}

    def test_fingerprints_correlate_only_with_fingerprints(self, attributes):
        correlate(["term", "cidr", "ja4"])
        correlations = stored_correlations()

        assert set(correlations) == JA4_PAIRS
        assert correlations[("1", "2")]["match_type"] == "ja4"
        assert correlations[("1", "2")]["ja4_variant"] == "JA4"
        assert correlations[("3", "4")]["match_type"] == "ja4"
        assert "ja4_variant" not in correlations[("3", "4")]
        assert correlations[("6", "7")]["match_type"] == "term"

    def test_without_the_ja4_match_values_correlate_as_before(self, attributes):
        correlate(["term", "cidr"])
        correlations = stored_correlations()

        # the casing differs, so the exact value match misses the JA4 pair
        assert ("1", "2") not in correlations
        # and the JA4L pairs with the plain text that shares its value
        assert ("3", "5") in correlations
        assert all(c["match_type"] == "term" for c in correlations.values())


class TestJa4Backfill(ApiTester):
    @pytest.fixture(scope="class")
    def attributes(self, db):
        # as if indexed before misp-attributes_ja4 existed, and correlated then
        index_attributes(pipeline="_none")
        correlate(["term", "cidr"])
        yield UUIDS
        correlations_repository.delete_attributes_correlations(UUIDS)

    def reindex(self):
        task_id = correlations_repository.start_ja4_reindex()
        for _ in range(100):
            status = correlations_repository.ja4_reindex_status(task_id)
            if status["completed"]:
                break
            time.sleep(0.1)
        assert status["completed"], "the JA4+ reindex did not complete"
        return status

    def test_backfill(self, attributes):
        client = get_opensearch_client()
        assert (
            "expanded"
            not in client.get(index="misp-attributes", id=UUIDS[1])["_source"]
        )
        # text attributes and ja4-fingerprint ones; the domains are left alone
        assert correlations_repository.count_ja4_candidates() == 5

        status = self.reindex()
        assert status["updated"] == 5
        assert status["failures"] == []
        assert client.get(index="misp-attributes", id=UUIDS[1])["_source"]["expanded"][
            "ja4"
        ] == {"value": JA4, "variant": "JA4"}
        assert set(correlations_repository.ja4_attribute_uuids()) == set(UUIDS[:4])

        with patch.object(
            correlations_repository, "dispatch_correlation_notifications"
        ) as dispatch:
            result = correlations_repository.recorrelate_ja4_attributes(
                _settings(["term", "cidr", "ja4"])
            )

        dispatch.assert_not_called()
        assert result == {"attributes": 4, "stored": 4}
        correlations = stored_correlations()
        # the stale term pairing of the JA4L with plain text is gone, the
        # ordinary attributes kept theirs
        assert set(correlations) == JA4_PAIRS
        assert {correlations[pair]["match_type"] for pair in JA4_PAIRS} == {
            "ja4",
            "term",
        }
