"""Tests for JA4+ fingerprint recognition.

The pure helper is tested on its own, then against the misp-attributes_ja4
ingest pipeline installed in OpenSearch: the pipeline fills the field the
correlation engine matches on, so the two must agree on every case.
"""

import pytest

from app.services.ja4 import detect_ja4_variant, ja4_fingerprint, normalize_ja4
from app.services.opensearch import get_opensearch_client

JA4 = "t13d1516h2_8daaf6152771_b186095e22b6"

# (attribute type, value, object relation, expected expanded.ja4)
CASES = [
    ("text", JA4, None, {"value": JA4, "variant": "JA4"}),
    ("text", f"  {JA4.upper()} ", None, {"value": JA4, "variant": "JA4"}),
    (
        "text",
        "q13d0310h3_55b375c5d22e_cd85d2d88918",
        None,
        {"value": "q13d0310h3_55b375c5d22e_cd85d2d88918", "variant": "JA4"},
    ),
    (
        "text",
        "t130200_1301_a56c5b993250",
        None,
        {"value": "t130200_1301_a56c5b993250", "variant": "JA4S"},
    ),
    (
        "text",
        "ge11cn20enus_60ca1bd65281_ac95b44401d9_8df6a44f726c",
        None,
        {
            "value": "ge11cn20enus_60ca1bd65281_ac95b44401d9_8df6a44f726c",
            "variant": "JA4H",
        },
    ),
    (
        "text",
        "a373a9f83c6b_2bab15409345_7bf9a7bf7029",
        None,
        {"value": "a373a9f83c6b_2bab15409345_7bf9a7bf7029", "variant": "JA4X"},
    ),
    (
        "text",
        "c76s76_c71s59_c0s70",
        None,
        {"value": "c76s76_c71s59_c0s70", "variant": "JA4SSH"},
    ),
    # too generic to recognise from its shape alone ...
    ("text", "4289_64", None, None),
    # ... but the object relation says it is a fingerprint
    ("text", "4289_64", "ja4-fingerprint", {"value": "4289_64", "variant": None}),
    (
        "text",
        "1024_2-4-8-1-3_1460_4",
        "ja4-fingerprint",
        {"value": "1024_2-4-8-1-3_1460_4", "variant": None},
    ),
    ("text", JA4, "ja4-fingerprint", {"value": JA4, "variant": "JA4"}),
    # only bare text attributes are recognised by shape
    ("other", JA4, None, None),
    ("ip-src", "1.2.3.4", None, None),
    ("text", "hello world", None, None),
    ("text", "", "ja4-fingerprint", None),
    ("text", "   ", "ja4-fingerprint", None),
    # one hex digit short
    ("text", JA4[:-1], None, None),
    # a non-ASCII digit in the counts
    ("text", "t13d١516h2_8daaf6152771_b186095e22b6", None, None),
]


class TestJa4Helper:
    @pytest.mark.parametrize("attribute_type,value,object_relation,expected", CASES)
    def test_ja4_fingerprint(self, attribute_type, value, object_relation, expected):
        assert ja4_fingerprint(attribute_type, value, object_relation) == expected

    def test_normalize_ja4(self):
        assert normalize_ja4(f" {JA4.upper()}\n") == JA4
        assert normalize_ja4(None) == ""

    def test_detect_ja4_variant_ignores_case_and_padding(self):
        assert detect_ja4_variant(f" {JA4.upper()} ") == "JA4"
        assert detect_ja4_variant("evil.com") is None


class TestJa4Pipeline:
    PIPELINE = "misp-attributes_ja4"

    def simulate(self, sources):
        response = get_opensearch_client().ingest.simulate(
            id=self.PIPELINE, body={"docs": [{"_source": s} for s in sources]}
        )
        return [doc["doc"]["_source"] for doc in response["docs"]]

    def test_pipeline_agrees_with_helper(self):
        sources = []
        for attribute_type, value, object_relation, _ in CASES:
            source = {"type": attribute_type, "value": value}
            if object_relation:
                source["object_relation"] = object_relation
            sources.append(source)

        for case, source in zip(CASES, self.simulate(sources)):
            attribute_type, value, object_relation, expected = case
            got = (source.get("expanded") or {}).get("ja4")
            if got is not None:
                got = {"value": got["value"], "variant": got.get("variant")}
            assert got == expected, case

    def test_pipeline_clears_a_stale_fingerprint(self):
        [source] = self.simulate(
            [{"type": "text", "value": "hello", "expanded": {"ja4": {"value": JA4}}}]
        )
        assert "ja4" not in source["expanded"]
