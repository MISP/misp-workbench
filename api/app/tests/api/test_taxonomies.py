import pytest
from app.auth import auth
from app.models import taxonomy as taxonomies_models
from app.tests.api_tester import ApiTester
from fastapi import status
from fastapi.testclient import TestClient


class TestTaxonomiesResource(ApiTester):
    @pytest.mark.parametrize("scopes", [["taxonomies:read"]])
    def test_get_taxonomies(
        self,
        client: TestClient,
        tlp_taxonomy: taxonomies_models.Taxonomy,
        tlp_white_predicate: taxonomies_models.TaxonomyPredicate,
        auth_token: auth.Token,
    ):
        response = client.get(
            "/taxonomies/", headers={"Authorization": "Bearer " + auth_token}
        )
        data = response.json()

        assert response.status_code == status.HTTP_200_OK

        assert len(data["items"]) == 1
        assert data["items"][0]["id"] == tlp_taxonomy.id
        assert data["items"][0]["namespace"] == tlp_taxonomy.namespace
        assert data["items"][0]["version"] == tlp_taxonomy.version
        assert data["items"][0]["enabled"] == tlp_taxonomy.enabled
        assert data["items"][0]["exclusive"] == tlp_taxonomy.exclusive
        assert data["items"][0]["required"] == tlp_taxonomy.required
        assert data["items"][0]["highlighted"] == tlp_taxonomy.highlighted

        # check predicates
        assert len(data["items"][0]["predicates"]) == 1
        assert (
            data["items"][0]["predicates"][0]["taxonomy_id"]
            == tlp_white_predicate.taxonomy_id
        )
        assert data["items"][0]["predicates"][0]["id"] == tlp_white_predicate.id
        assert data["items"][0]["predicates"][0]["value"] == tlp_white_predicate.value
        assert (
            data["items"][0]["predicates"][0]["expanded"]
            == tlp_white_predicate.expanded
        )
        assert data["items"][0]["predicates"][0]["colour"] == tlp_white_predicate.colour
        assert (
            data["items"][0]["predicates"][0]["description"]
            == tlp_white_predicate.description
        )

    @pytest.mark.parametrize("scopes", [["taxonomies:read"]])
    def test_get_taxonomy_by_id(
        self,
        client: TestClient,
        tlp_taxonomy: taxonomies_models.Taxonomy,
        tlp_white_predicate: taxonomies_models.TaxonomyPredicate,
        auth_token: auth.Token,
    ):
        response = client.get(
            f"/taxonomies/{tlp_taxonomy.id}",
            headers={"Authorization": "Bearer " + auth_token},
        )
        data = response.json()

        assert response.status_code == status.HTTP_200_OK

        assert data["id"] == tlp_taxonomy.id
        assert data["namespace"] == tlp_taxonomy.namespace
        assert data["version"] == tlp_taxonomy.version
        assert data["enabled"] == tlp_taxonomy.enabled
        assert data["exclusive"] == tlp_taxonomy.exclusive
        assert data["required"] == tlp_taxonomy.required
        assert data["highlighted"] == tlp_taxonomy.highlighted

        # check predicates
        assert len(data["predicates"]) == 1
        assert data["predicates"][0]["taxonomy_id"] == tlp_white_predicate.taxonomy_id
        assert data["predicates"][0]["id"] == tlp_white_predicate.id
        assert data["predicates"][0]["value"] == tlp_white_predicate.value
        assert data["predicates"][0]["expanded"] == tlp_white_predicate.expanded
        assert data["predicates"][0]["colour"] == tlp_white_predicate.colour
        assert data["predicates"][0]["description"] == tlp_white_predicate.description

    @pytest.mark.parametrize("scopes", [["taxonomies:update"]])
    def test_patch_taxonomy(
        self,
        client: TestClient,
        tlp_taxonomy: taxonomies_models.Taxonomy,
        auth_token: auth.Token,
    ):
        response = client.patch(
            f"/taxonomies/{tlp_taxonomy.id}",
            headers={"Authorization": "Bearer " + auth_token},
            json={
                "enabled": False,
                "exclusive": False,
                "required": True,
                "highlighted": True,
            },
        )
        data = response.json()

        assert response.status_code == status.HTTP_200_OK

        assert data["id"] == tlp_taxonomy.id
        assert data["namespace"] == tlp_taxonomy.namespace
        assert data["version"] == tlp_taxonomy.version
        assert data["enabled"] is False
        assert data["exclusive"] is False
        assert data["required"] is True
        assert data["highlighted"] is True

    @pytest.mark.parametrize("scopes", [["taxonomies:update"]])
    def test_update_taxonomies(
        self,
        client: TestClient,
        auth_token: auth.Token,
    ):
        # TODO: implement test without importing all the misp-taxonomies (takes too long)
        pass
