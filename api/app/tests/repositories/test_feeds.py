from unittest.mock import MagicMock, patch

from uuid import UUID

from app.models import feed as feed_models
from app.models import tag as tag_models
from app.models import user as user_models
from app.repositories import attributes as attributes_repository
from app.repositories import events as events_repository
from app.repositories import feeds as feeds_repository
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

            # check the object references were created
            from app.repositories import object_references as object_references_repository
            object_reference = object_references_repository.get_object_reference_by_uuid(
                db, UUID("d7e57f39-4dd5-4b87-b040-75561fa8289e")
            )
            assert object_reference is not None

            # check the tags were created
            tags = db.query(tag_models.Tag).all()
            assert len(tags) == 4

            # check the event tags were created
            event_tags = (
                db.query(tag_models.Tag)
                .join(tag_models.EventTag)
                .filter(
                    tag_models.Tag.name.in_(["type:OSINT", "tlp:clear", "tlp:white"]),
                )
                .all()
            )
            assert len(event_tags) == 3

            # check the attribute tags were created
            attribute_tags = (
                db.query(tag_models.Tag)
                .join(tag_models.AttributeTag)
                .filter(
                    tag_models.Tag.name.in_(["tlp:red"]),
                )
                .all()
            )
            assert len(attribute_tags) == 1

    def test_fetch_feed_by_id_existing_event(
        self,
        db: Session,
        feed_1: feed_models.Feed,
        event_1,
        attribute_1,
        object_1: object_models.Object,
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
            object = (
                db.query(object_models.Object)
                .filter(
                    object_models.Object.uuid == "90e06ef6-26f8-40dd-9fb7-75897445e2a0"
                )
                .first()
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
                db.query(object_reference_models.ObjectReference)
                .filter(
                    object_reference_models.ObjectReference.uuid
                    == "4d4c12b9-e514-496e-a8a6-06d5c6815b97"
                )
                .first()
            )
            assert (
                str(object_reference.referenced_uuid)
                == "7f2fd15d-3c63-47ba-8a39-2c4b0b3314b0"
            )

            # check the event tags were created
            event_tags = (
                db.query(tag_models.Tag)
                .join(tag_models.EventTag)
                .filter(
                    tag_models.Tag.name.in_(["EVENT_FEED_ADDED_TAG"]),
                )
                .all()
            )
            assert len(event_tags) == 1

            # check the attribute tags were created
            attribute_tags = (
                db.query(tag_models.Tag)
                .join(tag_models.AttributeTag)
                .filter(
                    tag_models.Tag.name.in_(
                        [
                            "ATTRIBUTE_EVENT_FEED_ADDED_TAG",
                            "OBJECT_ATTRIBUTE_EVENT_FEED_ADDED_TAG",
                        ]
                    ),
                )
                .all()
            )
            assert len(attribute_tags) == 2
