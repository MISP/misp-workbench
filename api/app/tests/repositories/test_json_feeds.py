import json

import pytest
from app.repositories.feeds import (
    get_json_path,
    parse_json_feed_items,
    process_json_item_to_attribute,
)
from fastapi import HTTPException


# ── get_json_path ─────────────────────────────────────────────────────────────


class TestGetJsonPath:
    def test_empty_path_returns_object(self):
        obj = {"a": 1}
        assert get_json_path(obj, "") is obj

    def test_simple_key(self):
        assert get_json_path({"a": 42}, "a") == 42

    def test_nested_path(self):
        assert get_json_path({"a": {"b": {"c": "deep"}}}, "a.b.c") == "deep"

    def test_missing_key_returns_none(self):
        assert get_json_path({"a": 1}, "b") is None

    def test_missing_intermediate_key_returns_none(self):
        assert get_json_path({"a": {"b": 1}}, "a.x.c") is None

    def test_non_dict_in_path_returns_none(self):
        assert get_json_path({"a": "not-a-dict"}, "a.b") is None

    def test_none_path_returns_object(self):
        obj = [1, 2, 3]
        assert get_json_path(obj, "") is obj


# ── parse_json_feed_items ─────────────────────────────────────────────────────


class TestParseJsonFeedItems:
    def test_array_format_root(self):
        content = json.dumps([{"v": "1.2.3.4"}, {"v": "5.6.7.8"}])
        items = parse_json_feed_items(content, {"format": "array", "items_path": ""})
        assert items == [{"v": "1.2.3.4"}, {"v": "5.6.7.8"}]

    def test_array_format_with_path(self):
        content = json.dumps({"data": {"iocs": [{"v": "a"}, {"v": "b"}]}})
        items = parse_json_feed_items(
            content, {"format": "array", "items_path": "data.iocs"}
        )
        assert items == [{"v": "a"}, {"v": "b"}]

    def test_object_format_wraps_in_list(self):
        content = json.dumps({"indicator": "1.2.3.4", "type": "ip-dst"})
        items = parse_json_feed_items(content, {"format": "object", "items_path": ""})
        assert items == [{"indicator": "1.2.3.4", "type": "ip-dst"}]

    def test_object_format_with_path(self):
        content = json.dumps({"data": {"indicator": "1.2.3.4"}})
        items = parse_json_feed_items(
            content, {"format": "object", "items_path": "data"}
        )
        assert items == [{"indicator": "1.2.3.4"}]

    def test_ndjson_format(self):
        content = '{"v":"1.2.3.4"}\n{"v":"5.6.7.8"}\n{"v":"example.com"}'
        items = parse_json_feed_items(content, {"format": "ndjson"})
        assert items == [{"v": "1.2.3.4"}, {"v": "5.6.7.8"}, {"v": "example.com"}]

    def test_ndjson_skips_empty_lines(self):
        content = '{"v":"1.2.3.4"}\n\n{"v":"5.6.7.8"}\n'
        items = parse_json_feed_items(content, {"format": "ndjson"})
        assert len(items) == 2

    def test_ndjson_skips_comment_lines(self):
        content = '# comment\n{"v":"1.2.3.4"}\n# another\n{"v":"5.6.7.8"}'
        items = parse_json_feed_items(content, {"format": "ndjson"})
        assert len(items) == 2

    def test_ndjson_skips_malformed_lines(self):
        content = '{"v":"ok"}\nnot-json\n{"v":"also-ok"}'
        items = parse_json_feed_items(content, {"format": "ndjson"})
        assert len(items) == 2

    def test_array_of_primitives(self):
        content = json.dumps(["1.2.3.4", "5.6.7.8"])
        items = parse_json_feed_items(content, {"format": "array", "items_path": ""})
        assert items == ["1.2.3.4", "5.6.7.8"]

    def test_invalid_json_raises(self):
        with pytest.raises(HTTPException) as exc_info:
            parse_json_feed_items("not-json", {"format": "array", "items_path": ""})
        assert exc_info.value.status_code == 400

    def test_path_not_found_raises(self):
        content = json.dumps({"a": 1})
        with pytest.raises(HTTPException) as exc_info:
            parse_json_feed_items(
                content, {"format": "array", "items_path": "missing"}
            )
        assert exc_info.value.status_code == 400

    def test_non_array_non_object_at_path_raises(self):
        content = json.dumps({"data": "string-not-array"})
        with pytest.raises(HTTPException) as exc_info:
            parse_json_feed_items(
                content, {"format": "array", "items_path": "data"}
            )
        assert exc_info.value.status_code == 400

    def test_default_format_is_array(self):
        content = json.dumps([{"v": "x"}])
        items = parse_json_feed_items(content, {})
        assert items == [{"v": "x"}]


