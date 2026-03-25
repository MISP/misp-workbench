"""Phase 0 regression harness: verifies that index_event produces OpenSearch
documents that are fully consistent with the PostgreSQL source of truth.

Each test creates SQL fixtures, calls index_event synchronously (full_reindex),
then fetches the indexed documents and asserts field-level parity.

Run with:
    docker compose exec api poetry run pytest tests/api/test_indexing_parity.py -v
"""
import pytest
from app.models import attribute as attribute_models
from app.models import event as event_models
from app.models import object as object_models
from app.models import object_reference as object_reference_models
from app.models import tag as tag_models
from app.tests.api_tester import ApiTester
from app.worker.tasks import index_attribute, index_event, index_object
from sqlalchemy.orm import Session


def _os_client():
    from app.services.opensearch import get_opensearch_client

    return get_opensearch_client()


class TestIndexingParity(ApiTester):
    """Assert SQL ↔ OpenSearch parity for events, attributes, and objects."""

    # ── cleanup ────────────────────────────────────────────────────────────────

    @pytest.fixture(scope="class", autouse=True)
    def cleanup(self, db: Session):
        # Runs at class setup time (same pattern as ApiTester.cleanup) so that
        # leftover data from a previous test class is wiped before our fixtures
        # try to insert rows with the same hardcoded UUIDs / info strings.
        try:
            pass
        finally:
            os = _os_client()
            for index in ("misp-events", "misp-attributes", "misp-objects"):
                try:
                    os.delete_by_query(
                        index=index,
                        body={"query": {"match_all": {}}},
                        refresh=True,
                        ignore=[404],
                    )
                except Exception:
                    pass
            self.teardown_db(db)

    # ── event parity ──────────────────────────────────────────────────────────

    def test_event_fields_in_opensearch(
        self,
        db: Session,
        event_1: event_models.Event,
        attribute_1: attribute_models.Attribute,
        object_1: object_models.Object,
        object_attribute_1: attribute_models.Attribute,
        tlp_white_tag: tag_models.Tag,
    ):
        """All scalar event fields must appear in the OS document with correct values."""
        # tag the event so we can assert tag parity too
        event_tag = tag_models.EventTag(
            event_id=event_1.id, tag_id=tlp_white_tag.id, local=False
        )
        db.add(event_tag)
        db.commit()

        index_event(str(event_1.uuid), full_reindex=True)

        os = _os_client()
        doc = os.get(index="misp-events", id=str(event_1.uuid))["_source"]

        assert doc["id"] == event_1.id
        assert doc["uuid"] == str(event_1.uuid)
        assert doc["info"] == event_1.info
        assert doc["org_id"] == event_1.org_id
        assert doc["orgc_id"] == event_1.orgc_id
        assert doc["user_id"] == event_1.user_id
        assert doc["published"] == event_1.published
        assert doc["analysis"] == event_1.analysis.value
        assert doc["distribution"] == event_1.distribution.value
        assert doc["threat_level"] == event_1.threat_level.value
        assert doc["timestamp"] == event_1.timestamp
        assert doc["publish_timestamp"] == event_1.publish_timestamp
        assert doc["deleted"] == event_1.deleted
        assert doc["locked"] == event_1.locked
        assert doc["protected"] == event_1.protected
        assert doc["disable_correlation"] == event_1.disable_correlation
        assert doc["proposal_email_lock"] == event_1.proposal_email_lock
        assert doc.get("sighting_timestamp") == event_1.sighting_timestamp
        assert doc.get("sharing_group_id") == event_1.sharing_group_id
        expected_extends = (
            str(event_1.extends_uuid) if event_1.extends_uuid else None
        )
        assert doc.get("extends_uuid") == expected_extends

    def test_event_tags_in_opensearch(
        self,
        db: Session,
        event_1: event_models.Event,
        tlp_white_tag: tag_models.Tag,
    ):
        """Tags attached to an event must appear in the misp-events document."""
        index_event(str(event_1.uuid), full_reindex=True)

        os = _os_client()
        doc = os.get(index="misp-events", id=str(event_1.uuid))["_source"]

        tag_names = [t["name"] for t in doc.get("tags", [])]
        assert tlp_white_tag.name in tag_names

    def test_event_organisation_in_opensearch(
        self,
        db: Session,
        event_1: event_models.Event,
    ):
        """The organisation nested object must be present in the misp-events document."""
        index_event(str(event_1.uuid), full_reindex=True)

        os = _os_client()
        doc = os.get(index="misp-events", id=str(event_1.uuid))["_source"]

        assert "organisation" in doc
        assert doc["organisation"]["id"] == event_1.org_id

    # ── attribute parity ──────────────────────────────────────────────────────

    def test_standalone_attribute_fields_in_opensearch(
        self,
        db: Session,
        event_1: event_models.Event,
        attribute_1: attribute_models.Attribute,
    ):
        """Standalone (non-object) attribute fields must be consistent in misp-attributes."""
        index_event(str(event_1.uuid), full_reindex=True)

        os = _os_client()
        doc = os.get(index="misp-attributes", id=str(attribute_1.uuid))["_source"]

        assert doc["id"] == attribute_1.id
        assert doc["uuid"] == str(attribute_1.uuid)
        assert doc["event_id"] == attribute_1.event_id
        assert doc["event_uuid"] == str(event_1.uuid)
        assert doc["type"] == attribute_1.type
        assert doc["value"] == attribute_1.value
        assert doc["category"] == attribute_1.category
        assert doc["to_ids"] == attribute_1.to_ids
        assert doc["deleted"] == attribute_1.deleted
        assert doc["disable_correlation"] == attribute_1.disable_correlation
        assert doc["timestamp"] == attribute_1.timestamp
        assert doc["distribution"] == attribute_1.distribution.value
        assert doc.get("sharing_group_id") == attribute_1.sharing_group_id
        assert doc.get("comment") == attribute_1.comment
        assert doc.get("first_seen") == attribute_1.first_seen
        assert doc.get("last_seen") == attribute_1.last_seen
        # standalone attributes must not carry an object_uuid
        assert doc.get("object_uuid") is None

    def test_object_attribute_fields_in_opensearch(
        self,
        db: Session,
        event_1: event_models.Event,
        object_1: object_models.Object,
        object_attribute_1: attribute_models.Attribute,
    ):
        """Object attributes must be in misp-attributes (not embedded in the object doc)
        and must carry both event_uuid and object_uuid."""
        index_event(str(event_1.uuid), full_reindex=True)

        os = _os_client()

        # must exist as a separate document in misp-attributes
        attr_doc = os.get(
            index="misp-attributes", id=str(object_attribute_1.uuid)
        )["_source"]

        assert attr_doc["event_uuid"] == str(event_1.uuid)
        assert attr_doc["object_uuid"] == str(object_1.uuid)
        assert attr_doc["value"] == object_attribute_1.value

    def test_standalone_attribute_object_uuid_via_index_attribute(
        self,
        db: Session,
        event_1: event_models.Event,
        attribute_1: attribute_models.Attribute,
    ):
        """index_attribute must not set object_uuid for standalone attributes."""
        index_attribute(str(attribute_1.uuid))

        os = _os_client()
        doc = os.get(index="misp-attributes", id=str(attribute_1.uuid))["_source"]

        assert doc.get("object_uuid") is None
        assert doc["event_uuid"] == str(event_1.uuid)

    def test_object_attribute_object_uuid_via_index_attribute(
        self,
        db: Session,
        event_1: event_models.Event,
        object_1: object_models.Object,
        object_attribute_1: attribute_models.Attribute,
    ):
        """index_attribute must populate object_uuid for attributes that belong to an object."""
        index_attribute(str(object_attribute_1.uuid))

        os = _os_client()
        doc = os.get(
            index="misp-attributes", id=str(object_attribute_1.uuid)
        )["_source"]

        assert doc["object_uuid"] == str(object_1.uuid)
        assert doc["event_uuid"] == str(event_1.uuid)

    # ── object parity ─────────────────────────────────────────────────────────

    def test_object_fields_in_opensearch(
        self,
        db: Session,
        event_1: event_models.Event,
        object_1: object_models.Object,
    ):
        """Object scalar fields must be consistent between SQL and misp-objects."""
        index_event(str(event_1.uuid), full_reindex=True)

        os = _os_client()
        doc = os.get(index="misp-objects", id=str(object_1.uuid))["_source"]

        assert doc["id"] == object_1.id
        assert doc["uuid"] == str(object_1.uuid)
        assert doc["event_uuid"] == str(event_1.uuid)
        assert doc["name"] == object_1.name
        assert doc["deleted"] == object_1.deleted
        assert doc["timestamp"] == object_1.timestamp
        assert doc["distribution"] == object_1.distribution.value
        assert doc.get("sharing_group_id") == object_1.sharing_group_id
        assert doc.get("meta_category") == object_1.meta_category
        assert doc.get("template_uuid") == object_1.template_uuid
        assert doc.get("template_version") == object_1.template_version
        assert doc.get("first_seen") == object_1.first_seen
        assert doc.get("last_seen") == object_1.last_seen

    def test_object_doc_does_not_contain_attributes(
        self,
        db: Session,
        event_1: event_models.Event,
        object_1: object_models.Object,
        object_attribute_1: attribute_models.Attribute,
    ):
        """Attributes must NOT be embedded inside the misp-objects document; they
        live as top-level documents in misp-attributes."""
        index_event(str(event_1.uuid), full_reindex=True)

        os = _os_client()
        doc = os.get(index="misp-objects", id=str(object_1.uuid))["_source"]

        assert "attributes" not in doc or doc["attributes"] == []

    def test_index_object_task_does_not_embed_attributes(
        self,
        db: Session,
        event_1: event_models.Event,
        object_1: object_models.Object,
        object_attribute_1: attribute_models.Attribute,
    ):
        """index_object (the standalone task) must also not embed attributes."""
        index_object(str(object_1.uuid))

        os = _os_client()
        doc = os.get(index="misp-objects", id=str(object_1.uuid))["_source"]

        assert "attributes" not in doc or doc["attributes"] == []

        # and the attribute must exist separately
        attr_doc = os.get(
            index="misp-attributes", id=str(object_attribute_1.uuid)
        )["_source"]
        assert attr_doc["object_uuid"] == str(object_1.uuid)

    # ── attribute count parity ────────────────────────────────────────────────

    def test_attribute_count_in_event_doc(
        self,
        db: Session,
        event_1: event_models.Event,
        attribute_1: attribute_models.Attribute,
        object_attribute_1: attribute_models.Attribute,
    ):
        """attribute_count in the misp-events document must match the SQL value."""
        db.refresh(event_1)
        index_event(str(event_1.uuid), full_reindex=True)

        os = _os_client()
        doc = os.get(index="misp-events", id=str(event_1.uuid))["_source"]

        assert doc["attribute_count"] == event_1.attribute_count
