from fastapi.testclient import TestClient
from ..models import event as event_models
from ..models import user as user_models
from ..models import attribute as attribute_models
from .api_test import ApiTest


class TestAttributesResource(ApiTest):
    def test_get_attributes(self,
                            client: TestClient,
                            user_1: user_models.User,
                            event_1: event_models.Event,
                            attribute_1: attribute_models.Attribute):
        response = client.get("/attributes/")
        data = response.json()

        assert response.status_code == 200

        assert len(data) == 1
        assert data[0]["id"] == attribute_1.id
        assert data[0]["category"] == attribute_1.category
        assert data[0]["type"] == attribute_1.type
        assert data[0]["value"] == attribute_1.value

    def test_create_attribute(self, client: TestClient, event_1: event_models.Event):
        response = client.post(
            "/attributes/", json={
                "event_id": event_1.id,
                "category": "Network activity",
                "type": "ip-dst",
                "value": "127.0.0.1"
            }
        )
        data = response.json()

        assert response.status_code == 200
        assert data["id"] is not None
        assert data["event_id"] == event_1.id
        assert data["category"] == "Network activity"
        assert data["type"] == "ip-dst"
        assert data["value"] == "127.0.0.1"

    def test_create_attribute_incomplete(self, client: TestClient, event_1: event_models.Event):
        # missing value
        response = client.post(
            "/attributes/", json={
                "event_id": event_1.id,
                "category": "Network activity",
                "type": "ip-dst",
            }
        )
        data = response.json()
        assert response.status_code == 422
