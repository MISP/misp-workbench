"""Unit tests for the auto-create-on-tag path in ``app/repositories/tags.py``."""

import hashlib
from unittest.mock import MagicMock, patch

from app.repositories import tags as tags_repository


class TestDefaultTagColour:
    def test_returns_hex_prefixed_seven_char_string(self):
        colour = tags_repository._default_tag_colour("tlp:red")
        assert colour.startswith("#")
        assert len(colour) == 7

    def test_is_deterministic(self):
        a = tags_repository._default_tag_colour("osint:source-type=\"blog-post\"")
        b = tags_repository._default_tag_colour("osint:source-type=\"blog-post\"")
        assert a == b

    def test_different_names_produce_different_colours(self):
        # Not strictly guaranteed (md5 collisions exist) but trivially true for
        # short distinct inputs and protects against e.g. constant returns.
        a = tags_repository._default_tag_colour("foo")
        b = tags_repository._default_tag_colour("bar")
        assert a != b

    def test_uses_md5_prefix(self):
        # Pin the algorithm so a future swap is intentional.
        name = "campaign:ursnif"
        expected = "#" + hashlib.md5(name.encode("utf-8")).hexdigest()[:6]
        assert tags_repository._default_tag_colour(name) == expected


class TestGetOrCreateTagByName:
    def test_returns_existing_tag_without_creating(self):
        db = MagicMock()
        existing = MagicMock(name="existing-tag")
        with patch.object(
            tags_repository, "get_tag_by_name", return_value=existing
        ) as get_by_name, patch.object(
            tags_repository, "create_tag"
        ) as create_tag:
            result = tags_repository.get_or_create_tag_by_name(db, "tlp:red")

        assert result is existing
        get_by_name.assert_called_once_with(db, tag_name="tlp:red")
        create_tag.assert_not_called()

    def test_creates_tag_with_defaults_when_missing(self):
        db = MagicMock()
        created = MagicMock(name="created-tag")
        with patch.object(
            tags_repository, "get_tag_by_name", return_value=None
        ), patch.object(
            tags_repository, "create_tag", return_value=created
        ) as create_tag:
            result = tags_repository.get_or_create_tag_by_name(db, "new:tag")

        assert result is created
        create_tag.assert_called_once()
        passed_db, passed_schema = create_tag.call_args.args
        assert passed_db is db
        assert passed_schema.name == "new:tag"
        assert passed_schema.colour == tags_repository._default_tag_colour("new:tag")
        assert passed_schema.exportable is True
        assert passed_schema.hide_tag is False
        assert passed_schema.is_galaxy is False
        assert passed_schema.is_custom_galaxy is False
        assert passed_schema.local_only is False
