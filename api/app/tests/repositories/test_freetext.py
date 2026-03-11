import pytest
from app.repositories.freetext import detect_type


class TestDetectType:
    # ── Hashes ────────────────────────────────────────────────────────────────

    def test_md5(self):
        assert detect_type("d41d8cd98f00b204e9800998ecf8427e") == "md5"

    def test_md5_uppercase(self):
        assert detect_type("D41D8CD98F00B204E9800998ECF8427E") == "md5"

    def test_sha1(self):
        assert detect_type("da39a3ee5e6b4b0d3255bfef95601890afd80709") == "sha1"

    def test_sha256(self):
        assert (
            detect_type(
                "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
            )
            == "sha256"
        )

    def test_sha512(self):
        assert (
            detect_type(
                "cf83e1357eefb8bdf1542850d66d8007d620e4050b5715dc83f4a921d36ce9ce"
                "47d0d13c5d85f2b0ff8318d2877eec2f63b931bd47417a81a538327af927da3e"
            )
            == "sha512"
        )

    # sha1 and sha256 lengths must not be confused with each other
    def test_sha1_not_confused_with_sha256(self):
        value = "a" * 40
        assert detect_type(value) == "sha1"

    def test_sha256_not_confused_with_sha512(self):
        value = "b" * 64
        assert detect_type(value) == "sha256"

    # ── IP addresses ──────────────────────────────────────────────────────────

    def test_ipv4(self):
        assert detect_type("1.2.3.4") == "ip-src"

    def test_ipv4_cidr(self):
        assert detect_type("192.168.1.0/24") == "ip-src"

    def test_ipv4_leading_whitespace(self):
        assert detect_type("  10.0.0.1  ") == "ip-src"

    def test_ipv6(self):
        assert detect_type("2001:db8:85a3:0:0:8a2e:370:7334") == "ip-src"

    def test_ipv6_cidr(self):
        assert detect_type("2001:db8::/32") == "ip-src"

    # ── URLs ──────────────────────────────────────────────────────────────────

    def test_url_http(self):
        assert detect_type("http://example.com/path") == "url"

    def test_url_https(self):
        assert detect_type("https://example.com/path?q=1") == "url"

    def test_url_uppercase_scheme(self):
        assert detect_type("HTTPS://example.com") == "url"

    # ── Email ─────────────────────────────────────────────────────────────────

    def test_email(self):
        assert detect_type("user@example.com") == "email-src"

    def test_email_subdomain(self):
        assert detect_type("user@mail.example.co.uk") == "email-src"

    # ── CVE ───────────────────────────────────────────────────────────────────

    def test_cve(self):
        assert detect_type("CVE-2021-44228") == "cve"

    def test_cve_lowercase(self):
        assert detect_type("cve-2021-44228") == "cve"

    # ── Domain ────────────────────────────────────────────────────────────────

    def test_domain(self):
        assert detect_type("example.com") == "domain"

    def test_domain_subdomain(self):
        assert detect_type("sub.example.co.uk") == "domain"

    # URLs must not fall through to domain
    def test_url_not_detected_as_domain(self):
        assert detect_type("https://example.com") != "domain"

    # emails must not fall through to domain
    def test_email_not_detected_as_domain(self):
        assert detect_type("user@example.com") != "domain"

    # ── Fallback ──────────────────────────────────────────────────────────────

    def test_unknown_returns_other(self):
        assert detect_type("not-an-ioc") == "other"

    def test_empty_string_returns_other(self):
        assert detect_type("") == "other"

    def test_plain_text_returns_other(self):
        assert detect_type("some random free text without structure") == "other"
