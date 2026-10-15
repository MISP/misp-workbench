"""Detection-engine output formats: Suricata rules, Zeek Intel and DNS RPZ.

Network sensors and DNS resolvers don't read IOC lists, they read rules and
zones in their own formats. These write the indicators an export holds in
those formats. They are line formats (see ``stream_exports.LINE_FORMATS``):
values arrive once each, in value order, with every type the value is
recorded under, and the first record of it as metadata.

A value turns into as many lines as its types call for (a domain becomes a
DNS, a TLS SNI and an HTTP Host rule) or none: types an engine has no use for
and values it can't hold (a domain with a space, a URL over TLS for a sensor)
are skipped rather than written as lines the engine would refuse to load.
"""

import hashlib
import ipaddress
import re
from typing import Optional
from urllib.parse import urlsplit

DETECTION_FORMATS = ("suricata", "zeek", "rpz")

# What a line is written from: an attribute's or an indicator's.
SOURCE_FIELDS = ["value", "type", "uuid", "event_uuid", "events", "score", "sources"]

# Suricata/Snort SIDs from 1,000,000 up are for local rules. These take a
# range of their own above them, derived from the rule, so a rule keeps its
# SID from one run to the next and suppressions and thresholds stay put.
SID_BASE = 1_000_000_000
SID_SPACE = 3_000_000_000

# The longest domain an RPZ owner name holds: a name and the zone's origin
# (``rpz.example.``, say) must fit DNS's 255 octets, and a domain is also
# written as ``*.<domain>``.
MAX_RPZ_NAME = 230
# Longer than this, a value's msg is cut: the value itself stays whole in the
# rule's content.
MAX_MSG_VALUE = 128

RPZ_TTL = 300
RPZ_POLICIES = ("nxdomain", "nodata", "drop", "redirect")

_LABEL = re.compile(r"^(?!-)[a-z0-9_-]{1,63}(?<!-)$")
_HASH_LENGTHS = {"md5": 32, "sha1": 40, "sha256": 64}
_HEX = re.compile(r"^[0-9a-fA-F]+$")
_METADATA_UNSAFE = re.compile(r"[^A-Za-z0-9_.:/@-]+")

# A composite type's part, by the name it goes by in the composite.
_PART_TYPES = {"ip": "ip-dst"}


def parts(type_: str, value: str) -> list[tuple[str, str]]:
    """``domain|ip`` and the like, as the types and values they combine."""
    if "|" not in type_ or "|" not in value:
        return [(type_, value)]
    types = type_.split("|")
    values = value.split("|", len(types) - 1)
    if len(values) != len(types):
        return []
    return [(_PART_TYPES.get(t, t), v) for t, v in zip(types, values)]


def domain(value: str) -> Optional[str]:
    """A domain as it goes on the wire: lowercased, IDNA-encoded, checked."""
    value = (value or "").strip().rstrip(".").lower()
    if not value or len(value) > 253:
        return None
    try:
        value = value.encode("idna").decode("ascii")
    except UnicodeError:
        return None
    labels = value.split(".")
    if len(labels) < 2 or not all(_LABEL.match(label) for label in labels):
        return None
    return value


def network(value: str):
    """An address or a network, or None."""
    try:
        return ipaddress.ip_network((value or "").strip(), strict=False)
    except ValueError:
        return None


def _single_line(value: str) -> bool:
    return bool(value) and not any(c in value for c in "\t\r\n")


def _source_name(source: dict) -> Optional[str]:
    sources = source.get("sources") or []
    return str(sources[0].get("name") or "") or None if sources else None


def _event_of(source: dict) -> Optional[str]:
    if source.get("event_uuid"):
        return source["event_uuid"]
    events = source.get("events") or []
    return events[0] if events else None


def _digest(key: str) -> int:
    return int.from_bytes(
        hashlib.blake2b(key.encode("utf-8"), digest_size=8).digest(), "big"
    )


