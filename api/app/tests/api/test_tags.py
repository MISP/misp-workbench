import pytest
from app.auth import auth
from app.models import organisation as organisation_models
from app.models import tag as tag_models
from app.models import user as user_models
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

        assert len(data["items"]) == 1
        assert data["items"][0]["id"] == tlp_white_tag.id
        assert data["items"][0]["name"] == tlp_white_tag.name
        assert data["items"][0]["colour"] == tlp_white_tag.colour
        assert data["items"][0]["exportable"] == tlp_white_tag.exportable
        assert data["items"][0]["hide_tag"] == tlp_white_tag.hide_tag
        assert data["items"][0]["is_galaxy"] == tlp_white_tag.is_galaxy
        assert data["items"][0]["is_custom_galaxy"] == tlp_white_tag.is_custom_galaxy
        assert data["items"][0]["numerical_value"] == tlp_white_tag.numerical_value
        assert data["items"][0]["local_only"] == tlp_white_tag.local_only

    @pytest.mark.parametrize("scopes", [["tags:read"]])
    def test_get_tag_by_id(
        self,
        client: TestClient,
        tlp_white_tag: tag_models.Tag,
        auth_token: auth.Token,
    ):
        response = client.get(
            f"/tags/{tlp_white_tag.id}",
            headers={"Authorization": "Bearer " + auth_token},
        )
        data = response.json()

        assert response.status_code == status.HTTP_200_OK

        assert data["id"] == tlp_white_tag.id
        assert data["name"] == tlp_white_tag.name
        assert data["colour"] == tlp_white_tag.colour
        assert data["exportable"] == tlp_white_tag.exportable
        assert data["hide_tag"] == tlp_white_tag.hide_tag
        assert data["is_galaxy"] == tlp_white_tag.is_galaxy
        assert data["is_custom_galaxy"] == tlp_white_tag.is_custom_galaxy
        assert data["numerical_value"] == tlp_white_tag.numerical_value
        assert data["local_only"] == tlp_white_tag.local_only

    @pytest.mark.parametrize("scopes", [[]])
    def test_get_tags_unauthorized(self, client: TestClient, auth_token: auth.Token):
        response = client.get(
            "/tags/", headers={"Authorization": "Bearer " + auth_token}
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.parametrize("scopes", [["tags:create"]])
    def test_create_tag(
        self,
        client: TestClient,
        organisation_1: organisation_models.Organisation,
        user_1: user_models.User,
        auth_token: auth.Token,
    ):
        response = client.post(
            "/tags/",
            json={
                "name": "tlp:rainbow",
                "colour": "#233067",
                "org_id": organisation_1.id,
                "user_id": user_1.id,
                "exportable": True,
                "hide_tag": False,
                "is_galaxy": False,
                "is_custom_galaxy": False,
                "numerical_value": None,
                "local_only": False,
            },
            headers={"Authorization": "Bearer " + auth_token},
        )
        data = response.json()

        assert response.status_code == status.HTTP_201_CREATED
        assert data["id"] is not None
        assert data["name"] == "tlp:rainbow"
        assert data["colour"] == "#233067"
        assert data["exportable"] is True
        assert data["hide_tag"] is False
        assert data["is_galaxy"] is False
        assert data["is_custom_galaxy"] is False
        assert data["numerical_value"] is None
        assert data["local_only"] is False

    @pytest.mark.parametrize("scopes", [["tags:read"]])
    def test_create_tag_unauthorized(
        self,
        client: TestClient,
        organisation_1: organisation_models.Organisation,
        user_1: user_models.User,
        auth_token: auth.Token,
    ):
        response = client.post(
            "/tags/",
            json={
                "name": "tlp:rainbow",
                "colour": "#233067",
                "org_id": organisation_1.id,
                "user_id": user_1.id,
                "exportable": True,
                "hide_tag": False,
                "is_galaxy": False,
                "is_custom_galaxy": False,
                "numerical_value": None,
                "local_only": False,
            },
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.parametrize("scopes", [["tags:create"]])
    def test_create_tag_incomplete(self, client: TestClient, auth_token: auth.Token):
        # missing value
        response = client.post(
            "/tags/",
            json={
                "name": "foobar",
            },
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.parametrize("scopes", [["tags:update"]])
    def test_update_tag(
        self,
        client: TestClient,
        tlp_white_tag: tag_models.Tag,
        auth_token: auth.Token,
    ):
        response = client.patch(
            f"/tags/{tlp_white_tag.id}",
            json={
                "name": "tlp:clear",
            },
            headers={"Authorization": "Bearer " + auth_token},
        )
        data = response.json()

        assert response.status_code == status.HTTP_200_OK
        assert data["name"] == "tlp:clear"

    @pytest.mark.parametrize("scopes", [["tags:delete"]])
    def test_delete_tag(
        self,
        client: TestClient,
        tlp_white_tag: tag_models.Tag,
        auth_token: auth.Token,
    ):
        response = client.delete(
            f"/tags/{tlp_white_tag.id}",
            headers={"Authorization": "Bearer " + auth_token},
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT
