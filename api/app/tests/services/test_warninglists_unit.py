"""Unit tests for warninglist matching (no database, OpenSearch faked)."""

from unittest.mock import MagicMock

from app.repositories import warninglists as warninglists_repository
from app.repositories.warninglists import Matcher, _candidates, _compile_regex, _List


class FakeEntries:
    """Answers the matcher's entry queries from in-memory lists."""

    def __init__(self, values: dict, ranges: dict):
        # values: {list_id: {value, ...}}, ranges: {list_id: [ip_network, ...]}
        self.values = values
        self.ranges = ranges
        self.searches = 0

    def search(self, index, body):
        self.searches += 1
        filters = body["query"]["bool"]["filter"]
        ids = set(filters[0]["terms"]["warninglist_id"])
        keys = set(filters[2]["terms"]["value"])
        hits = [
            {"_source": {"warninglist_id": list_id, "value": value}}
            for list_id, values in self.values.items()
            if list_id in ids
            for value in values & keys
        ]
        return {"hits": {"total": {"value": len(hits)}, "hits": hits}}

    def msearch(self, body):
        import ipaddress

        responses = []
        for query in body[1::2]:
            filters = query["query"]["bool"]["filter"]
            ids = set(filters[0]["terms"]["warninglist_id"])
            ip = ipaddress.ip_address(filters[1]["term"]["range"])
            buckets = [
                {"key": list_id}
                for list_id, networks in self.ranges.items()
                if list_id in ids and any(ip in n for n in networks)
            ]
            responses.append({"aggregations": {"lists": {"buckets": buckets}}})
        return {"responses": responses}


def make_matcher(lists, client):
    matcher = Matcher.__new__(Matcher)
    matcher.indexed = {
        w.id: w for w in lists if w.type in ("string", "hostname", "cidr")
    }
    matcher.patterns = [w for w in lists if w.type in ("substring", "regex")]
    matcher.client = client
    return matcher


def test_candidates_cover_parts_hosts_and_ips():
    c = _candidates("domain|ip", "Sub.Example.COM|198.51.100.7")
    assert "198.51.100.7" in c.ips
    assert {"sub.example.com", "example.com", "com"} <= c.hosts
    url = _candidates("url", "https://www.example.org/path?q=1")
    assert {"www.example.org", "example.org"} <= url.hosts
    cidr = _candidates("ip-dst", "10.1.2.0/24")
    assert cidr.ips == {"10.1.2.0"}


def test_regex_supports_php_delimiters():
    assert _compile_regex("/^foo.*$/i").search("FOObar")
    assert _compile_regex("^bar$").search("bar")
    assert _compile_regex("/(unclosed/") is None


def test_matching_by_list_type_and_attribute_type():
    import ipaddress

    lists = [
        _List(1, "Top domains", "hostname", frozenset({"domain", "hostname", "url"})),
        _List(2, "Public resolvers", "string", frozenset()),
        _List(3, "RFC1918", "cidr", frozenset({"ip-src", "ip-dst"})),
        _List(4, "Sinkholes", "substring", frozenset(), ["sinkhole"]),
        _List(
            5,
            "Empty hashes",
            "regex",
            frozenset({"md5"}),
            [_compile_regex("/^d41d8cd9/")],
        ),
    ]
    client = FakeEntries(
        values={1: {"example.com"}, 2: {"8.8.8.8"}},
        ranges={3: [ipaddress.ip_network("10.0.0.0/8")]},
    )
    matcher = make_matcher(lists, client)
    results = matcher.match(
        [
            ("domain", "www.example.com"),  # subdomain of a hostname entry
            ("ip-dst", "8.8.8.8"),  # exact string, list applies to all types
            ("ip-dst", "10.20.30.40"),  # inside a CIDR
            ("domain", "10.20.30.40.example.net"),  # not an IP, not listed
            ("domain", "sinkhole.evil.example"),  # substring
            ("md5", "d41d8cd98f00b204e9800998ecf8427e"),  # regex
            ("sha1", "d41d8cd98f00b204e9800998ecf8427e"),  # regex list not for sha1
            ("ip-src", "198.51.100.7"),  # nothing
            ("url", "https://deep.www.example.com/x"),  # host of a URL
        ]
    )
    assert results == [
        ["Top domains"],
        ["Public resolvers"],
        ["RFC1918"],
        [],
        ["Sinkholes"],
        ["Empty hashes"],
        [],
        [],
        ["Top domains"],
    ]


def test_list_restricted_to_other_types_is_skipped():
    lists = [_List(1, "Domains only", "string", frozenset({"domain"}))]
    client = FakeEntries(values={1: {"8.8.8.8"}}, ranges={})
    matcher = make_matcher(lists, client)
    assert matcher.match([("ip-dst", "8.8.8.8"), (None, "8.8.8.8")]) == [
        [],
        ["Domains only"],  # type None checks every list
    ]


def test_no_enabled_lists_never_queries():
    client = MagicMock()
    matcher = make_matcher([], client)
    assert matcher.match([("ip-dst", "8.8.8.8")]) == [[]]
    client.search.assert_not_called()
    client.msearch.assert_not_called()


def test_index_values():
    assert warninglists_repository._index_value("cidr", "10.0.0.1") == {
        "range": "10.0.0.1/32"
    }
    assert warninglists_repository._index_value("cidr", "2001:db8::/32") == {
        "range": "2001:db8::/32"
    }
    assert warninglists_repository._index_value("cidr", "nonsense") is None
    assert warninglists_repository._index_value("hostname", ".Example.COM.") == {
        "value": "example.com"
    }
    assert warninglists_repository._index_value("string", "  ") is None