class Writer:
    """Writes one format's lines, and keeps the keys it wrote so each rule,
    intel item or zone record is written once."""

    header_lines = 0

    def __init__(self, options: Optional[dict] = None, now: int = 0):
        self.options = options or {}
        self.now = now
        # Digests, not keys: an export can hold a lot of them.
        self._seen: set = set()

    def header(self) -> str:
        return ""

    def _first(self, key: str) -> bool:
        digest = _digest(key)
        if digest in self._seen:
            return False
        self._seen.add(digest)
        return True

    def lines(self, value: str, records: list) -> str:
        """What ``value`` turns into, from its ``(type, source)`` records."""
        out = []
        for type_, source in records:
            for part_type, part in parts(type_ or "", str(value)):
                out.extend(self.write(part_type, part, source))
        return "".join(out)

    def write(self, type_: str, value: str, source: dict) -> list[str]:
        raise NotImplementedError


# -- Suricata ---------------------------------------------------------------


def content(text: str) -> str:
    """A rule's content string: the bytes Suricata can't take as they are
    (quotes, semicolons, backslashes, pipes, anything not printable ASCII)
    written as |hex|."""
    out: list[str] = []
    run: list[str] = []
    for byte in text.encode("utf-8"):
        char = chr(byte)
        if 0x20 <= byte < 0x7F and char not in '";\\|':
            if run:
                out.append("|" + " ".join(run) + "|")
                run = []
            out.append(char)
        else:
            run.append(f"{byte:02X}")
    if run:
        out.append("|" + " ".join(run) + "|")
    return "".join(out)


def _msg(text: str) -> str:
    if len(text) > MAX_MSG_VALUE:
        text = text[:MAX_MSG_VALUE] + "..."
    text = "".join(c if 0x20 <= ord(c) < 0x7F else "?" for c in text)
    return re.sub(r'([\\";])', r"\\\1", text)


def sid(key: str) -> int:
    digest = hashlib.sha256(key.encode("utf-8")).digest()
    return SID_BASE + int.from_bytes(digest[:8], "big") % SID_SPACE


