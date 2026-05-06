"""Unit tests for reactor service helpers (no DB)."""

from unittest.mock import MagicMock

import pytest
from app.services.tech_lab.reactor import sandbox, triggers


class TestSandbox:
    def test_restricted_builtins_includes_safe(self):
        b = sandbox.restricted_builtins()
        assert "len" in b and "print" in b and "range" in b
        assert "True" in b and "False" in b and "None" in b

    def test_restricted_builtins_excludes_dangerous(self):
        b = sandbox.restricted_builtins()
        # The whitelist is intentionally narrow — it must not include open/import.
        for name in ("open", "exec", "eval", "compile", "__import__"):
            assert name not in b

    def test_time_limit_raises_on_overrun(self):
        import time

        with pytest.raises(sandbox.ScriptTimeout):
            with sandbox.time_limit(1):
                time.sleep(2)

    def test_time_limit_ok_when_under(self):
        with sandbox.time_limit(2):
            x = sum(range(100))
        assert x == sum(range(100))


class TestTriggerMatching:
    def test_has_trigger_matches_resource_and_action(self):
        ts = [{"resource_type": "attribute", "action": "created"}]
        assert triggers._has_trigger(ts, "attribute", "created") is True
        assert triggers._has_trigger(ts, "attribute", "updated") is False
        assert triggers._has_trigger(ts, "event", "created") is False

    def test_filters_pass_tag(self):
        ts = [
            {
                "resource_type": "event",
                "action": "published",
                "filters": {"tag": "tlp:red"},
            }
        ]
        match_red = {"tags": [{"name": "tlp:red"}]}
        match_amber = {"tags": [{"name": "tlp:amber"}]}
        assert triggers.matches_filters(ts, "event", "published", match_red) is True
        assert triggers.matches_filters(ts, "event", "published", match_amber) is False

    def test_filters_pass_type(self):
        ts = [
            {
                "resource_type": "attribute",
                "action": "created",
                "filters": {"type": "ip-src"},
            }
        ]
        assert triggers.matches_filters(ts, "attribute", "created", {"type": "ip-src"}) is True
        assert (
            triggers.matches_filters(ts, "attribute", "created", {"type": "url"}) is False
        )

    def test_no_filters_matches(self):
        ts = [{"resource_type": "event", "action": "created"}]
        assert triggers.matches_filters(ts, "event", "created", {}) is True

    def test_org_filter(self):
        ts = [
            {
                "resource_type": "event",
                "action": "created",
                "filters": {"org": "ACME"},
            }
        ]
        assert (
            triggers.matches_filters(ts, "event", "created", {"orgc": {"name": "ACME"}})
            is True
        )
        assert (
            triggers.matches_filters(ts, "event", "created", {"orgc": {"name": "OTHER"}})
            is False
        )

    def test_list_active_scripts_filters_by_status(self):
        active = MagicMock(status="active", triggers=[{"resource_type": "event", "action": "created"}])
        unrelated = MagicMock(status="active", triggers=[{"resource_type": "attribute", "action": "created"}])
        db = MagicMock()
        # SQLAlchemy chain: db.query(...).filter(...).all()
        chain = db.query.return_value.filter.return_value
        chain.all.return_value = [active, unrelated]
        result = triggers.list_active_scripts_for(db, "event", "created")
        assert result == [active]
