import pytest
from app.auth import auth
from app.models import tag as tag_models
from app.tests.api_tester import ApiTester
from fastapi import status
from fastapi.testclient import TestClient


class TestTagsResource(ApiTester):
    @pytest.mark.parametrize("scopes", [["tags:read"]])
    def test_get_tags(
        self,
        client: TestClient,
        tlp_white_tag: tag_models.Tag,
        auth_token: auth.Token,
    ):
        response = client.get(
            "/tags/", headers={"Authorization": "Bearer " + auth_token}
        )
        data = response.json()

        assert response.status_code == status.HTTP_200_OK

        assert len(data) == 1
        assert data[0]["id"] == tlp_white_tag.id
        assert data[0]["name"] == tlp_white_tag.name
        assert data[0]["colour"] == tlp_white_tag.colour
        assert data[0]["exportable"] == tlp_white_tag.exportable
        assert data[0]["hide_tag"] == tlp_white_tag.hide_tag
        assert data[0]["is_galaxy"] == tlp_white_tag.is_galaxy
        assert data[0]["is_custom_galaxy"] == tlp_white_tag.is_custom_galaxy
        assert data[0]["numerical_value"] == tlp_white_tag.numerical_value
        assert data[0]["local_only"] == tlp_white_tag.local_only
