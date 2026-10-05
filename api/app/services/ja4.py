"""Recognise JA4+ fingerprints so they can be indexed and correlated as such.

MISP core has no JA4+ attribute type. A fingerprint travels as a ``text``
attribute, normally inside a ``ja4-plus`` object under the ``ja4-fingerprint``
relation, with the variant (JA4, JA4S, ...) in a sibling ``ja4-type``
attribute. Inventing workbench-only types would break pushing to MISP, so
fingerprints are recognised instead, from where they sit or from their shape.

Kept in step with the misp-attributes_ja4 ingest pipeline, which fills the
``expanded.ja4`` fields the correlation engine matches against.
"""

import re
from typing import Optional

JA4_OBJECT_RELATION = "ja4-fingerprint"

# The variants the ja4-plus object template offers for its ja4-type relation.
JA4_VARIANTS = (
    "JA4",
    "JA4S",
    "JA4H",
    "JA4L",
    "JA4X",
    "JA4SSH",
    "JA4T",
    "JA4TS",
    "JA4TScan",
)

# Shapes of the hashed (default) form of each variant, matched against the
# normalized value. See
# https://github.com/FoxIO-LLC/ja4/blob/main/technical_details/README.md
# Digits are spelled [0-9]: Python's \d also matches non-ASCII digits, Java's
# does not, and the ingest pipeline runs these same patterns in Painless.
#
# Only variants distinctive enough to tell apart from arbitrary text are
# listed. JA4L (``4289_64``), JA4T/JA4TS (``1024_2-4-8-1-3_1460_4``) and
# JA4TScan are short runs of digits, so a bare ``text`` attribute shaped like
# one is not taken for a fingerprint; they are recognised only from the
# ja4-fingerprint relation. JA4T and JA4TS share a shape anyway, as do the
# client and server halves of JA4L.
JA4_PATTERNS = (
    # protocol, TLS version, SNI, cipher count, extension count, ALPN
    (
        "JA4",
        re.compile(
            r"^[tqd][0-9a-z]{2}[di][0-9]{4}[0-9a-z]{2}_[0-9a-f]{12}_[0-9a-f]{12}$"
        ),
    ),
    # protocol, TLS version, extension count, ALPN; chosen cipher
    (
        "JA4S",
        re.compile(r"^[tqd][0-9a-z]{2}[0-9]{2}[0-9a-z]{2}_[0-9a-f]{4}_[0-9a-f]{12}$"),
    ),
    # method, HTTP version, cookie, referer, header count, language
    (
        "JA4H",
        re.compile(
            r"^[a-z]{2}[0-9]{2}[cn][rn][0-9]{2}[0-9a-z]{4}_[0-9a-f]{12}_[0-9a-f]{12}_[0-9a-f]{12}$"
        ),
    ),
    ("JA4X", re.compile(r"^[0-9a-f]{12}_[0-9a-f]{12}_[0-9a-f]{12}$")),
    ("JA4SSH", re.compile(r"^c[0-9]+s[0-9]+_c[0-9]+s[0-9]+_c[0-9]+s[0-9]+$")),
)


def normalize_ja4(value) -> str:
    """JA4+ fingerprints are lowercase by definition; match them as such."""
    return str(value or "").strip().lower()


def detect_ja4_variant(value) -> Optional[str]:
    """The variant a value is shaped like, or None."""
    normalized = normalize_ja4(value)
    for variant, pattern in JA4_PATTERNS:
        if pattern.match(normalized):
            return variant
    return None


def ja4_fingerprint(attribute_type, value, object_relation=None) -> Optional[dict]:
    """The ``expanded.ja4`` fields for an attribute, or None if it is not one.

    An attribute under the ja4-fingerprint relation is a fingerprint whatever
    it looks like - the object says so - though its variant is only known when
    the value has a recognisable shape. A bare ``text`` attribute counts only
    when it has one.
    """
    normalized = normalize_ja4(value)
    if not normalized:
        return None

    variant = detect_ja4_variant(normalized)

    if object_relation == JA4_OBJECT_RELATION:
        return {"value": normalized, "variant": variant}

    if attribute_type == "text" and variant:
        return {"value": normalized, "variant": variant}

    return None
