"""Serialization contract for MISP's own event API shape.

``to_misp_format()`` is what a remote MISP server, a JSON export and the event
graph all consume, so the exact wire values matter more than the round trip
through our own schemas.
"""

from uuid import UUID

from app.schemas import attribute as attribute_schemas
from app.schemas import event as event_schemas
from app.schemas import object as object_schemas
from app.schemas import object_reference as object_reference_schemas


def make_reference(referenced_type):
    return object_reference_schemas.ObjectReference(
        uuid=UUID("11111111-1111-1111-1111-111111111111"),
        source_uuid=UUID("22222222-2222-2222-2222-222222222222"),
        referenced_uuid=UUID("33333333-3333-3333-3333-333333333333"),
        referenced_type=referenced_type,
        relationship_type="derived-from",
        timestamp=1577836800,
    )


class TestObjectReferenceMispFormat:
    def test_referenced_type_is_the_numeric_level_not_the_enum_name(self):
        as_object = make_reference(object_reference_schemas.ReferencedType.OBJECT)
        as_attribute = make_reference(object_reference_schemas.ReferencedType.ATTRIBUTE)

        assert as_object.to_misp_format()["referenced_type"] == "1"
        assert as_attribute.to_misp_format()["referenced_type"] == "0"

    def test_referenced_type_survives_a_raw_int(self):
        assert make_reference(1).to_misp_format()["referenced_type"] == "1"
        assert make_reference(0).to_misp_format()["referenced_type"] == "0"

    def test_referenced_type_is_none_when_unset(self):
        assert make_reference(None).to_misp_format()["referenced_type"] is None


class TestAttachmentInlining:
    """``include_attachments=False`` has to reach every nested attribute."""

    def make_event(self):
        attachment = attribute_schemas.Attribute(
            category="Payload delivery",
            type="attachment",
            value="invoice.doc",
            uuid=UUID("44444444-4444-4444-4444-444444444444"),
            timestamp=1577836800,
        )
        nested = attribute_schemas.Attribute(
            category="Payload delivery",
            type="malware-sample",
            value="sample.exe|d41d8cd98f00b204e9800998ecf8427e",
            uuid=UUID("55555555-5555-5555-5555-555555555555"),
            timestamp=1577836800,
        )
        misp_object = object_schemas.Object(
            name="file",
            template_version=1,
            uuid=UUID("66666666-6666-6666-6666-666666666666"),
            timestamp=1577836800,
            attributes=[nested],
        )

        return event_schemas.Event(
            info="test event",
            uuid=UUID("77777777-7777-7777-7777-777777777777"),
            timestamp=1577836800,
            attributes=[attachment],
            objects=[misp_object],
        )

    def test_no_data_key_on_any_attribute_when_excluded(self):
        payload = self.make_event().to_misp_format(include_attachments=False)["Event"]

        assert "data" not in payload["Attribute"][0]
        assert "data" not in payload["Object"][0]["Attribute"][0]

    def test_metadata_is_untouched(self):
        payload = self.make_event().to_misp_format(include_attachments=False)["Event"]

        assert payload["Attribute"][0]["value"] == "invoice.doc"
        assert payload["Object"][0]["name"] == "file"
