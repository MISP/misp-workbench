import pytest
from app.auth import auth
from app.models import role as role_models
from app.models import organisation as organisation_models
from app.models import user as user_models
from app.tests.api_tester import ApiTester
from fastapi import status
from fastapi.testclient import TestClient


class TestRolesResource(ApiTester):
    @pytest.fixture(scope="class")
    def role_10(self, db):
        role = role_models.Role(
            id=10,
            name="test role",
            scopes=["events:read", "attributes:read"],
            default_role=False,
        )
        db.add(role)
        db.commit()
        db.refresh(role)
        yield role

    @pytest.fixture(scope="class")
    def role_for_delete(self, db):
        role = role_models.Role(
            name="test role for delete",
            scopes=[],
            default_role=False,
        )
        db.add(role)
        db.commit()
        db.refresh(role)
        yield role

    # GET /roles/scopes

    @pytest.mark.parametrize("scopes", [["roles:read"]])
    def test_get_scopes(self, client: TestClient, auth_token: auth.Token):
        response = client.get(
            "/roles/scopes", headers={"Authorization": "Bearer " + auth_token}
        )
        data = response.json()

        assert response.status_code == status.HTTP_200_OK
        assert isinstance(data, dict)
        assert "roles:read" in data

    @pytest.mark.parametrize("scopes", [[]])
    def test_get_scopes_unauthorized(self, client: TestClient, auth_token: auth.Token):
        response = client.get(
            "/roles/scopes", headers={"Authorization": "Bearer " + auth_token}
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    # GET /roles/

    @pytest.mark.parametrize("scopes", [["roles:read"]])
    def test_get_roles(
        self,
        client: TestClient,
        role_10: role_models.Role,
        auth_token: auth.Token,
    ):
        response = client.get(
            "/roles/", headers={"Authorization": "Bearer " + auth_token}
        )
        data = response.json()

        assert response.status_code == status.HTTP_200_OK
        assert isinstance(data, list)
        assert any(r["id"] == role_10.id for r in data)

    @pytest.mark.parametrize("scopes", [[]])
    def test_get_roles_unauthorized(self, client: TestClient, auth_token: auth.Token):
        response = client.get(
            "/roles/", headers={"Authorization": "Bearer " + auth_token}
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    # GET /roles/{role_id}

    @pytest.mark.parametrize("scopes", [["roles:read"]])
    def test_get_role(
        self,
        client: TestClient,
        role_10: role_models.Role,
        auth_token: auth.Token,
    ):
        response = client.get(
            f"/roles/{role_10.id}", headers={"Authorization": "Bearer " + auth_token}
        )
        data = response.json()

        assert response.status_code == status.HTTP_200_OK
        assert data["id"] == role_10.id
        assert data["name"] == role_10.name
        assert data["scopes"] == role_10.scopes

    @pytest.mark.parametrize("scopes", [[]])
    def test_get_role_unauthorized(
        self,
        client: TestClient,
        role_10: role_models.Role,
        auth_token: auth.Token,
    ):
        response = client.get(
            f"/roles/{role_10.id}", headers={"Authorization": "Bearer " + auth_token}
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.parametrize("scopes", [["roles:read"]])
    def test_get_role_not_found(self, client: TestClient, auth_token: auth.Token):
        response = client.get(
            "/roles/999999", headers={"Authorization": "Bearer " + auth_token}
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    # PATCH /roles/{role_id}

    @pytest.mark.parametrize("scopes", [["roles:update"]])
    def test_update_role(
        self,
        client: TestClient,
        role_10: role_models.Role,
        auth_token: auth.Token,
    ):
        response = client.patch(
            f"/roles/{role_10.id}",
            json={"scopes": ["events:read", "attributes:read", "feeds:read"]},
            headers={"Authorization": "Bearer " + auth_token},
        )
        data = response.json()

        assert response.status_code == status.HTTP_200_OK
        assert data["id"] == role_10.id
        assert "feeds:read" in data["scopes"]

    @pytest.mark.parametrize("scopes", [["roles:update"]])
    def test_update_role_name(
        self,
        client: TestClient,
        role_10: role_models.Role,
        auth_token: auth.Token,
    ):
        response = client.patch(
            f"/roles/{role_10.id}",
            json={"name": "test role updated"},
            headers={"Authorization": "Bearer " + auth_token},
        )
        data = response.json()

        assert response.status_code == status.HTTP_200_OK
        assert data["name"] == "test role updated"

    @pytest.mark.parametrize("scopes", [["roles:read"]])
    def test_update_role_unauthorized(
        self,
        client: TestClient,
        role_10: role_models.Role,
        auth_token: auth.Token,
    ):
        response = client.patch(
            f"/roles/{role_10.id}",
            json={"scopes": []},
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.parametrize("scopes", [["roles:update"]])
    def test_update_role_not_found(self, client: TestClient, auth_token: auth.Token):
        response = client.patch(
            "/roles/999999",
            json={"name": "nonexistent"},
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    # DELETE /roles/{role_id}

    @pytest.mark.parametrize("scopes", [["roles:delete"]])
    def test_delete_role(
        self,
        client: TestClient,
        role_for_delete: role_models.Role,
        auth_token: auth.Token,
    ):
        response = client.delete(
            f"/roles/{role_for_delete.id}",
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert response.status_code == status.HTTP_204_NO_CONTENT

    @pytest.mark.parametrize("scopes", [["roles:read"]])
    def test_delete_role_unauthorized(
        self,
        client: TestClient,
        role_10: role_models.Role,
        auth_token: auth.Token,
    ):
        response = client.delete(
            f"/roles/{role_10.id}",
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.parametrize("scopes", [["roles:delete"]])
    def test_delete_role_not_found(self, client: TestClient, auth_token: auth.Token):
        response = client.delete(
            "/roles/999999",
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND
