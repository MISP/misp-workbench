"""Unit tests for the lookup prefilter logic (no OpenSearch, no real Redis)."""

from unittest.mock import MagicMock, patch

import pytest

from app.repositories import lookup as lookup_repository


class FakeRedis:
    """Just the set/string commands the lookup cache uses."""

    def __init__(self):
        self.sets: dict[str, set] = {}
        self.strings: dict[str, str] = {}

    def exists(self, key):
        return int(key in self.sets or key in self.strings)

    def smismember(self, key, values):
        members = self.sets.get(key, set())
        return [int(v in members) for v in values]

    def sadd(self, key, *values):
        target = self.sets.setdefault(key, set())
        before = len(target)
        target.update(values)
        return len(target) - before

    def scard(self, key):
        return len(self.sets.get(key, set()))

    def set(self, key, value, nx=False, ex=None):
        if nx and key in self.strings:
            return None
        self.strings[key] = str(value)
        return True

    def get(self, key):
        return self.strings.get(key)

    def delete(self, *keys):
        for key in keys:
            self.sets.pop(key, None)
            self.strings.pop(key, None)

    def rename(self, src, dst):
        self.sets[dst] = self.sets.pop(src)

    def pipeline(self):
        redis = self

        class Pipe:
            def __init__(self):
                self.ops = []

            def __getattr__(self, name):
                return lambda *a, **k: self.ops.append((name, a, k))

            def execute(self):
                return [getattr(redis, name)(*a, **k) for name, a, k in self.ops]

        return Pipe()


@pytest.fixture
def redis():
    fake = FakeRedis()
    with patch.object(lookup_repository, "get_redis_client", return_value=fake):
        yield fake


class TestCandidates:
    def test_cache_filters_misses(self, redis):
        redis.strings[lookup_repository.BUILT_AT_KEY] = "1"
        redis.sets[lookup_repository.VALUES_KEY] = {"1.2.3.4", "evil.example"}
        candidates, source = lookup_repository._candidates(
            ["8.8.8.8", "1.2.3.4", "evil.example", "benign.example"]
        )
        assert source == "cache"
        assert candidates == ["1.2.3.4", "evil.example"]

    def test_unbuilt_cache_falls_back_and_queues_one_rebuild(self, redis):
        with patch.object(lookup_repository, "request_rebuild") as rebuild:
            candidates, source = lookup_repository._candidates(["a", "b"])
        assert (candidates, source) == (["a", "b"], "opensearch")
        rebuild.assert_called_once()

    def test_redis_down_falls_back(self):
        broken = MagicMock()
        broken.exists.side_effect = ConnectionError("redis down")
        with patch.object(lookup_repository, "get_redis_client", return_value=broken):
            assert lookup_repository._candidates(["a"]) == (["a"], "opensearch")


class TestMaintenance:
    def test_rebuild_swaps_in_a_fresh_set(self, redis):
        redis.sets[lookup_repository.VALUES_KEY] = {"stale.example"}
        with patch.object(
            lookup_repository, "_scan_values", return_value=iter(["a", "b", "a", None])
        ):
            assert lookup_repository.rebuild_cache() == 2
        assert redis.sets[lookup_repository.VALUES_KEY] == {"a", "b"}
        assert lookup_repository.BUILT_AT_KEY in redis.strings
        assert lookup_repository.CURSOR_KEY in redis.strings
        # The lock is released for the next run.
        assert lookup_repository.REBUILD_LOCK_KEY not in redis.strings

    def test_rebuild_is_exclusive(self, redis):
        redis.strings[lookup_repository.REBUILD_LOCK_KEY] = "1"
        assert lookup_repository.rebuild_cache() is None

    def test_sync_adds_with_overlap(self, redis):
        redis.strings[lookup_repository.BUILT_AT_KEY] = "1"
        redis.strings[lookup_repository.CURSOR_KEY] = "1000"
        redis.sets[lookup_repository.VALUES_KEY] = {"a"}
        with patch.object(
            lookup_repository, "_scan_values", return_value=iter(["a", "new"])
        ) as scan:
            assert lookup_repository.sync_cache() == 1
        query = scan.call_args.args[0]
        [window] = [c for c in query["bool"]["filter"] if "range" in c]
        assert (
            window["range"]["updated_at"]["gte"]
            == 1000 - lookup_repository.SYNC_OVERLAP_SECONDS
        )
        assert redis.sets[lookup_repository.VALUES_KEY] == {"a", "new"}

    def test_sync_before_first_build_queues_rebuild(self, redis):
        with patch.object(lookup_repository, "request_rebuild") as rebuild:
            assert lookup_repository.sync_cache() is None
        rebuild.assert_called_once()


class TestLookup:
    def test_too_many_values(self):
        values = [str(i) for i in range(lookup_repository.MAX_VALUES_PER_REQUEST + 1)]
        with pytest.raises(lookup_repository.TooManyValues):
            lookup_repository.lookup(values)

    def test_dedupes_and_skips_opensearch_on_all_misses(self, redis):
        redis.strings[lookup_repository.BUILT_AT_KEY] = "1"
        with patch.object(lookup_repository, "get_opensearch_client") as os_client:
            result = lookup_repository.lookup(["x", "x", "y", ""])
        assert result["checked"] == 2
        assert result["candidates"] == 0
        assert result["matches"] == []
        os_client.assert_not_called()

    def test_response_size_is_bounded(self):
        values = [f"v{i}" for i in range(lookup_repository.MAX_VALUES_PER_REQUEST)]
        with patch.object(
            lookup_repository, "_candidates", return_value=(values, "cache")
        ), patch.object(
            lookup_repository, "_find_attributes", return_value={}
        ) as find, patch.object(
            lookup_repository, "_events", return_value={}
        ):
            lookup_repository.lookup(values, max_attributes=100)
        # 10,000 candidates x 100 would be a million attributes: capped.
        assert find.call_args.args[2] == (
            lookup_repository.MAX_ATTRIBUTES_PER_RESPONSE
            // lookup_repository.MAX_VALUES_PER_REQUEST
        )

    def test_opensearch_returns_at_most_max_attributes_per_value(self):
        client = MagicMock()
        client.search.return_value = {"aggregations": {"values": {"buckets": []}}}
        with patch.object(
            lookup_repository, "get_opensearch_client", return_value=client
        ):
            lookup_repository._find_attributes(["1.2.3.4"], True, 7)
        aggs = client.search.call_args.kwargs["body"]["aggs"]
        assert client.search.call_args.kwargs["body"]["size"] == 0
        assert aggs["values"]["aggs"]["newest"]["top_hits"]["size"] == 7