class SuricataWriter(Writer):
    """Suricata rules: IP rules for addresses and networks, DNS, TLS SNI and
    HTTP Host rules for domains and hostnames, HTTP rules for http:// URLs and
    user agents, and JA3 rules for JA3 fingerprints."""

    def __init__(self, options=None, now=0):
        super().__init__(options, now)
        self.action = self.options.get("rule_action") or "alert"
        # Each SID written, with the digest of the rule it went to: one map
        # both for writing each rule once and for finding a free SID.
        self._sids: dict = {}

    def _sid(self, key: str) -> Optional[int]:
        """The rule's SID, or None if the rule was written already.

        Two rules hashing to the same SID: the second takes the next free
        one. Rare, and stable as long as both stay in the export.
        """
        digest = _digest(key)
        number = sid(key)
        while number in self._sids:
            if self._sids[number] == digest:
                return None
            number = SID_BASE + (number - SID_BASE + 1) % SID_SPACE
        self._sids[number] = digest
        return number

    def _metadata(self, type_: str, source: dict) -> str:
        pairs = [("misp_type", type_)]
        if source.get("uuid"):
            pairs.append(("misp_uuid", source["uuid"]))
        if _event_of(source):
            pairs.append(("misp_event", _event_of(source)))
        if source.get("score") is not None:
            pairs.append(("misp_score", str(source["score"])))
        if _source_name(source):
            pairs.append(("misp_source", _source_name(source)))
        return ", ".join(
            f"{key} {_METADATA_UNSAFE.sub('_', str(value)).strip('_') or '-'}"
            for key, value in pairs
        )

    def _rule(
        self, key, header: str, what: str, value: str, body: str, type_, source
    ) -> Optional[str]:
        number = self._sid(key)
        if number is None:
            return None
        return (
            f"{self.action} {header} ("
            f'msg:"MISP {what} {_msg(value)}"; {body}'
            f"metadata:{self._metadata(type_, source)}; "
            f"sid:{number}; rev:1;)\n"
        )

    def write(self, type_: str, value: str, source: dict) -> list[str]:
        rules: list[Optional[str]] = []
        if type_ in ("ip-dst", "ip-src"):
            net = network(value)
            if net is None:
                return []
            address = str(net.network_address if net.num_addresses == 1 else net)
            if type_ == "ip-dst":
                header = f"ip $HOME_NET any -> [{address}] any"
            else:
                header = f"ip [{address}] any -> $HOME_NET any"
            rules.append(
                self._rule(
                    f"{type_}|{address}", header, type_, address, "", type_, source
                )
            )
        elif type_ in ("domain", "hostname"):
            name = domain(value)
            if name is None:
                return []
            for proto, buffer, header, nocase in (
                ("dns", "dns.query", "dns $HOME_NET any -> any any", "nocase; "),
                (
                    "tls",
                    "tls.sni",
                    "tls $HOME_NET any -> $EXTERNAL_NET any",
                    "nocase; ",
                ),
                # The Host buffer is lowercased already.
                ("http", "http.host", "http $HOME_NET any -> $EXTERNAL_NET any", ""),
            ):
                flow = "" if proto == "dns" else "flow:established,to_server; "
                # A domain covers its subdomains, a hostname is itself only.
                if type_ == "domain":
                    match = f'dotprefix; content:".{content(name)}"; {nocase}endswith; '
                else:
                    match = f'content:"{content(name)}"; {nocase}startswith; endswith; '
                rules.append(
                    self._rule(
                        f"{type_}|{proto}|{name}",
                        header,
                        f"{type_} ({proto})",
                        name,
                        f"{flow}{buffer}; {match}",
                        type_,
                        source,
                    )
                )
        elif type_ == "url":
            rule = self._url_rule(value, source)
            if rule:
                rules.append(rule)
        elif type_ == "user-agent":
            if not _single_line(value):
                return []
            rules.append(
                self._rule(
                    f"user-agent|{value}",
                    "http $HOME_NET any -> $EXTERNAL_NET any",
                    "user-agent",
                    value,
                    "flow:established,to_server; http.user_agent; "
                    f'content:"{content(value)}"; startswith; endswith; ',
                    type_,
                    source,
                )
            )
        elif type_ == "ja3-fingerprint-md5":
            fingerprint = value.strip().lower()
            if len(fingerprint) != 32 or not _HEX.match(fingerprint):
                return []
            rules.append(
                self._rule(
                    f"ja3|{fingerprint}",
                    "tls $HOME_NET any -> $EXTERNAL_NET any",
                    "ja3",
                    fingerprint,
                    f'ja3.hash; content:"{fingerprint}"; ',
                    type_,
                    source,
                )
            )
        return [r for r in rules if r]

    def _url_rule(self, value: str, source: dict) -> Optional[str]:
        """An http:// URL: its host and its request target, exactly.

        An https:// URL's path travels encrypted, out of a sensor's sight;
        its host, recorded as a domain or hostname, is what a sensor sees.
        """
        if not _single_line(value) or " " in value:
            return None
        url = value if "://" in value else f"http://{value}"
        try:
            parts_ = urlsplit(url)
            host = parts_.hostname
        except ValueError:
            return None
        if parts_.scheme.lower() != "http" or not host:
            return None
        target = parts_.path or "/"
        if parts_.query:
            target += f"?{parts_.query}"
        net = network(host)
        name = str(net.network_address) if net is not None else domain(host)
        if name is None:
            return None
        return self._rule(
            f"url|{name}|{target}",
            "http $HOME_NET any -> $EXTERNAL_NET any",
            "url",
            value,
            "flow:established,to_server; "
            f'http.host; content:"{content(name)}"; startswith; endswith; '
            f'http.uri.raw; content:"{content(target)}"; startswith; endswith; ',
            "url",
            source,
        )


# -- Zeek Intel -------------------------------------------------------------

ZEEK_FIELDS = ("indicator", "indicator_type", "meta.source", "meta.desc")
_ZEEK_HASHES = ("md5", "sha1", "sha256")
_ZEEK_EMAILS = ("email", "email-src", "email-dst", "target-email")


def _zeek_field(value: Optional[str]) -> str:
    value = re.sub(r"[\t\r\n]+", " ", str(value or "")).strip()
    return value or "-"


