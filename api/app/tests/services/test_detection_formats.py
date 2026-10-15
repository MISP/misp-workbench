import ipaddress

import pytest

from app.schemas.export import ExportCreate
from app.services.exports import detection_formats as formats

SOURCE = {
    "uuid": "11111111-1111-4111-8111-111111111111",
    "events": ["22222222-2222-4222-8222-222222222222"],
    "score": 73,
    "sources": [{"name": "CIRCL OSINT, feed"}],
}


def write(fmt, records, options=None, now=1792000000):
    writer = formats.writer(fmt, options, now)
    out = writer.header()
    for type_, value in records:
        out += writer.lines(value, [(type_, SOURCE)])
    return out


def body(fmt, records, options=None):
    return write(fmt, records, options).splitlines()[formats.writer(fmt).header_lines :]


class TestParts:
    def test_composites(self):
        assert formats.parts("domain|ip", "evil.com|192.0.2.1") == [
            ("domain", "evil.com"),
            ("ip-dst", "192.0.2.1"),
        ]
        assert formats.parts("filename|md5", "a|b.exe|d41d") == [
            ("filename", "a"),
            ("md5", "b.exe|d41d"),
        ]
        assert formats.parts("ip-dst", "192.0.2.1") == [("ip-dst", "192.0.2.1")]

    @pytest.mark.parametrize(
        "value,expected",
        [
            ("Evil.COM.", "evil.com"),
            ("bücher.example", "xn--bcher-kva.example"),
            ("_dmarc.example.org", "_dmarc.example.org"),
            ("bad domain.com", None),
            ("-lead.example", None),
            ("localhost", None),
            ("a" * 64 + ".com", None),
            ("", None),
        ],
    )
    def test_domain(self, value, expected):
        assert formats.domain(value) == expected


class TestWhatAValueMayBlock:
    """Values come from feeds: none may block more than an indicator."""

    @pytest.mark.parametrize(
        "value",
        [
            "0.0.0.0/0",
            "::/0",
            "10.0.0.0/8",
            "2001:db8::/32",
            "127.0.0.1",
            "0.0.0.0",
            "::1",
            "224.0.0.1",
            "169.254.1.1",
            "fe80::1",
            "240.0.0.1",
            # Python takes a scope, which would go into the rule as is.
            'fe80::1%a] any (msg:"x"; sid:1;) #',
            "2001:db8::1%eth0",
            # IPv4 in IPv6: all of IPv4, a /8, loopback.
            "::ffff:0:0/96",
            "::ffff:10.0.0.0/104",
            "::ffff:127.0.0.1",
            "::ffff:192.0.2.1",
            "::/96",
            "64:ff9b::/96",
            "64:ff9b::c000:201",
        ],
    )
    def test_addresses(self, value):
        for fmt in formats.DETECTION_FORMATS:
            assert body(fmt, [("ip-dst", value)]) == [], fmt

    @pytest.mark.parametrize("value", ["co.uk", "github.io", "COM.AU."])
    def test_public_suffixes(self, value):
        for fmt in formats.DETECTION_FORMATS:
            for type_ in ("domain", "hostname"):
                assert body(fmt, [(type_, value)]) == [], (fmt, type_)
        assert body("suricata", [("url", f"http://{value}/x")]) == []
        assert body("rpz", [("domain", f"evil.{value}")]) != []

    def test_narrow_networks_and_private_addresses_stay(self):
        assert len(body("rpz", [("ip-dst", "192.168.1.0/24")])) == 1
        assert len(body("rpz", [("ip-dst", "10.1.2.3")])) == 1

    @pytest.mark.parametrize("value", ["#separator ,", "#fields", "-", "(empty)"])
    def test_zeek_reserved_values(self, value):
        assert body("zeek", [("filename", value)]) == []


