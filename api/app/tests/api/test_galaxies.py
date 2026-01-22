import pytest
from app.auth import auth
from app.models import galaxy as galaxies_models
from app.tests.api_tester import ApiTester
from fastapi import status
from fastapi.testclient import TestClient


class TestTaxonomiesResource(ApiTester):
    @pytest.mark.parametrize("scopes", [["galaxies:read"]])
    def test_get_galaxies(
        self,
        client: TestClient,
        threat_actor_galaxy: galaxies_models.Galaxy,
        threat_actor_galaxy_cluster_apt29: galaxies_models.GalaxyCluster,
        auth_token: auth.Token,
    ):
        response = client.get(
            "/galaxies", headers={"Authorization": "Bearer " + auth_token},
            params={"include_clusters": True}
        )
        data = response.json()

        assert response.status_code == status.HTTP_200_OK

        assert len(data["items"]) == 1
        assert data["items"][0]["id"] == threat_actor_galaxy.id
        assert data["items"][0]["name"] == threat_actor_galaxy.name
        assert data["items"][0]["type"] == threat_actor_galaxy.type
        assert data["items"][0]["description"] == threat_actor_galaxy.description
        assert data["items"][0]["namespace"] == threat_actor_galaxy.namespace
        assert data["items"][0]["icon"] == threat_actor_galaxy.icon
        assert data["items"][0]["enabled"] == threat_actor_galaxy.enabled
        assert data["items"][0]["local_only"] == threat_actor_galaxy.local_only
        assert data["items"][0]["default"] == threat_actor_galaxy.default
        assert data["items"][0]["org_id"] == threat_actor_galaxy.org_id
        assert data["items"][0]["orgc_id"] == threat_actor_galaxy.orgc_id

        # check clusters
        assert len(data["items"][0]["clusters"]) == 1
        assert data["items"][0]["clusters"][0]["galaxy_id"] == threat_actor_galaxy.id
        assert (
            data["items"][0]["clusters"][0]["id"]
            == threat_actor_galaxy_cluster_apt29.id
        )
        assert (
            data["items"][0]["clusters"][0]["value"]
            == threat_actor_galaxy_cluster_apt29.value
        )
        assert (
            data["items"][0]["clusters"][0]["value"]
            == threat_actor_galaxy_cluster_apt29.value
        )
        assert (
            data["items"][0]["clusters"][0]["tag_name"]
            == threat_actor_galaxy_cluster_apt29.tag_name
        )

    @pytest.mark.parametrize("scopes", [["galaxies:read"]])
    def test_get_galaxy_by_id(
        self,
        client: TestClient,
        threat_actor_galaxy: galaxies_models.Galaxy,
        threat_actor_galaxy_cluster_apt29: galaxies_models.GalaxyCluster,
        auth_token: auth.Token,
    ):
        response = client.get(
            f"/galaxies/{threat_actor_galaxy.id}",
            headers={"Authorization": "Bearer " + auth_token},
        )
        data = response.json()

        assert response.status_code == status.HTTP_200_OK
        assert data["id"] == threat_actor_galaxy.id
        assert data["name"] == threat_actor_galaxy.name
        assert data["type"] == threat_actor_galaxy.type
        assert data["description"] == threat_actor_galaxy.description
        assert data["namespace"] == threat_actor_galaxy.namespace
        assert data["icon"] == threat_actor_galaxy.icon
        assert data["enabled"] == threat_actor_galaxy.enabled
        assert data["local_only"] == threat_actor_galaxy.local_only
        assert data["default"] == threat_actor_galaxy.default
        assert data["org_id"] == threat_actor_galaxy.org_id
        assert data["orgc_id"] == threat_actor_galaxy.orgc_id

        # check clusters
        assert len(data["clusters"]) == 1
        assert data["clusters"][0]["galaxy_id"] == threat_actor_galaxy.id
        assert data["clusters"][0]["id"] == threat_actor_galaxy_cluster_apt29.id
        assert data["clusters"][0]["value"] == threat_actor_galaxy_cluster_apt29.value
        assert data["clusters"][0]["value"] == threat_actor_galaxy_cluster_apt29.value
        assert (
            data["clusters"][0]["tag_name"]
            == threat_actor_galaxy_cluster_apt29.tag_name
        )

    @pytest.mark.parametrize("scopes", [["galaxies:update"]])
    def test_patch_taxonomy(
        self,
        client: TestClient,
        threat_actor_galaxy: galaxies_models.Galaxy,
        auth_token: auth.Token,
    ):
        response = client.patch(
            f"/galaxies/{threat_actor_galaxy.id}",
            headers={"Authorization": "Bearer " + auth_token},
            json={
                "enabled": False,
                "local_only": True,
                "default": True,
            },
        )
        data = response.json()

        assert response.status_code == status.HTTP_200_OK

        assert data["id"] == threat_actor_galaxy.id
        assert data["name"] == threat_actor_galaxy.name
        assert data["enabled"] is False
        assert data["local_only"] is True
        assert data["default"] is True

    @pytest.mark.parametrize("scopes", [["galaxies:update"]])
    def test_update_galaxies(
        self,
        client: TestClient,
        auth_token: auth.Token,
    ):
        # TODO: implement test without importing all the misp-galaxies (takes too long)
        pass
