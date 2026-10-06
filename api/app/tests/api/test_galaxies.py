import json
import uuid

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import auth
from app.models import galaxy as galaxies_models
from app.models import tag as tags_models
from app.models import user as user_models
from app.repositories import galaxies as galaxies_repository
from app.tests.api_tester import ApiTester


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
            "/galaxies",
            headers={"Authorization": "Bearer " + auth_token},
            params={"include_clusters": True},
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

    # ── GET /galaxies/mitre-attack-patterns ─────────────────────────────────

    @pytest.mark.parametrize("scopes", [["galaxies:read"]])
    def test_get_mitre_attack_patterns(
        self,
        client: TestClient,
        mitre_attack_cluster_t1391: galaxies_models.GalaxyCluster,
        auth_token: auth.Token,
    ):
        response = client.get(
            "/galaxies/mitre-attack-patterns",
            headers={"Authorization": "Bearer " + auth_token},
        )
        data = response.json()

        assert response.status_code == status.HTTP_200_OK
        assert isinstance(data, list)
        codes = [item["external_id"] for item in data]
        assert "T1391" in codes

        entry = next(item for item in data if item["external_id"] == "T1391")
        assert entry["uuid"] == str(mitre_attack_cluster_t1391.uuid)
        assert entry["value"] == mitre_attack_cluster_t1391.value
        assert entry["description"] == mitre_attack_cluster_t1391.description

    @pytest.mark.parametrize("scopes", [["galaxies:read"]])
    def test_get_mitre_attack_patterns_filter_by_code(
        self,
        client: TestClient,
        mitre_attack_cluster_t1391: galaxies_models.GalaxyCluster,
        auth_token: auth.Token,
    ):
        response = client.get(
            "/galaxies/mitre-attack-patterns",
            params={"filter": "T1391"},
            headers={"Authorization": "Bearer " + auth_token},
        )
        data = response.json()

        assert response.status_code == status.HTTP_200_OK
        assert len(data) == 1
        assert data[0]["external_id"] == "T1391"

    @pytest.mark.parametrize("scopes", [["galaxies:read"]])
    def test_get_mitre_attack_patterns_filter_by_value(
        self,
        client: TestClient,
        mitre_attack_cluster_t1391: galaxies_models.GalaxyCluster,
        auth_token: auth.Token,
    ):
        response = client.get(
            "/galaxies/mitre-attack-patterns",
            params={"filter": "pre-compromised"},
            headers={"Authorization": "Bearer " + auth_token},
        )
        data = response.json()

        assert response.status_code == status.HTTP_200_OK
        assert len(data) == 1
        assert data[0]["external_id"] == "T1391"

    @pytest.mark.parametrize("scopes", [["galaxies:read"]])
    def test_get_mitre_attack_patterns_filter_no_match(
        self,
        client: TestClient,
        mitre_attack_cluster_t1391: galaxies_models.GalaxyCluster,
        auth_token: auth.Token,
    ):
        response = client.get(
            "/galaxies/mitre-attack-patterns",
            params={"filter": "T9999-nonexistent"},
            headers={"Authorization": "Bearer " + auth_token},
        )
        data = response.json()

        assert response.status_code == status.HTTP_200_OK
        assert data == []

    @pytest.mark.parametrize("scopes", [[]])
    def test_get_mitre_attack_patterns_unauthorized(
        self, client: TestClient, auth_token: auth.Token
    ):
        response = client.get(
            "/galaxies/mitre-attack-patterns",
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


def _uuid(*parts):
    return str(uuid.uuid5(uuid.NAMESPACE_URL, ":".join(parts)))


def _write_galaxy(tmp_path, name, version, clusters, galaxy_version=1):
    """Write a galaxy and its clusters file. Each cluster is a
    (value, meta) tuple; its uuid derives from the value so the same cluster
    can be shipped in more than one galaxy. As in misp-galaxy, cluster changes
    bump the version of the clusters file, not the galaxy one."""
    galaxies_dir, clusters_dir = tmp_path / "galaxies", tmp_path / "clusters"
    galaxies_dir.mkdir(exist_ok=True)
    clusters_dir.mkdir(exist_ok=True)
    (galaxies_dir / f"{name}.json").write_text(
        json.dumps(
            {
                "name": f"{name} v{version}",
                "uuid": _uuid(name),
                "namespace": "test",
                "type": name,
                "version": galaxy_version,
                "description": f"{name} galaxy",
                "icon": "user",
            }
        )
    )
    (clusters_dir / f"{name}.json").write_text(
        json.dumps(
            {
                "name": name,
                "type": name,
                "uuid": _uuid(name),
                "version": version,
                "source": "test",
                "authors": ["test"],
                "values": [
                    {
                        "uuid": _uuid(value),
                        "value": value,
                        "description": f"{value} v{version}",
                        "meta": meta,
                    }
                    for value, meta in clusters
                ],
            }
        )
    )
    return str(galaxies_dir), str(clusters_dir)


class TestGalaxiesImport(ApiTester):
    def _load(self, db: Session, name):
        db.expire_all()
        return (
            db.query(galaxies_models.Galaxy)
            .filter(galaxies_models.Galaxy.uuid == _uuid(name))
            .one()
        )

    def _clusters(self, galaxy):
        return {cluster.value: cluster for cluster in galaxy.clusters}

    def _elements(self, cluster):
        return sorted((element.key, element.value) for element in cluster.elements)

    def test_import_and_update_galaxies(
        self, db: Session, api_tester_user: user_models.User, tmp_path
    ):
        dirs = _write_galaxy(
            tmp_path,
            "test-actor",
            1,
            [
                ("APT1", {"country": "CN", "synonyms": ["Comment Crew"]}),
                ("APT2", {}),
            ],
        )
        # ships APT1 too: it must stay with the galaxy imported first (files
        # are imported in sorted order) and not make this one fail
        _write_galaxy(tmp_path, "test-mirror", 1, [("APT1", {}), ("APT3", {})])

        imported = galaxies_repository.update_galaxies(db, api_tester_user, *dirs)
        assert len(imported) == 2

        galaxy = self._load(db, "test-actor")
        assert galaxy.version == 1
        assert galaxy.org_id == api_tester_user.org_id
        clusters = self._clusters(galaxy)
        assert sorted(clusters) == ["APT1", "APT2"]
        assert clusters["APT1"].tag_name == 'misp-galaxy:test-actor="APT1"'
        assert clusters["APT1"].description == "APT1 v1"
        assert clusters["APT1"].authors == ["test"]
        assert self._elements(clusters["APT1"]) == [
            ("country", "CN"),
            ("synonyms", '["Comment Crew"]'),
        ]
        assert self._elements(clusters["APT2"]) == []

        assert sorted(self._clusters(self._load(db, "test-mirror"))) == ["APT3"]

        # same version: nothing to do
        assert galaxies_repository.update_galaxies(db, api_tester_user, *dirs) == []

        # new clusters version: the new cluster is inserted, existing ones are
        # updated in place and their elements replaced
        _write_galaxy(
            tmp_path,
            "test-actor",
            2,
            [("APT1", {"country": "US"}), ("APT2", {"country": "RU"}), ("APT4", {})],
        )
        imported = galaxies_repository.update_galaxies(db, api_tester_user, *dirs)
        assert len(imported) == 1

        galaxy = self._load(db, "test-actor")
        assert galaxy.version == 1
        assert galaxy.name == "test-actor v2"
        updated_clusters = self._clusters(galaxy)
        assert sorted(updated_clusters) == ["APT1", "APT2", "APT4"]
        assert updated_clusters["APT1"].id == clusters["APT1"].id
        assert updated_clusters["APT1"].description == "APT1 v2"
        assert updated_clusters["APT1"].version == 2
        assert self._elements(updated_clusters["APT1"]) == [("country", "US")]
        assert self._elements(updated_clusters["APT2"]) == [("country", "RU")]

        # new galaxy version: picked up as well
        _write_galaxy(tmp_path, "test-mirror", 1, [("APT3", {})], galaxy_version=2)
        imported = galaxies_repository.update_galaxies(db, api_tester_user, *dirs)
        assert len(imported) == 1
        assert self._load(db, "test-mirror").version == 2

        # the tags of the clusters added to an enabled galaxy are created
        galaxy.enabled = True
        db.commit()
        galaxies_repository.enable_galaxy_tags(db, galaxy)
        _write_galaxy(tmp_path, "test-actor", 3, [("APT1", {}), ("APT5", {})])
        galaxies_repository.update_galaxies(db, api_tester_user, *dirs)
        tag_names = db.scalars(
            select(tags_models.Tag.name).where(
                tags_models.Tag.name.startswith("misp-galaxy:test-actor=")
            )
        ).all()
        assert sorted(tag_names) == [
            'misp-galaxy:test-actor="APT1"',
            'misp-galaxy:test-actor="APT2"',
            'misp-galaxy:test-actor="APT4"',
            'misp-galaxy:test-actor="APT5"',
        ]

    def test_enable_and_disable_galaxy_tags(
        self, db: Session, api_tester_user: user_models.User, tmp_path
    ):
        # own type and cluster uuids (derived from the value) so it does not
        # see clusters left by the import test
        dirs = _write_galaxy(tmp_path, "tag-actor", 1, [("TAG1", {}), ("TAG2", {})])
        galaxies_repository.update_galaxies(db, api_tester_user, *dirs)
        galaxy = self._load(db, "tag-actor")

        # a pre-existing tag must not be duplicated, and tags of a galaxy whose
        # type shares the prefix must not be touched
        for name in ['misp-galaxy:tag-actor="TAG1"', 'misp-galaxy:tag-actor-x="X"']:
            db.add(
                tags_models.Tag(
                    name=name, colour="#BBBBBB", exportable=True, hide_tag=False
                )
            )
        db.commit()

        galaxies_repository.enable_galaxy_tags(db, galaxy)
        galaxies_repository.enable_galaxy_tags(db, galaxy)

        def tags():
            db.expire_all()
            return {
                tag.name: tag
                for tag in db.query(tags_models.Tag)
                .filter(tags_models.Tag.name.startswith("misp-galaxy:tag-actor"))
                .all()
            }

        assert sorted(tags()) == [
            'misp-galaxy:tag-actor-x="X"',
            'misp-galaxy:tag-actor="TAG1"',
            'misp-galaxy:tag-actor="TAG2"',
        ]
        new_tag = tags()['misp-galaxy:tag-actor="TAG2"']
        assert new_tag.is_galaxy and new_tag.exportable and not new_tag.hide_tag

        galaxies_repository.disable_galaxy_tags(db, galaxy)
        assert {name: tag.hide_tag for name, tag in tags().items()} == {
            'misp-galaxy:tag-actor-x="X"': False,
            'misp-galaxy:tag-actor="TAG1"': True,
            'misp-galaxy:tag-actor="TAG2"': True,
        }

        # re-enabling shows the galaxy tags again, without duplicating them
        galaxies_repository.enable_galaxy_tags(db, galaxy)
        assert {name: tag.hide_tag for name, tag in tags().items()} == {
            'misp-galaxy:tag-actor-x="X"': False,
            'misp-galaxy:tag-actor="TAG1"': False,
            'misp-galaxy:tag-actor="TAG2"': False,
        }