class ZeekWriter(Writer):
    """A Zeek Intel framework file, ``Intel::read_files``' input."""

    header_lines = 1

    def header(self) -> str:
        return "#fields\t" + "\t".join(ZEEK_FIELDS) + "\n"

    def _item(self, indicator: str, kind: str, type_: str, source: dict) -> list:
        if not _single_line(indicator) or not self._first(f"{kind}|{indicator}"):
            return []
        desc = [type_]
        if source.get("score") is not None:
            desc.append(f"score {source['score']}")
        if _event_of(source):
            desc.append(f"event {_event_of(source)}")
        return [
            "\t".join(
                [
                    indicator,
                    f"Intel::{kind}",
                    _zeek_field(_source_name(source) or "misp-workbench"),
                    _zeek_field(", ".join(desc)),
                ]
            )
            + "\n"
        ]

    def write(self, type_: str, value: str, source: dict) -> list[str]:
        value = value.strip()
        if type_ in ("ip-dst", "ip-src"):
            net = network(value)
            if net is None:
                return []
            if net.num_addresses == 1:
                return self._item(str(net.network_address), "ADDR", type_, source)
            return self._item(str(net), "SUBNET", type_, source)
        if type_ in ("domain", "hostname"):
            name = domain(value)
            return self._item(name, "DOMAIN", type_, source) if name else []
        if type_ == "url":
            # Zeek's URLs are written without their scheme.
            url = re.sub(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", "", value)
            return self._item(url, "URL", type_, source) if " " not in url else []
        if type_ in _ZEEK_HASHES:
            if len(value) != _HASH_LENGTHS[type_] or not _HEX.match(value):
                return []
            return self._item(value.lower(), "FILE_HASH", type_, source)
        if type_ == "x509-fingerprint-sha1":
            value = value.replace(":", "")
            if len(value) != 40 or not _HEX.match(value):
                return []
            return self._item(value.lower(), "CERT_HASH", type_, source)
        if type_ == "filename":
            return self._item(value, "FILE_NAME", type_, source)
        if type_ in _ZEEK_EMAILS:
            return self._item(value.lower(), "EMAIL", type_, source)
        if type_ == "user-agent":
            return self._item(value, "SOFTWARE", type_, source)
        return []


# -- DNS RPZ ----------------------------------------------------------------


def rpz_ip(net) -> str:
    """An address or network as an ``rpz-ip`` trigger's owner name:
    the prefix length, then the address's parts in reverse."""
    if net.version == 4:
        return (
            ".".join(
                [str(net.prefixlen), *reversed(str(net.network_address).split("."))]
            )
            + ".rpz-ip"
        )
    groups = []
    for half in str(net.network_address.compressed).split("::"):
        groups.append([g for g in half.split(":") if g])
    # The longest run of zeros, which the address compresses as ::, is zz.
    written = groups[0] if len(groups) == 1 else [*groups[0], "zz", *groups[1]]
    return ".".join([str(net.prefixlen), *reversed(written)]) + ".rpz-ip"


class RpzWriter(Writer):
    """A Response Policy Zone. Domains are triggers for themselves and their
    subdomains, hostnames for themselves, and addresses are ``rpz-ip``
    triggers for answers that resolve to them. The serial is the time of the
    run, so every run's zone is newer than the last."""

    header_lines = 3

    def __init__(self, options=None, now=0):
        super().__init__(options, now)
        policy = self.options.get("rpz_policy") or "nxdomain"
        self.target = {
            "nxdomain": ".",
            "nodata": "*.",
            "drop": "rpz-drop.",
        }.get(policy)
        if policy == "redirect":
            self.target = f"{domain(self.options.get('rpz_redirect') or '')}."

    def header(self) -> str:
        return (
            f"$TTL {RPZ_TTL}\n"
            f"@ SOA localhost. hostmaster.localhost. {self.now} 3600 600 2592000 {RPZ_TTL}\n"
            "@ NS localhost.\n"
        )

    def _record(self, name: str) -> list:
        if not self._first(name):
            return []
        return [f"{name} CNAME {self.target}\n"]

    def write(self, type_: str, value: str, source: dict) -> list[str]:
        if type_ in ("ip-dst", "ip-src"):
            net = network(value)
            return self._record(rpz_ip(net)) if net is not None else []
        if type_ in ("domain", "hostname"):
            name = domain(value)
            if name is None or len(name) > MAX_RPZ_NAME:
                return []
            records = self._record(name)
            if type_ == "domain":
                records += self._record(f"*.{name}")
            return records
        return []


WRITERS = {"suricata": SuricataWriter, "zeek": ZeekWriter, "rpz": RpzWriter}


def writer(fmt: str, options: Optional[dict] = None, now: int = 0) -> Optional[Writer]:
    """The writer of a detection format, or None for any other format."""
    cls = WRITERS.get(fmt)
    return cls(options, now) if cls else None
