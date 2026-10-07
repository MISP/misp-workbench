"""Editing an event's content through the API takes it back to unpublished.

As in MISP: a change isn't shared (pushed, sent to sinks) until the event is
published again. Pulls and feeds go through the repositories directly and
keep the published state they bring.
"""

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.auth import auth
from app.repositories import attributes as attributes_repository
from app.repositories import events as events_repository
from app.schemas import attribute as attribute_schemas
from app.services.opensearch import get_opensearch_client
from app.tests.api_tester import ApiTester

EDIT_SCOPES = [
    "events:update",
    "attributes:create",
    "attributes:update",
    "attributes:delete",
    "objects:create",
    "objects:update",
    "objects:delete",
]


def _publish(event_uuid) -> None:
    get_opensearch_client().update(
        index="misp-events",
        id=str(event_uuid),
        body={"doc": {"published": True}},
        refresh=True,
    )


def _published(event_uuid) -> bool:
    return events_repository.get_event_from_opensearch(event_uuid).published


class TestUnpublishOnEdit(ApiTester):
    def _headers(self, token):
        return {"Authorization": "Bearer " + token}

    def _new_attribute(self, client, token, event_uuid, value):
        response = client.post(
            "/attributes/",
            json={
                "event_uuid": str(event_uuid),
                "category": "Network activity",
                "type": "ip-dst",
                "value": value,
            },
            headers=self._headers(token),
        )
        assert response.status_code == status.HTTP_201_CREATED, response.text
        return response.json()["uuid"]

    @pytest.mark.parametrize("scopes", [EDIT_SCOPES])
    def test_event_edits(self, client: TestClient, event_1, auth_token: auth.Token):
        _publish(event_1.uuid)
        response = client.patch(
            f"/events/{event_1.uuid}",
            json={"info": "edited"},
            headers=self._headers(auth_token),
        )
        assert response.json()["published"] is False

        # An edit that sets the published state itself keeps it.
        response = client.patch(
            f"/events/{event_1.uuid}",
            json={"info": "edited again", "published": True},
            headers=self._headers(auth_token),
        )
        assert response.json()["published"] is True

        for method in ("post", "delete"):
            _publish(event_1.uuid)
            response = getattr(client, method)(
                f"/events/{event_1.uuid}/tag/unpublish-test",
                headers=self._headers(auth_token),
            )
            assert response.status_code < 300, response.text
            assert _published(event_1.uuid) is False, method

    @pytest.mark.parametrize("scopes", [EDIT_SCOPES])
    def test_attribute_edits(self, client: TestClient, event_1, auth_token: auth.Token):
        _publish(event_1.uuid)
        attribute_uuid = self._new_attribute(
            client, auth_token, event_1.uuid, "203.0.113.50"
        )
        assert _published(event_1.uuid) is False

        _publish(event_1.uuid)
        client.patch(
            f"/attributes/{attribute_uuid}",
            json={"to_ids": False},
            headers=self._headers(auth_token),
        )
        assert _published(event_1.uuid) is False

        for method in ("post", "delete"):
            _publish(event_1.uuid)
            response = getattr(client, method)(
                f"/attributes/{attribute_uuid}/tag/unpublish-test",
                headers=self._headers(auth_token),
            )
            assert response.status_code < 300, response.text
            assert _published(event_1.uuid) is False, method

        _publish(event_1.uuid)
        response = client.delete(
            f"/attributes/{attribute_uuid}", headers=self._headers(auth_token)
        )
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert _published(event_1.uuid) is False

    @pytest.mark.parametrize("scopes", [EDIT_SCOPES])
    def test_object_edits(self, client: TestClient, event_1, auth_token: auth.Token):
        _publish(event_1.uuid)
        response = client.post(
            "/objects/",
            json={
                "event_uuid": str(event_1.uuid),
                "name": "unpublish test object",
                "template_version": 0,
                "timestamp": 1655283899,
                "deleted": False,
            },
            headers=self._headers(auth_token),
        )
        assert response.status_code == status.HTTP_201_CREATED, response.text
        object_uuid = response.json()["uuid"]
        assert _published(event_1.uuid) is False

        _publish(event_1.uuid)
        response = client.delete(
            f"/objects/{object_uuid}", headers=self._headers(auth_token)
        )
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert _published(event_1.uuid) is False

    def test_repository_writes_keep_the_published_state(self, db: Session, event_1):
        # The path pulls, feeds and imports take: no unpublishing there.
        _publish(event_1.uuid)
        attributes_repository.create_attribute(
            db,
            attribute_schemas.AttributeCreate(
                event_uuid=event_1.uuid,
                category="Network activity",
                type="ip-dst",
                value="203.0.113.51",
            ),
        )
        assert _published(event_1.uuid) is True

    def test_mark_event_modified_is_safe_to_call(self, event_1):
        get_opensearch_client().update(
            index="misp-events",
            id=str(event_1.uuid),
            body={"doc": {"published": False}},
            refresh=True,
        )
        # Already unpublished, and a missing event: both are no-ops.
        events_repository.mark_event_modified(event_1.uuid)
        events_repository.mark_event_modified("00000000-0000-4000-8000-0000000000ee")
        events_repository.mark_event_modified(None)
        assert _published(event_1.uuid) is False