class TestSuricata:
    def test_addresses(self):
        rules = body(
            "suricata",
            [
                ("ip-dst", "192.0.2.1"),
                ("ip-src", "10.20.0.0/16"),
                ("ip-dst", "2001:db8::1"),
                ("ip-dst", "not an address"),
            ],
        )
        assert len(rules) == 3
        assert rules[0].startswith("alert ip $HOME_NET any -> [192.0.2.1] any (")
        assert rules[1].startswith("alert ip [10.20.0.0/16] any -> $HOME_NET any (")
        assert "[2001:db8::1]" in rules[2]

    def test_domain_covers_subdomains_and_hostname_itself(self):
        domain = body("suricata", [("domain", "evil.com")])
        assert [r.split(" (")[0] for r in domain] == [
            "alert dns $HOME_NET any -> any any",
            "alert tls $HOME_NET any -> $EXTERNAL_NET any",
            "alert http $HOME_NET any -> $EXTERNAL_NET any",
        ]
        assert 'dns.query; dotprefix; content:".evil.com"; nocase; endswith;' in (
            domain[0]
        )
        # The Host buffer is lowercase: nocase there is refused.
        assert 'http.host; dotprefix; content:".evil.com"; endswith;' in domain[2]
        hostname = body("suricata", [("hostname", "c2.evil.com")])
        assert 'content:"c2.evil.com"; nocase; startswith; endswith;' in hostname[0]
        assert "dotprefix" not in "".join(hostname)

    def test_urls(self):
        rules = body(
            "suricata",
            [
                ("url", 'http://Evil.com/dl?a=1;b="2"'),
                ("url", "evil.com/no-scheme"),
                ("url", "https://evil.com/secret"),
            ],
        )
        # An https:// URL's path is encrypted: no rule could see it.
        assert len(rules) == 2
        assert 'http.host; content:"evil.com"; startswith; endswith;' in rules[0]
        assert 'http.uri.raw; content:"/dl?a=1|3B|b=|22|2|22|";' in rules[0]
        assert 'content:"/no-scheme"' in rules[1]

    def test_content_escapes(self):
        assert formats.content('a";\\|b') == "a|22 3B 5C 7C|b"
        assert formats.content("é") == "|C3 A9|"
        assert formats.content("plain text") == "plain text"

    def test_metadata_and_msg(self):
        (rule,) = body("suricata", [("user-agent", 'Bot "x"; y')])
        assert 'msg:"MISP user-agent Bot \\"x\\"\\; y";' in rule
        assert (
            "metadata:misp_type user-agent, "
            "misp_uuid 11111111-1111-4111-8111-111111111111, "
            "misp_event 22222222-2222-4222-8222-222222222222, "
            "misp_score 73, misp_source CIRCL_OSINT_feed;"
        ) in rule

    def test_sids_are_stable_and_unique(self):
        records = [("domain", f"d{i}.example") for i in range(200)]
        first = write("suricata", records)
        again = write("suricata", list(records))
        assert first == again
        sids = [line.split("sid:")[1].split(";")[0] for line in first.splitlines()]
        assert len(sids) == len(set(sids)) == 600
        assert all(
            formats.SID_BASE <= int(s) < formats.SID_BASE + formats.SID_SPACE
            for s in sids
        )

    def test_colliding_sids_move_on(self, monkeypatch):
        monkeypatch.setattr(formats, "sid", lambda key: formats.SID_BASE + 5)
        rules = body("suricata", [("ip-dst", "192.0.2.1"), ("ip-dst", "192.0.2.2")])
        assert [r.split("sid:")[1].split(";")[0] for r in rules] == [
            str(formats.SID_BASE + 5),
            str(formats.SID_BASE + 6),
        ]

    def test_each_rule_once(self):
        # The same rule from two spellings of one value.
        rules = body("suricata", [("domain", "Evil.com"), ("domain", "evil.com.")])
        assert len(rules) == 3

    def test_drop_and_ja3(self):
        rules = body(
            "suricata",
            [
                ("ja3-fingerprint-md5", "E7D705A3286E19EA42F587B344EE6865"),
                ("ja3-fingerprint-md5", "nothex"),
            ],
            {"rule_action": "drop"},
        )
        assert len(rules) == 1
        assert rules[0].startswith("drop tls ")
        assert 'ja3.hash; content:"e7d705a3286e19ea42f587b344ee6865";' in rules[0]

    def test_unknown_types_write_nothing(self):
        out = write("suricata", [("text", "hello"), ("md5", "0" * 32)])
        assert out == ""


