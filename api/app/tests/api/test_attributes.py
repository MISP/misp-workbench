from unittest.mock import MagicMock, patch

import pytest
from app.auth import auth
from app.models import tag as tag_models
from app.tests.api_tester import ApiTester
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session


OPENSEARCH_PATCH = "app.repositories.attributes.get_opensearch_client"

MOCK_HISTOGRAM_RESPONSE = {
    "aggregations": {
        "attributes_over_time": {
            "buckets": [
                {"key_as_string": "2024-01-01T00:00:00.000Z", "key": 1704067200000, "doc_count": 10},
                {"key_as_string": "2024-01-02T00:00:00.000Z", "key": 1704153600000, "doc_count": 4},
            ]
        }
    }
}


def make_opensearch_mock(search_return=None):
    mock = MagicMock()
    mock.search.return_value = search_return or MOCK_HISTOGRAM_RESPONSE
    return mock


class TestAttributesResource(ApiTester):
    @pytest.mark.parametrize("scopes", [["attributes:read"]])
    def test_get_attributes(
        self,
        client: TestClient,
        attribute_1,
        auth_token: auth.Token,
    ):
        response = client.get(
            "/attributes/", headers={"Authorization": "Bearer " + auth_token}
        )
        data = response.json()["items"]

        assert response.status_code == status.HTTP_200_OK

        assert len(data) == 1
        assert data[0]["uuid"] == str(attribute_1.uuid)
        assert data[0]["category"] == attribute_1.category
        assert data[0]["type"] == attribute_1.type
        assert data[0]["value"] == attribute_1.value

    @pytest.mark.parametrize("scopes", [[]])
    def test_get_attributes_unauthorized(
        self, client: TestClient, auth_token: auth.Token
    ):
        response = client.get(
            "/attributes/", headers={"Authorization": "Bearer " + auth_token}
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.parametrize("scopes", [["attributes:create"]])
    def test_create_attribute(
        self, client: TestClient, event_1: object, auth_token: auth.Token
    ):
        response = client.post(
            "/attributes/",
            json={
                "event_uuid": str(event_1.uuid),
                "category": "Network activity",
                "type": "ip-dst",
                "value": "127.0.0.1",
            },
            headers={"Authorization": "Bearer " + auth_token},
        )
        data = response.json()

        assert response.status_code == status.HTTP_201_CREATED
        assert data["uuid"] is not None
        assert data["event_uuid"] == str(event_1.uuid)
        assert data["category"] == "Network activity"
        assert data["type"] == "ip-dst"
        assert data["value"] == "127.0.0.1"

    @pytest.mark.parametrize("scopes", [["attributes:read"]])
    def test_create_attribute_unauthorized(
        self, client: TestClient, event_1: object, auth_token: auth.Token
    ):
        response = client.post(
            "/attributes/",
            json={
                "event_uuid": str(event_1.uuid),
                "category": "Network activity",
                "type": "ip-dst",
                "value": "127.0.0.1",
            },
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.parametrize("scopes", [["attributes:create"]])
    def test_create_attribute_incomplete(
        self, client: TestClient, event_1: object, auth_token: auth.Token
    ):
        # missing value
        response = client.post(
            "/attributes/",
            json={
                "event_uuid": str(event_1.uuid),
                "category": "Network activity",
                "type": "ip-dst",
            },
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.parametrize("scopes", [["attributes:update"]])
    def test_update_attribute(
        self,
        client: TestClient,
        attribute_1,
        auth_token: auth.Token,
    ):
        response = client.patch(
            f"/attributes/{attribute_1.uuid}",
            json={
                "type": "ip-src",
                "value": "8.8.8.8",
            },
            headers={"Authorization": "Bearer " + auth_token},
        )
        data = response.json()

        assert response.status_code == status.HTTP_200_OK
        assert data["type"] == "ip-src"
        assert data["value"] == "8.8.8.8"

    @pytest.mark.parametrize("scopes", [["attributes:delete"]])
    def test_delete_attribute(
        self,
        client: TestClient,
        attribute_1,
        auth_token: auth.Token,
    ):
        response = client.delete(
            f"/attributes/{attribute_1.uuid}",
            headers={"Authorization": "Bearer " + auth_token},
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT

    @pytest.mark.parametrize("scopes", [["attributes:update"]])
    def test_tag_attribute(
        self,
        client: TestClient,
        event_1: object,
        attribute_1,
        tlp_white_tag: tag_models.Tag,
        auth_token: auth.Token,
        db: Session,
    ):
        response = client.post(
            f"/attributes/{attribute_1.uuid}/tag/{tlp_white_tag.name}",
            headers={"Authorization": "Bearer " + auth_token},
        )

        assert response.status_code == status.HTTP_201_CREATED

        from app.services.opensearch import get_opensearch_client
        os_client = get_opensearch_client()
        os_attr = os_client.get(index="misp-attributes", id=str(attribute_1.uuid))
        tag_names = [t.get("name") for t in os_attr["_source"].get("tags", [])]
        assert tlp_white_tag.name in tag_names

    @pytest.mark.parametrize("scopes", [["attributes:update"]])
    def test_untag_event(
        self,
        client: TestClient,
        event_1: object,
        attribute_1,
        tlp_white_tag: tag_models.Tag,
        auth_token: auth.Token,
        db: Session,
    ):
        response = client.delete(
            f"/attributes/{attribute_1.uuid}/tag/{tlp_white_tag.name}",
            headers={"Authorization": "Bearer " + auth_token},
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT

        from app.services.opensearch import get_opensearch_client
        os_client = get_opensearch_client()
        os_attr = os_client.get(index="misp-attributes", id=str(attribute_1.uuid))
        tag_names = [t.get("name") for t in os_attr["_source"].get("tags", [])]
        assert tlp_white_tag.name not in tag_names

    # ---- GET /attributes/histogram ----

    @pytest.mark.parametrize("scopes", [["attributes:read"]])
    def test_get_attributes_histogram(self, client: TestClient, auth_token: auth.Token):
        mock_os = make_opensearch_mock(MOCK_HISTOGRAM_RESPONSE)
        with patch(OPENSEARCH_PATCH, return_value=mock_os):
            response = client.get(
                "/attributes/histogram",
                params={"query": ""},
                headers={"Authorization": "Bearer " + auth_token},
            )
        data = response.json()

        assert response.status_code == status.HTTP_200_OK
        assert "buckets" in data
        assert len(data["buckets"]) == 2
        assert data["buckets"][0]["doc_count"] == 10
        assert data["buckets"][1]["doc_count"] == 4

    @pytest.mark.parametrize("scopes", [["attributes:read"]])
    def test_get_attributes_histogram_with_query(
        self, client: TestClient, auth_token: auth.Token
    ):
        mock_os = make_opensearch_mock(MOCK_HISTOGRAM_RESPONSE)
        with patch(OPENSEARCH_PATCH, return_value=mock_os):
            response = client.get(
                "/attributes/histogram",
                params={"query": "ip-src", "interval": "1w"},
                headers={"Authorization": "Bearer " + auth_token},
            )

        assert response.status_code == status.HTTP_200_OK
        call_body = mock_os.search.call_args.kwargs["body"]
        assert call_body["aggs"]["attributes_over_time"]["date_histogram"]["calendar_interval"] == "1w"
        assert call_body["query"]["bool"]["must"]["query_string"]["query"] == "ip-src"

    @pytest.mark.parametrize("scopes", [["attributes:read"]])
    def test_get_attributes_histogram_invalid_interval(
        self, client: TestClient, auth_token: auth.Token
    ):
        response = client.get(
            "/attributes/histogram",
            params={"query": "", "interval": "invalid"},
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.parametrize("scopes", [[]])
    def test_get_attributes_histogram_unauthorized(
        self, client: TestClient, auth_token: auth.Token
    ):
        response = client.get(
            "/attributes/histogram",
            params={"query": ""},
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
