from unittest.mock import MagicMock, patch

from app.models import attribute as attribute_models
from app.models import event as event_models
from app.models import feed as feed_models
from app.models import object as object_models
from app.models import object_reference as object_reference_models
from app.models import tag as tag_models
from app.models import user as user_models
from app.repositories import feeds as feeds_repository
from app.tests.api_tester import ApiTester
from sqlalchemy.orm import Session

feed_manifest = {
    "988ce14e-0802-4aa3-92ca-8ca1104e0b38": {
        "Orgc": {"name": "CIRCL", "uuid": "22bdfb84-98d9-468c-aba4-986e63ffea62"},
        "Tag": [
            {
                "colour": "#004646",
                "local": False,
                "name": "type:OSINT",
                "relationship_type": "",
            },
            {
                "colour": "#ffffff",
                "local": False,
                "name": "tlp:white",
                "relationship_type": "",
            },
            {
                "colour": "#ffffff",
                "local": False,
                "name": "tlp:clear",
                "relationship_type": "",
            },
        ],
        "info": "Test Feed Event",
        "date": "2024-08-27",
        "analysis": 0,
        "threat_level_id": 3,
        "timestamp": 1724753268,
    }
}


feed_event = {
    "Event": {
        "analysis": "0",
        "date": "2024-08-27",
        "extends_uuid": "",
        "info": "Test Feed Event",
        "publish_timestamp": "1724758165",
        "published": True,
        "threat_level_id": "3",
        "timestamp": "1724753268",
        "uuid": "988ce14e-0802-4aa3-92ca-8ca1104e0b38",
        "Orgc": {"name": "CIRCL", "uuid": "22bdfb84-98d9-468c-aba4-986e63ffea62"},
        "Tag": [
            {
                "colour": "#004646",
                "local": False,
                "name": "type:OSINT",
                "relationship_type": "",
            },
            {
                "colour": "#ffffff",
                "local": False,
                "name": "tlp:white",
                "relationship_type": "",
            },
            {
                "colour": "#ffffff",
                "local": False,
                "name": "tlp:clear",
                "relationship_type": "",
            },
        ],
        "Attribute": [
            {
                "category": "Payload delivery",
                "comment": "Original RAR file",
                "deleted": False,
                "disable_correlation": False,
                "timestamp": "1724749019",
                "to_ids": True,
                "type": "sha1",
                "uuid": "317e63e6-b95d-4dd1-b4fd-de2f64f33fd8",
                "value": "7edc546f741eff3e13590a62ce2856bb39d8f71d",
                "Tag": [
                    {
                        "colour": "#004646",
                        "local": False,
                        "name": "tlp:red",
                        "relationship_type": "",
                    },
                ],
            }
        ],
        "Object": [
            {
                "comment": "Malicious account posting malicious links (compromise?)",
                "deleted": False,
                "description": "GitHub user",
                "meta-category": "misc",
                "name": "github-user",
                "template_uuid": "4329b5e6-8e6a-4b55-8fd1-9033782017d4",
                "template_version": "3",
                "timestamp": "1724749149",
                "uuid": "df23d3be-1179-4824-ac03-471f0bc6d92d",
                "ObjectReference": [
                    {
                        "comment": "",
                        "object_uuid": "df23d3be-1179-4824-ac03-471f0bc6d92d",
                        "referenced_uuid": "317e63e6-b95d-4dd1-b4fd-de2f64f33fd8",
                        "relationship_type": "mentions",
                        "timestamp": "1724749149",
                        "uuid": "d7e57f39-4dd5-4b87-b040-75561fa8289e",
                    }
                ],
                "Attribute": [
                    {
                        "category": "Social network",
                        "comment": "",
                        "deleted": False,
                        "disable_correlation": False,
                        "object_relation": "username",
                        "timestamp": "1724748475",
                        "to_ids": False,
                        "type": "github-username",
                        "uuid": "8be7a04d-c10b-4ef6-854f-2072e67f6cd5",
                        "value": "Foobar12345",
                    }
                ],
            },
        ],
    }
}


class TestFeedsRepository(ApiTester):

    def test_fetch_feed_by_id(
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
                json=MagicMock(return_value=feed_manifest),
                status_code=200,
            )
            # mock remote Feed API calls
            mock_fetch_event_by_uuid.return_value = feed_event

            feeds_repository.fetch_feed(db, feed_1.id, user_1)

            # check that the events were created
            events = (
                db.query(event_models.Event)
                .filter(event_models.Event.uuid == feed_event["Event"]["uuid"])
                .all()
            )
            assert len(events) == 1

            # check that the attributes were created
            attributes = (
                db.query(attribute_models.Attribute)
                .filter(
                    attribute_models.Attribute.uuid.in_(
                        [
                            "317e63e6-b95d-4dd1-b4fd-de2f64f33fd8",
                            "8be7a04d-c10b-4ef6-854f-2072e67f6cd5",
                        ]
                    )
                )
                .all()
            )
            assert len(attributes) == 2

            # check the objects were created
            objects = (
                db.query(object_models.Object)
                .filter(
                    object_models.Object.uuid == "df23d3be-1179-4824-ac03-471f0bc6d92d"
                )
                .all()
            )
            assert len(objects) == 1

            # check the object references were created
            object_references = (
                db.query(object_reference_models.ObjectReference)
                .filter(
                    object_reference_models.ObjectReference.uuid
                    == "d7e57f39-4dd5-4b87-b040-75561fa8289e"
                )
                .all()
            )
            assert len(object_references) == 1

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
