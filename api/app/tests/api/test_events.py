import pytest
from app.auth import auth
from app.models import organisation as organisation_models
from app.models import tag as tag_models
from app.models import user as user_models
from app.tests.api_tester import ApiTester
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session


class TestEventsResource(ApiTester):
    @pytest.mark.parametrize("scopes", [["events:read"]])
    def test_get_events(
        self,
        client: TestClient,
        user_1: user_models.User,
        event_1: object,
        auth_token: auth.Token,
    ):
        response = client.get(
            "/events/", headers={"Authorization": "Bearer " + auth_token}
        )
        data = response.json()["items"]

        assert response.status_code == status.HTTP_200_OK

        assert len(data) == 1
        assert data[0]["info"] == event_1.info
        assert data[0]["org_id"] == event_1.org_id
        assert data[0]["orgc_id"] == event_1.orgc_id
        assert data[0]["user_id"] == user_1.id

    @pytest.mark.parametrize("scopes", [[]])
    def test_get_events_unauthorized(
        self, client: TestClient, user_1: user_models.User, auth_token: auth.Token
    ):
        response = client.get(
            "/events/", headers={"Authorization": "Bearer " + auth_token}
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.parametrize("scopes", [["events:create"]])
    def test_create_event(
        self,
        client: TestClient,
        api_tester_user: user_models.User,
        auth_token: auth.Token,
    ):
        response = client.post(
            "/events/",
            json={
                "info": "test create event",
                "date": "2020-01-01",
                "analysis": 1,
                "distribution": 0,
                "threat_level": 1,
            },
            headers={"Authorization": "Bearer " + auth_token},
        )
        data = response.json()

        assert response.status_code == status.HTTP_201_CREATED
        assert data["uuid"] is not None
        assert data["info"] == "test create event"
        assert data["user_id"] == api_tester_user.id
        assert data["org_id"] == api_tester_user.org_id

    @pytest.mark.parametrize("scopes", [["events:read"]])
    def test_create_event_unauthorized(
        self,
        client: TestClient,
        organisation_1: organisation_models.Organisation,
        user_1: user_models.User,
        auth_token: auth.Token,
    ):
        response = client.post(
            "/events/",
            json={
                "info": "test create event",
                "user_id": user_1.id,
                "orgc_id": 1,
                "org_id": organisation_1.id,
                "date": "2020-01-01",
            },
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.parametrize("scopes", [["events:create"]])
    def test_create_event_incomplete(self, client: TestClient, auth_token: auth.Token):
        # missing info
        response = client.post(
            "/events/",
            json={"user_id": 1, "orgc_id": 1, "org_id": 1, "date": "2020-01-01"},
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.parametrize("scopes", [["events:create"]])
    def test_create_event_invalid_exists(
        self, client: TestClient, event_1: object, auth_token: auth.Token
    ):
        # event with duplicated info
        response = client.post(
            "/events/",
            json={
                "info": event_1.info,
                "user_id": event_1.user_id,
                "org_id": event_1.org_id,
                "orgc_id": event_1.orgc_id,
                "date": "2020-01-01",
            },
            headers={"Authorization": "Bearer " + auth_token},
        )
        data = response.json()

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert data["detail"] == "An event with this info already exists"

    @pytest.mark.parametrize("scopes", [["events:update"]])
    def test_update_event(
        self,
        client: TestClient,
        event_1: object,
        auth_token: auth.Token,
    ):
        response = client.patch(
            f"/events/{event_1.uuid}",
            json={
                "info": "updated via API",
                "published": False,
            },
            headers={"Authorization": "Bearer " + auth_token},
        )
        data = response.json()

        assert response.status_code == status.HTTP_200_OK
        assert data["info"] == "updated via API"
        assert data["published"] is False

    @pytest.mark.parametrize("scopes", [["events:delete"]])
    def test_delete_event(
        self,
        client: TestClient,
        event_1: object,
        auth_token: auth.Token,
    ):
        response = client.delete(
            f"/events/{event_1.uuid}",
            headers={"Authorization": "Bearer " + auth_token},
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT

    @pytest.mark.parametrize("scopes", [["events:update"]])
    def test_tag_event(
        self,
        client: TestClient,
        event_1: object,
        tlp_white_tag: tag_models.Tag,
        auth_token: auth.Token,
        db: Session,
    ):
        response = client.post(
            f"/events/{event_1.uuid}/tag/{tlp_white_tag.name}",
            headers={"Authorization": "Bearer " + auth_token},
        )

        assert response.status_code == status.HTTP_201_CREATED

        from app.services.opensearch import get_opensearch_client
        os_client = get_opensearch_client()
        os_event = os_client.get(index="misp-events", id=str(event_1.uuid))
        tag_names = [t.get("name") for t in os_event["_source"].get("tags", [])]
        assert tlp_white_tag.name in tag_names

    @pytest.mark.parametrize("scopes", [["events:update"]])
    def test_untag_event(
        self,
        client: TestClient,
        event_1: object,
        tlp_white_tag: tag_models.Tag,
        auth_token: auth.Token,
        db: Session,
    ):
        response = client.delete(
            f"/events/{event_1.uuid}/tag/{tlp_white_tag.name}",
            headers={"Authorization": "Bearer " + auth_token},
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT

        from app.services.opensearch import get_opensearch_client
        os_client = get_opensearch_client()
        os_event = os_client.get(index="misp-events", id=str(event_1.uuid))
        tag_names = [t.get("name") for t in os_event["_source"].get("tags", [])]
        assert tlp_white_tag.name not in tag_names

    @pytest.fixture(scope="class")
    def event_2(
        self,
        db: Session,
        organisation_1: organisation_models.Organisation,
        user_1: user_models.User,
    ):
        """A second event used for force-delete and other destructive tests."""
        from datetime import datetime
        from uuid import UUID
        from app.repositories import events as events_repository
        from app.schemas import event as event_schemas

        event_create = event_schemas.EventCreate(
            info="test event 2 for force delete",
            user_id=user_1.id,
            orgc_id=1,
            org_id=organisation_1.id,
            date=datetime(2020, 1, 1),
            uuid=UUID("d8a2b0c1-aaaa-bbbb-cccc-ef1234567890"),
            timestamp=1577836800,
        )
        yield events_repository.create_event(db=db, event=event_create)

    @pytest.fixture(scope="class")
    def event_for_filter(
        self,
        db: Session,
        organisation_1: organisation_models.Organisation,
        user_1: user_models.User,
    ):
        """A stable event used for filter/search tests that won't be mutated."""
        from datetime import datetime
        from uuid import UUID
        from app.repositories import events as events_repository
        from app.schemas import event as event_schemas

        event_create = event_schemas.EventCreate(
            info="stable filter test event",
            user_id=user_1.id,
            orgc_id=1,
            org_id=organisation_1.id,
            date=datetime(2020, 1, 1),
            uuid=UUID("f1f7e2a3-0000-0000-0000-000000000001"),
            timestamp=1577836800,
        )
        yield events_repository.create_event(db=db, event=event_create)

    # ---- GET /events/{event_uuid} ----

    @pytest.mark.parametrize("scopes", [["events:read"]])
    def test_get_event_by_uuid(
        self,
        client: TestClient,
        event_1: object,
        auth_token: auth.Token,
    ):
        response = client.get(
            f"/events/{event_1.uuid}",
            headers={"Authorization": "Bearer " + auth_token},
        )
        data = response.json()

        assert response.status_code == status.HTTP_200_OK
        assert data["uuid"] == str(event_1.uuid)

    @pytest.mark.parametrize("scopes", [["events:read"]])
    def test_get_event_not_found(
        self,
        client: TestClient,
        auth_token: auth.Token,
    ):
        response = client.get(
            "/events/00000000-0000-0000-0000-000000000000",
            headers={"Authorization": "Bearer " + auth_token},
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.json()["detail"] == "Event not found"

    # ---- GET /events/ with filters ----

    @pytest.mark.parametrize("scopes", [["events:read"]])
    def test_get_events_filter_by_info(
        self,
        client: TestClient,
        event_for_filter: object,
        auth_token: auth.Token,
    ):
        response = client.get(
            "/events/",
            params={"info": "stable filter"},
            headers={"Authorization": "Bearer " + auth_token},
        )
        data = response.json()["items"]

        assert response.status_code == status.HTTP_200_OK
        assert len(data) == 1
        assert data[0]["uuid"] == str(event_for_filter.uuid)

    @pytest.mark.parametrize("scopes", [["events:read"]])
    def test_get_events_filter_by_info_no_results(
        self,
        client: TestClient,
        auth_token: auth.Token,
    ):
        response = client.get(
            "/events/",
            params={"info": "xyzzy_nonexistent_event_string_99999"},
            headers={"Authorization": "Bearer " + auth_token},
        )
        data = response.json()["items"]

        assert response.status_code == status.HTTP_200_OK
        assert len(data) == 0

    @pytest.mark.parametrize("scopes", [["events:read"]])
    def test_get_events_filter_by_uuid(
        self,
        client: TestClient,
        event_for_filter: object,
        auth_token: auth.Token,
    ):
        response = client.get(
            "/events/",
            params={"uuid": str(event_for_filter.uuid)},
            headers={"Authorization": "Bearer " + auth_token},
        )
        data = response.json()["items"]

        assert response.status_code == status.HTTP_200_OK
        assert len(data) == 1
        assert data[0]["uuid"] == str(event_for_filter.uuid)

    @pytest.mark.parametrize("scopes", [["events:read"]])
    def test_get_events_filter_by_deleted_true(
        self,
        client: TestClient,
        event_1: object,
        auth_token: auth.Token,
    ):
        # event_1 was soft-deleted by test_delete_event
        response = client.get(
            "/events/",
            params={"deleted": True},
            headers={"Authorization": "Bearer " + auth_token},
        )
        data = response.json()["items"]

        assert response.status_code == status.HTTP_200_OK
        assert any(item["uuid"] == str(event_1.uuid) for item in data)

    @pytest.mark.parametrize("scopes", [["events:read"]])
    def test_get_events_filter_by_deleted_false(
        self,
        client: TestClient,
        event_1: object,
        event_for_filter: object,
        auth_token: auth.Token,
    ):
        # event_1 was soft-deleted; event_for_filter was not
        response = client.get(
            "/events/",
            params={"deleted": False},
            headers={"Authorization": "Bearer " + auth_token},
        )
        data = response.json()["items"]

        assert response.status_code == status.HTTP_200_OK
        uuids = [item["uuid"] for item in data]
        assert str(event_1.uuid) not in uuids
        assert str(event_for_filter.uuid) in uuids

    # ---- DELETE /events/{event_id} force ----

    @pytest.mark.parametrize("scopes", [["events:delete"]])
    def test_delete_event_force(
        self,
        client: TestClient,
        event_2: object,
        db: Session,
        auth_token: auth.Token,
    ):
        response = client.delete(
            f"/events/{event_2.uuid}",
            params={"force": True},
            headers={"Authorization": "Bearer " + auth_token},
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT

        from app.services.opensearch import get_opensearch_client
        os_client = get_opensearch_client()
        response_os = os_client.search(
            index="misp-events",
            body={"query": {"term": {"uuid.keyword": str(event_2.uuid)}}},
        )
        assert response_os["hits"]["total"]["value"] == 0

    # ---- Tag/untag 404 cases ----

    @pytest.mark.parametrize("scopes", [["events:update"]])
    def test_tag_event_event_not_found(
        self,
        client: TestClient,
        tlp_white_tag: tag_models.Tag,
        auth_token: auth.Token,
    ):
        response = client.post(
            f"/events/00000000-0000-0000-0000-000000000000/tag/{tlp_white_tag.name}",
            headers={"Authorization": "Bearer " + auth_token},
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.json()["detail"] == "Event not found"

    @pytest.mark.parametrize("scopes", [["events:update"]])
    def test_tag_event_tag_not_found(
        self,
        client: TestClient,
        event_1: object,
        auth_token: auth.Token,
    ):
        response = client.post(
            f"/events/{event_1.uuid}/tag/nonexistent:tag",
            headers={"Authorization": "Bearer " + auth_token},
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.json()["detail"] == "Tag not found"

    @pytest.mark.parametrize("scopes", [["events:update"]])
    def test_untag_event_event_not_found(
        self,
        client: TestClient,
        tlp_white_tag: tag_models.Tag,
        auth_token: auth.Token,
    ):
        response = client.delete(
            f"/events/00000000-0000-0000-0000-000000000000/tag/{tlp_white_tag.name}",
            headers={"Authorization": "Bearer " + auth_token},
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.json()["detail"] == "Event not found"

    @pytest.mark.parametrize("scopes", [["events:update"]])
    def test_untag_event_tag_not_found(
        self,
        client: TestClient,
        event_1: object,
        auth_token: auth.Token,
    ):
        response = client.delete(
            f"/events/{event_1.uuid}/tag/nonexistent:tag",
            headers={"Authorization": "Bearer " + auth_token},
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.json()["detail"] == "Tag not found"

    # ---- POST /events/{uuid}/publish ----

    @pytest.mark.parametrize("scopes", [["events:publish"]])
    def test_publish_event(
        self,
        client: TestClient,
        event_1: object,
        auth_token: auth.Token,
    ):
        # event_1 has published=False after test_update_event
        response = client.post(
            f"/events/{event_1.uuid}/publish",
            headers={"Authorization": "Bearer " + auth_token},
        )
        data = response.json()

        assert response.status_code == status.HTTP_200_OK
        assert str(event_1.uuid) in data["message"]

    @pytest.mark.parametrize("scopes", [["events:publish"]])
    def test_publish_event_not_found(
        self,
        client: TestClient,
        auth_token: auth.Token,
    ):
        response = client.post(
            "/events/00000000-0000-0000-0000-000000000000/publish",
            headers={"Authorization": "Bearer " + auth_token},
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.json()["detail"] == "Event not found"

    # ---- POST /events/{uuid}/unpublish ----

    @pytest.mark.parametrize("scopes", [["events:publish"]])
    def test_unpublish_event(
        self,
        client: TestClient,
        event_1: object,
        auth_token: auth.Token,
    ):
        # event_1 was published by test_publish_event
        response = client.post(
            f"/events/{event_1.uuid}/unpublish",
            headers={"Authorization": "Bearer " + auth_token},
        )
        data = response.json()

        assert response.status_code == status.HTTP_200_OK
        assert str(event_1.uuid) in data["message"]

    @pytest.mark.parametrize("scopes", [["events:publish"]])
    def test_unpublish_event_not_found(
        self,
        client: TestClient,
        auth_token: auth.Token,
    ):
        response = client.post(
            "/events/00000000-0000-0000-0000-000000000000/unpublish",
            headers={"Authorization": "Bearer " + auth_token},
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.json()["detail"] == "Event not found"

    # ---- POST /events/{uuid}/toggle-correlation ----

    @pytest.mark.parametrize("scopes", [["events:update"]])
    def test_toggle_correlation(
        self,
        client: TestClient,
        event_1: object,
        auth_token: auth.Token,
    ):
        response = client.post(
            f"/events/{event_1.uuid}/toggle-correlation",
            headers={"Authorization": "Bearer " + auth_token},
        )
        data = response.json()

        assert response.status_code == status.HTTP_200_OK
        assert "disable_correlation" in data["message"]

    @pytest.mark.parametrize("scopes", [["events:update"]])
    def test_toggle_correlation_not_found(
        self,
        client: TestClient,
        auth_token: auth.Token,
    ):
        response = client.post(
            "/events/00000000-0000-0000-0000-000000000000/toggle-correlation",
            headers={"Authorization": "Bearer " + auth_token},
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.json()["detail"] == "Event not found"

    # ---- POST /events/{uuid}/import ----

    @pytest.mark.parametrize("scopes", [["events:import"]])
    def test_import_data(
        self,
        client: TestClient,
        event_1: object,
        auth_token: auth.Token,
    ):
        response = client.post(
            f"/events/{event_1.uuid}/import",
            json={
                "attributes": [
                    {
                        "type": "ip-dst",
                        "value": "192.168.1.100",
                        "category": "Network activity",
                    },
                    {
                        "type": "domain",
                        "value": "example-import.com",
                        "category": "Network activity",
                    },
                ]
            },
            headers={"Authorization": "Bearer " + auth_token},
        )
        data = response.json()

        assert response.status_code == status.HTTP_202_ACCEPTED
        assert data["imported_attributes"] == 2
        assert data["total_attributes"] == 2
        assert data["failed_attributes"] == 0
        assert data["event_uuid"] == str(event_1.uuid)

    @pytest.mark.parametrize("scopes", [["events:import"]])
    def test_import_data_not_found(
        self,
        client: TestClient,
        auth_token: auth.Token,
    ):
        response = client.post(
            "/events/00000000-0000-0000-0000-000000000000/import",
            json={"attributes": []},
            headers={"Authorization": "Bearer " + auth_token},
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.json()["detail"] == "Event not found"

    # ---- POST /events/force-index ----

    @pytest.mark.parametrize("scopes", [["events:update"]])
    def test_force_index_by_uuid(
        self,
        client: TestClient,
        event_1: object,
        auth_token: auth.Token,
    ):
        response = client.post(
            "/events/force-index",
            params={"uuid": str(event_1.uuid)},
            headers={"Authorization": "Bearer " + auth_token},
        )
        data = response.json()

        assert response.status_code == status.HTTP_202_ACCEPTED
        assert str(event_1.uuid) in data["message"]

    @pytest.mark.parametrize("scopes", [["events:update"]])
    def test_force_index_all_events(
        self,
        client: TestClient,
        event_1: object,
        auth_token: auth.Token,
    ):
        response = client.post(
            "/events/force-index",
            headers={"Authorization": "Bearer " + auth_token},
        )
        data = response.json()

        assert response.status_code == status.HTTP_202_ACCEPTED
        assert "all events" in data["message"]

    # ---- GET /events/{uuid}/attachments ----

    @pytest.mark.parametrize("scopes", [["events:read"]])
    def test_get_event_attachments(
        self,
        client: TestClient,
        event_1: object,
        auth_token: auth.Token,
    ):
        response = client.get(
            f"/events/{event_1.uuid}/attachments",
            headers={"Authorization": "Bearer " + auth_token},
        )

        assert response.status_code == status.HTTP_200_OK
        assert "items" in response.json()

    @pytest.mark.parametrize("scopes", [["events:read"]])
    def test_get_event_attachments_not_found(
        self,
        client: TestClient,
        auth_token: auth.Token,
    ):
        response = client.get(
            "/events/00000000-0000-0000-0000-000000000000/attachments",
            headers={"Authorization": "Bearer " + auth_token},
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.json()["detail"] == "Event not found"