# ── process_json_item_to_attribute ────────────────────────────────────────────


FIXED_SETTINGS = {
    "jsonConfig": {
        "attribute": {
            "value": "indicator",
            "type": {"strategy": "fixed", "value": "ip-dst", "mappings": []},
            "properties": {"comment": None, "tags": None, "to_ids": None},
        }
    }
}


class TestProcessJsonItemToAttribute:
    def test_fixed_type(self):
        result = process_json_item_to_attribute(
            {"indicator": "1.2.3.4"}, FIXED_SETTINGS
        )
        assert result["value"] == "1.2.3.4"
        assert result["type"] == "ip-dst"

    def test_field_type(self):
        settings = {
            "jsonConfig": {
                "attribute": {
                    "value": "indicator",
                    "type": {"strategy": "field", "field": "type", "mappings": []},
                    "properties": {},
                }
            }
        }
        result = process_json_item_to_attribute(
            {"indicator": "1.2.3.4", "type": "ip-src"}, settings
        )
        assert result["value"] == "1.2.3.4"
        assert result["type"] == "ip-src"

    def test_field_type_with_mappings(self):
        settings = {
            "jsonConfig": {
                "attribute": {
                    "value": "ioc",
                    "type": {
                        "strategy": "field",
                        "field": "kind",
                        "mappings": [
                            {"from": "ip", "to": "ip-dst"},
                            {"from": "domain", "to": "domain"},
                        ],
                    },
                    "properties": {},
                }
            }
        }
        result = process_json_item_to_attribute({"ioc": "1.2.3.4", "kind": "ip"}, settings)
        assert result["type"] == "ip-dst"

    def test_field_type_unmapped_value_passes_through(self):
        settings = {
            "jsonConfig": {
                "attribute": {
                    "value": "ioc",
                    "type": {
                        "strategy": "field",
                        "field": "kind",
                        "mappings": [{"from": "ip", "to": "ip-dst"}],
                    },
                    "properties": {},
                }
            }
        }
        result = process_json_item_to_attribute(
            {"ioc": "example.com", "kind": "domain"}, settings
        )
        assert result["type"] == "domain"

    def test_missing_value_field_returns_error(self):
        result = process_json_item_to_attribute({"other": "x"}, FIXED_SETTINGS)
        assert result["value"] is None
        assert "error" in result

    def test_missing_type_field_returns_error(self):
        settings = {
            "jsonConfig": {
                "attribute": {
                    "value": "ioc",
                    "type": {"strategy": "field", "field": "missing_type", "mappings": []},
                    "properties": {},
                }
            }
        }
        result = process_json_item_to_attribute({"ioc": "1.2.3.4"}, settings)
        assert result["type"] is None
        assert "error" in result

    def test_nested_value_path(self):
        settings = {
            "jsonConfig": {
                "attribute": {
                    "value": "data.indicator",
                    "type": {"strategy": "fixed", "value": "domain", "mappings": []},
                    "properties": {},
                }
            }
        }
        result = process_json_item_to_attribute(
            {"data": {"indicator": "example.com"}}, settings
        )
        assert result["value"] == "example.com"

    def test_primitive_item_empty_path(self):
        settings = {
            "jsonConfig": {
                "attribute": {
                    "value": "",
                    "type": {"strategy": "fixed", "value": "ip-dst", "mappings": []},
                    "properties": {},
                }
            }
        }
        result = process_json_item_to_attribute("1.2.3.4", settings)
        assert result["value"] == "1.2.3.4"
        assert result["type"] == "ip-dst"

    def test_primitive_item_with_path_returns_error(self):
        settings = {
            "jsonConfig": {
                "attribute": {
                    "value": "someField",
                    "type": {"strategy": "fixed", "value": "ip-dst", "mappings": []},
                    "properties": {},
                }
            }
        }
        result = process_json_item_to_attribute("1.2.3.4", settings)
        assert result["value"] is None
        assert "error" in result

    def test_comment_fixed(self):
        settings = {
            "jsonConfig": {
                "attribute": {
                    "value": "ioc",
                    "type": {"strategy": "fixed", "value": "ip-dst", "mappings": []},
                    "properties": {
                        "comment": {"strategy": "fixed", "value": "from feed"},
                        "tags": None,
                        "to_ids": None,
                    },
                }
            }
        }
        result = process_json_item_to_attribute({"ioc": "1.2.3.4"}, settings)
        assert result["comment"] == "from feed"

    def test_comment_from_field(self):
        settings = {
            "jsonConfig": {
                "attribute": {
                    "value": "ioc",
                    "type": {"strategy": "fixed", "value": "ip-dst", "mappings": []},
                    "properties": {
                        "comment": {"strategy": "field", "field": "description"},
                        "tags": None,
                        "to_ids": None,
                    },
                }
            }
        }
        result = process_json_item_to_attribute(
            {"ioc": "1.2.3.4", "description": "malicious host"}, settings
        )
        assert result["comment"] == "malicious host"

    def test_tags_fixed(self):
        settings = {
            "jsonConfig": {
                "attribute": {
                    "value": "ioc",
                    "type": {"strategy": "fixed", "value": "ip-dst", "mappings": []},
                    "properties": {
                        "comment": None,
                        "tags": {"strategy": "fixed", "value": ["tlp:white", "feed"]},
                        "to_ids": None,
                    },
                }
            }
        }
        result = process_json_item_to_attribute({"ioc": "1.2.3.4"}, settings)
        assert result["tags"] == ["tlp:white", "feed"]

    def test_tags_from_field_as_list(self):
        settings = {
            "jsonConfig": {
                "attribute": {
                    "value": "ioc",
                    "type": {"strategy": "fixed", "value": "ip-dst", "mappings": []},
                    "properties": {
                        "comment": None,
                        "tags": {"strategy": "field", "field": "tags"},
                        "to_ids": None,
                    },
                }
            }
        }
        result = process_json_item_to_attribute(
            {"ioc": "1.2.3.4", "tags": ["tlp:white", "feed"]}, settings
        )
        assert result["tags"] == ["tlp:white", "feed"]

    def test_tags_from_field_as_comma_string(self):
        settings = {
            "jsonConfig": {
                "attribute": {
                    "value": "ioc",
                    "type": {"strategy": "fixed", "value": "ip-dst", "mappings": []},
                    "properties": {
                        "comment": None,
                        "tags": {"strategy": "field", "field": "tags"},
                        "to_ids": None,
                    },
                }
            }
        }
        result = process_json_item_to_attribute(
            {"ioc": "1.2.3.4", "tags": "tlp:white, feed"}, settings
        )
        assert result["tags"] == ["tlp:white", "feed"]

    def test_to_ids_fixed_true(self):
        settings = {
            "jsonConfig": {
                "attribute": {
                    "value": "ioc",
                    "type": {"strategy": "fixed", "value": "ip-dst", "mappings": []},
                    "properties": {
                        "comment": None,
                        "tags": None,
                        "to_ids": {"strategy": "fixed", "value": True},
                    },
                }
            }
        }
        result = process_json_item_to_attribute({"ioc": "1.2.3.4"}, settings)
        assert result["to_ids"] is True

    def test_to_ids_from_field_truthy_string(self):
        settings = {
            "jsonConfig": {
                "attribute": {
                    "value": "ioc",
                    "type": {"strategy": "fixed", "value": "ip-dst", "mappings": []},
                    "properties": {
                        "comment": None,
                        "tags": None,
                        "to_ids": {"strategy": "field", "field": "ids"},
                    },
                }
            }
        }
        for truthy in ("1", "true", "yes", "True", "YES"):
            result = process_json_item_to_attribute(
                {"ioc": "1.2.3.4", "ids": truthy}, settings
            )
            assert result["to_ids"] is True, f"Expected True for '{truthy}'"

    def test_to_ids_from_field_falsy_string(self):
        settings = {
            "jsonConfig": {
                "attribute": {
                    "value": "ioc",
                    "type": {"strategy": "fixed", "value": "ip-dst", "mappings": []},
                    "properties": {
                        "comment": None,
                        "tags": None,
                        "to_ids": {"strategy": "field", "field": "ids"},
                    },
                }
            }
        }
        result = process_json_item_to_attribute({"ioc": "1.2.3.4", "ids": "false"}, settings)
        assert result["to_ids"] is False
