from unittest.mock import MagicMock, patch

from uuid import UUID

from app.models import feed as feed_models
from app.models import tag as tag_models
from app.models import user as user_models
from app.repositories import attributes as attributes_repository
from app.repositories import analyst_data as analyst_data_repository
from app.repositories import events as events_repository
from app.repositories import feeds as feeds_repository
from app.repositories import object_references as object_references_repository
from app.repositories import objects as objects_repository
from app.tests.api_tester import ApiTester
from app.tests.scenarios import feed_fetch_scenarios
from sqlalchemy.orm import Session


class TestFeedsRepository(ApiTester):

    def test_fetch_feed_by_id_new_event(
        self,
        db: Session,
        feed_1: feed_models.Feed,
        user_1: user_models.User,
    ):

        # mock remote Feed API calls
        with patch(
            "app.repositories.feeds.get_feed_manifest"
        ) as mock_requests_get_feed_manifest, patch(
            "app.repositories.feeds.fetch_feed_event_by_uuid"
        ) as mock_fetch_event_by_uuid:
            mock_requests_get_feed_manifest.return_value = MagicMock(
                # get feed manifest
                json=MagicMock(
                    return_value=feed_fetch_scenarios.feed_new_event_manifest
                ),
                status_code=200,
            )
            # mock remote Feed API calls
            mock_fetch_event_by_uuid.return_value = feed_fetch_scenarios.feed_new_event

            feeds_repository.process_feed_event(
                db, "988ce14e-0802-4aa3-92ca-8ca1104e0b38", feed_1, user_1
            )

            # check that the events were created
            os_event = events_repository.get_event_from_opensearch(
                UUID(feed_fetch_scenarios.feed_new_event["Event"]["uuid"])
            )
            assert os_event is not None

            # check that the attributes were created
            attributes = [
                attributes_repository.get_attribute_from_opensearch(UUID(u))
                for u in [
                    "317e63e6-b95d-4dd1-b4fd-de2f64f33fd8",
                    "8be7a04d-c10b-4ef6-854f-2072e67f6cd5",
                ]
            ]
            assert len([a for a in attributes if a is not None]) == 2

            # check the objects were created
            obj = objects_repository.get_object_from_opensearch(
                UUID("df23d3be-1179-4824-ac03-471f0bc6d92d")
            )
            assert obj is not None

            # check the analyst data was captured, threads included
            event_uuid = feed_fetch_scenarios.feed_new_event["Event"]["uuid"]
            captured = {
                d["uuid"]: d
                for d in analyst_data_repository.get_all_analyst_data_for_event(
                    event_uuid
                )
            }
            assert {
                "c1a11111-1111-4111-8111-111111111111",
                "c1a22222-2222-4222-8222-222222222222",
                "c1a33333-3333-4333-8333-333333333333",
                "c1a44444-4444-4444-8444-444444444444",
                "c1a55555-5555-4555-8555-555555555555",
                "c1a66666-6666-4666-8666-666666666666",
            }.issubset(captured.keys())

            # a feed fetch is not a server pull, so the distribution is kept
            assert captured["c1a11111-1111-4111-8111-111111111111"]["distribution"] == 3
            assert captured["c1a44444-4444-4444-8444-444444444444"]["opinion"] == 25
            assert (
                captured["c1a55555-5555-4555-8555-555555555555"]["relationship_type"]
                == "related-to"
            )

            threads = analyst_data_repository.get_analyst_data_by_event_uuid(event_uuid)
            assert [n.uuid for n in threads.notes] == [
                "c1a11111-1111-4111-8111-111111111111"
            ]
            assert [o.uuid for o in threads.opinions] == [
                "c1a44444-4444-4444-8444-444444444444"
            ]
            assert [r.uuid for r in threads.relationships] == [
                "c1a55555-5555-4555-8555-555555555555"
            ]

            # the nested reply and opinion hang off the event note
            event_note = threads.notes[0]
            assert [n.uuid for n in event_note.notes] == [
                "c1a22222-2222-4222-8222-222222222222"
            ]
            assert [o.uuid for o in event_note.opinions] == [
                "c1a33333-3333-4333-8333-333333333333"
            ]

            # analyst data on an attribute is read by the attribute uuid
            attribute_threads = analyst_data_repository.get_analyst_data_by_object_uuid(
                "317e63e6-b95d-4dd1-b4fd-de2f64f33fd8", "Attribute"
            )
            assert "c1a66666-6666-4666-8666-666666666666" in {
                n.uuid for n in attribute_threads.notes
            }

            # check the object references were created
            object_reference = (
                object_references_repository.get_object_reference_by_uuid(
                    db, UUID("d7e57f39-4dd5-4b87-b040-75561fa8289e")
                )
            )
            assert object_reference is not None

            # check the tags were created
            tags = db.query(tag_models.Tag).all()
            assert len(tags) == 4

            # check the event tags were created
            os_event = events_repository.get_event_from_opensearch(
                UUID(feed_fetch_scenarios.feed_new_event["Event"]["uuid"])
            )
            event_tag_names = {t.name for t in (os_event.tags or [])}
            assert {"type:OSINT", "tlp:clear", "tlp:white"}.issubset(event_tag_names)

            # check the attribute tags were created
            all_attribute_tag_names = set()
            for uuid in [
                "317e63e6-b95d-4dd1-b4fd-de2f64f33fd8",
                "8be7a04d-c10b-4ef6-854f-2072e67f6cd5",
            ]:
                attr = attributes_repository.get_attribute_from_opensearch(UUID(uuid))
                if attr:
                    for t in attr.tags or []:
                        all_attribute_tag_names.add(t.name)
            assert "tlp:red" in all_attribute_tag_names

    def test_fetch_feed_by_id_existing_event(
        self,
        db: Session,
        feed_1: feed_models.Feed,
        event_1,
        attribute_1,
        object_1,
        object_attribute_1,
        user_1: user_models.User,
    ):
        # mock remote Feed API calls
        with patch(
            "app.repositories.feeds.get_feed_manifest"
        ) as mock_requests_get_feed_manifest, patch(
            "app.repositories.feeds.fetch_feed_event_by_uuid"
        ) as mock_fetch_event_by_uuid:
            mock_requests_get_feed_manifest.return_value = MagicMock(
                # get feed manifest
                json=MagicMock(
                    return_value=feed_fetch_scenarios.feed_update_event_manifest
                ),
                status_code=200,
            )
            # mock remote Feed API calls
            mock_fetch_event_by_uuid.return_value = (
                feed_fetch_scenarios.feed_update_event
            )

            feeds_repository.fetch_feed(db, feed_1.id, user_1)
            feeds_repository.process_feed_event(
                db, "ba4b11b6-dcce-4315-8fd0-67b69160ea76", feed_1, user_1
            )

            # check that the events was updated
            os_event = events_repository.get_event_from_opensearch(
                UUID(feed_fetch_scenarios.feed_update_event["Event"]["uuid"])
            )
            assert os_event is not None
            assert os_event.info == "Updated by Feed fetch"
            assert os_event.timestamp == 1577836801

            # check that the attribute was updated
            attribute = attributes_repository.get_attribute_from_opensearch(
                UUID("7f2fd15d-3c63-47ba-8a39-2c4b0b3314b0")
            )
            assert attribute is not None
            assert attribute.value == "7edc546f741eff3e13590a62ce2856bb39d8f71d"
            assert attribute.timestamp == 1577836801

            # check the object was updated
            object = objects_repository.get_object_from_opensearch(
                UUID("90e06ef6-26f8-40dd-9fb7-75897445e2a0")
            )
            assert object.comment == "Object comment updated by Feed fetch"
            assert object.timestamp == 1577836801

            # check the object attribute was added
            object_attribute = attributes_repository.get_attribute_from_opensearch(
                UUID("011aca4f-eaf0-4a06-8133-b69f3806cbe8")
            )
            assert object_attribute is not None
            assert object_attribute.value == "Foobar12345"
            assert object_attribute.timestamp == 1577836801

            # check the object references were created
            object_reference = (
                object_references_repository.get_object_reference_by_uuid(
                    db, UUID("4d4c12b9-e514-496e-a8a6-06d5c6815b97")
                )
            )
            assert (
                str(object_reference.referenced_uuid)
                == "7f2fd15d-3c63-47ba-8a39-2c4b0b3314b0"
            )

            # check the event tags were created
            os_event = events_repository.get_event_from_opensearch(
                UUID(feed_fetch_scenarios.feed_update_event["Event"]["uuid"])
            )
            event_tag_names = {t.name for t in (os_event.tags or [])}
            assert "EVENT_FEED_ADDED_TAG" in event_tag_names

            # check the attribute tags were created
            all_attribute_tag_names = set()
            for uuid in [
                "7f2fd15d-3c63-47ba-8a39-2c4b0b3314b0",
                "011aca4f-eaf0-4a06-8133-b69f3806cbe8",
            ]:
                attr = attributes_repository.get_attribute_from_opensearch(UUID(uuid))
                if attr:
                    for t in attr.tags or []:
                        all_attribute_tag_names.add(t.name)
            assert "ATTRIBUTE_EVENT_FEED_ADDED_TAG" in all_attribute_tag_names
            assert "OBJECT_ATTRIBUTE_EVENT_FEED_ADDED_TAG" in all_attribute_tag_names