class TestZeek:
    def test_items(self):
        out = write(
            "zeek",
            [
                ("ip-dst", "192.0.2.1"),
                ("ip-src", "198.51.100.0/24"),
                ("domain|ip", "evil.com|192.0.2.9"),
                ("url", "https://evil.com/path?q=1"),
                ("filename|sha256", "evil.exe|" + "A" * 64),
                ("email-src", "Phish@Evil.com"),
                ("x509-fingerprint-sha1", ":".join(["AB"] * 20)),
                ("md5", "short"),
                ("text", "ignored"),
            ],
        )
        lines = out.splitlines()
        assert lines[0] == "#fields\tindicator\tindicator_type\tmeta.source\tmeta.desc"
        assert [line.split("\t")[:2] for line in lines[1:]] == [
            ["192.0.2.1", "Intel::ADDR"],
            ["198.51.100.0/24", "Intel::SUBNET"],
            ["evil.com", "Intel::DOMAIN"],
            ["192.0.2.9", "Intel::ADDR"],
            ["evil.com/path?q=1", "Intel::URL"],
            ["evil.exe", "Intel::FILE_NAME"],
            ["a" * 64, "Intel::FILE_HASH"],
            ["phish@evil.com", "Intel::EMAIL"],
            ["ab" * 20, "Intel::CERT_HASH"],
        ]
        assert lines[1].split("\t")[2:] == [
            "CIRCL OSINT, feed",
            "ip-dst, score 73, event 22222222-2222-4222-8222-222222222222",
        ]

    def test_values_with_tabs_are_skipped(self):
        assert body("zeek", [("filename", "a\tb"), ("user-agent", "x\ny")]) == []

    def test_metadata_defaults(self):
        writer = formats.writer("zeek")
        assert writer.lines("192.0.2.1", [("ip-dst", {})]) == (
            "192.0.2.1\tIntel::ADDR\tmisp-workbench\tip-dst\n"
        )


class TestRpz:
    def test_zone(self):
        out = write(
            "rpz",
            [
                ("domain", "Evil.com"),
                ("hostname", "c2.bad.net"),
                ("ip-dst", "192.0.2.1"),
                ("ip-src", "10.20.0.0/16"),
                ("ip-dst", "2001:db8::1"),
                ("url", "http://evil.com/x"),
            ],
        )
        assert out.splitlines() == [
            "$TTL 300",
            "@ SOA localhost. hostmaster.localhost. 1792000000 3600 600 2592000 300",
            "@ NS localhost.",
            "evil.com CNAME .",
            "*.evil.com CNAME .",
            "c2.bad.net CNAME .",
            "32.1.2.0.192.rpz-ip CNAME .",
            "16.0.0.20.10.rpz-ip CNAME .",
            "128.1.zz.db8.2001.rpz-ip CNAME .",
        ]

    @pytest.mark.parametrize(
        "network,name",
        [
            ("2001:db8:0:1::/64", "64.zz.1.0.db8.2001.rpz-ip"),
            ("::1", "128.1.zz.rpz-ip"),
            ("2001:db8::", "128.zz.db8.2001.rpz-ip"),
            ("2001:db8:1:2:3:4:5:6", "128.6.5.4.3.2.1.db8.2001.rpz-ip"),
        ],
    )
    def test_ipv6_triggers(self, network, name):
        assert formats.rpz_ip(ipaddress.ip_network(network)) == name

    @pytest.mark.parametrize(
        "options,target",
        [
            ({"rpz_policy": "nodata"}, "*."),
            ({"rpz_policy": "drop"}, "rpz-drop."),
            (
                {"rpz_policy": "redirect", "rpz_redirect": "walled.example.org"},
                "walled.example.org.",
            ),
        ],
    )
    def test_policies(self, options, target):
        assert body("rpz", [("hostname", "c2.bad.net")], options) == [
            f"c2.bad.net CNAME {target}"
        ]

    def test_names_too_long_for_a_zone_are_skipped(self):
        name = ".".join(["a" * 60] * 4)
        assert formats.domain(name) and len(name) > formats.MAX_RPZ_NAME
        assert body("rpz", [("domain", name)]) == []


class TestFormatOptions:
    def test_only_detection_formats_keep_them(self):
        assert (
            ExportCreate(
                name="x", query="*", format="json", format_options={}
            ).format_options
            is None
        )

    def test_redirect_needs_a_host(self):
        with pytest.raises(ValueError, match="rpz_redirect"):
            ExportCreate(
                name="x",
                query="*",
                format="rpz",
                format_options={"rpz_policy": "redirect", "rpz_redirect": "not a host"},
            )
        options = ExportCreate(
            name="x",
            query="*",
            format="rpz",
            format_options={
                "rpz_policy": "redirect",
                "rpz_redirect": "Walled.Example.",
            },
        ).format_options
        assert options.rpz_redirect == "walled.example"

    def test_events_have_no_values_to_write(self):
        with pytest.raises(ValueError, match="attributes and indicators"):
            ExportCreate(name="x", query="*", format="zeek", index_target="events")