def _csv_settings(**csv_config) -> dict:
    """A CSV preview request whose rows are read from a local file.

    `csv_config` is merged into `csvConfig`, so a test can leave `header` out
    entirely to cover a config written before the key existed.
    """
    config = {
        "mode": "attribute",
        "delimiter": ",",
        "attribute": {
            "value_column": 0,
            "type": {"strategy": "fixed", "value": "ip-dst", "mappings": []},
            "properties": {
                "timestamp": {"strategy": "fixed", "value": 0},
                "comment": None,
                "tags": None,
                "to_ids": None,
                "first_seen": None,
                "last_seen": None,
            },
        },
    }
    config.update(csv_config)
    return {"input_source": "local", "url": "key", "settings": {"csvConfig": config}}


class TestCsvFeedHasHeader:
    def test_reads_the_flag(self):
        assert feeds_repository.csv_feed_has_header({"csvConfig": {"header": True}})
        assert not feeds_repository.csv_feed_has_header(
            {"csvConfig": {"header": False}}
        )

    def test_a_missing_key_means_no_header(self):
        # configs stored before the flag existed must not raise
        assert not feeds_repository.csv_feed_has_header({"csvConfig": {}})


class TestPreviewCsvFeed:
    """
    `preview` is what would be imported, so it must skip the header row the
    same way `fetch_csv_feed` does. `rows` keeps it: the feed wizard reads
    rows[0] to label the columns and slices it off itself.
    """

    LINES = ["value", "1.1.1.1", "2.2.2.2", "3.3.3.3", "4.4.4.4", "5.5.5.5"]

    def _preview(self, settings, limit=5):
        with patch.object(
            feeds_repository, "fetch_csv_content_from_local", return_value=self.LINES
        ):
            return feeds_repository.preview_csv_feed(settings, limit=limit)

    def test_header_row_is_not_previewed_as_an_attribute(self):
        result = self._preview(_csv_settings(header=True))

        assert [row["value"] for row in result["preview"]] == [
            "1.1.1.1",
            "2.2.2.2",
            "3.3.3.3",
            "4.4.4.4",
            "5.5.5.5",
        ]

    def test_header_row_is_still_returned_in_rows(self):
        # the wizard derives the column labels from it
        result = self._preview(_csv_settings(header=True))

        assert result["rows"][0] == ["value"]

    def test_a_header_does_not_cost_a_data_row(self):
        # the header used to eat one of the `limit` slots, so a 3-row preview
        # showed the header plus only 2 real rows
        result = self._preview(_csv_settings(header=True), limit=3)

        assert [row["value"] for row in result["preview"]] == [
            "1.1.1.1",
            "2.2.2.2",
            "3.3.3.3",
        ]

    def test_every_row_is_previewed_when_there_is_no_header(self):
        result = self._preview(_csv_settings(header=False), limit=3)

        assert [row["value"] for row in result["preview"]] == [
            "value",
            "1.1.1.1",
            "2.2.2.2",
        ]

    def test_a_missing_header_key_is_treated_as_no_header(self):
        result = self._preview(_csv_settings(), limit=3)

        assert [row["value"] for row in result["preview"]] == [
            "value",
            "1.1.1.1",
            "2.2.2.2",
        ]
