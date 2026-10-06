import json
import uuid

import pytest
from app.auth import auth
from app.models import tag as tags_models
from app.models import taxonomy as taxonomies_models
from app.repositories import taxonomies as taxonomies_repository
from app.tests.api_tester import ApiTester
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session


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


def _uuid(*parts):
    return str(uuid.uuid5(uuid.NAMESPACE_URL, ":".join(parts)))


def _entry(namespace, entry):
    """An entry is either its value or a dict with the value and extra fields."""
    entry = {"value": entry} if isinstance(entry, str) else dict(entry)
    entry.setdefault("uuid", _uuid(namespace, "colour", entry["value"]))
    return entry


def _write_taxonomy(
    taxonomies_dir,
    version,
    entries,
    namespace="test-taxonomy",
    description="Test taxonomy",
    empty_expanded="Predicate without entries",
):
    taxonomy_dir = taxonomies_dir / namespace
    taxonomy_dir.mkdir(exist_ok=True)
    (taxonomy_dir / "machinetag.json").write_text(
        json.dumps(
            {
                "namespace": namespace,
                "uuid": _uuid(namespace),
                "description": description,
                "version": version,
                "predicates": [
                    {
                        "value": "colour",
                        "uuid": _uuid(namespace, "colour"),
                        "colour": "#ff0000",
                    },
                    {
                        "value": "empty",
                        "uuid": _uuid(namespace, "empty"),
                        "expanded": empty_expanded,
                    },
                ],
                "values": [
                    {
                        "predicate": "colour",
                        "entry": [_entry(namespace, entry) for entry in entries],
                    }
                ],
            }
        )
    )


RED = {"value": "red", "colour": "#cc0000"}
GREEN, BLUE = "green", "blue"


class TestTaxonomiesImport(ApiTester):
    def _load(self, db: Session, namespace="test-taxonomy"):
        db_taxonomy = (
            db.query(taxonomies_models.Taxonomy)
            .filter(taxonomies_models.Taxonomy.namespace == namespace)
            .one()
        )
        db.refresh(db_taxonomy)
        return db_taxonomy

    def _entries(self, db_taxonomy):
        return {
            predicate.value: sorted(entry.value for entry in predicate.entries)
            for predicate in db_taxonomy.predicates
        }

    def test_import_and_update_taxonomies(self, db: Session, tmp_path):
        _write_taxonomy(tmp_path, 1, [RED, GREEN])

        imported = taxonomies_repository.update_taxonomies(db, str(tmp_path))
        assert len(imported) == 1

        db_taxonomy = self._load(db)
        assert db_taxonomy.version == 1
        assert self._entries(db_taxonomy) == {
            "colour": ["green", "red"],
            "empty": [],
        }
        predicates = {p.value: p for p in db_taxonomy.predicates}
        assert predicates["colour"].colour == "#ff0000"
        assert predicates["colour"].expanded == "colour"
        assert predicates["empty"].colour == "#ffffff"
        assert predicates["empty"].expanded == "Predicate without entries"
        entries = {e.value: e for e in predicates["colour"].entries}
        assert entries["red"].colour == "#cc0000"
        assert entries["green"].colour is None

        # same version: nothing to do
        assert taxonomies_repository.update_taxonomies(db, str(tmp_path)) == []

        # new version: the new entry is inserted, existing rows are updated in
        # place (no duplicates)
        _write_taxonomy(
            tmp_path,
            2,
            [
                RED,
                {"value": "green", "colour": "#00cc00", "expanded": "Green!"},
                BLUE,
            ],
            description="Test taxonomy v2",
            empty_expanded="Still no entries",
        )
        imported = taxonomies_repository.update_taxonomies(db, str(tmp_path))
        assert len(imported) == 1

        db_taxonomy = self._load(db)
        assert db_taxonomy.version == 2
        assert db_taxonomy.description == "Test taxonomy v2"
        assert len(db_taxonomy.predicates) == 2
        assert self._entries(db_taxonomy) == {
            "colour": ["blue", "green", "red"],
            "empty": [],
        }
        updated_predicates = {p.value: p for p in db_taxonomy.predicates}
        assert updated_predicates["empty"].id == predicates["empty"].id
        assert updated_predicates["empty"].expanded == "Still no entries"
        updated_entries = {e.value: e for e in updated_predicates["colour"].entries}
        assert updated_entries["green"].id == entries["green"].id
        assert updated_entries["green"].colour == "#00cc00"
        assert updated_entries["green"].expanded == "Green!"
        assert updated_entries["red"].colour == "#cc0000"

    def test_enable_and_disable_taxonomy_tags(self, db: Session, tmp_path):
        # own namespace so it does not see entries left by the import test
        _write_taxonomy(tmp_path, 1, [RED, GREEN], namespace="tag-taxonomy")
        taxonomies_repository.update_taxonomies(db, str(tmp_path))
        db_taxonomy = self._load(db, "tag-taxonomy")

        # a pre-existing tag must not be duplicated
        db.add(
            tags_models.Tag(
                name="tag-taxonomy:colour",
                colour="#ff0000",
                exportable=True,
                hide_tag=False,
            )
        )
        db.commit()

        taxonomies_repository.enable_taxonomy_tags(db, db_taxonomy)
        taxonomies_repository.enable_taxonomy_tags(db, db_taxonomy)

        tags = (
            db.query(tags_models.Tag)
            .filter(tags_models.Tag.name.startswith("tag-taxonomy:"))
            .all()
        )
        assert sorted(tag.name for tag in tags) == [
            "tag-taxonomy:colour",
            "tag-taxonomy:colour:green",
            "tag-taxonomy:colour:red",
            "tag-taxonomy:empty",
        ]
        assert all(not tag.hide_tag for tag in tags)
        colours = {tag.name: tag.colour for tag in tags}
        # entry colour when set, otherwise the predicate colour
        assert colours["tag-taxonomy:colour:red"] == "#cc0000"
        assert colours["tag-taxonomy:colour:green"] == "#ff0000"
        assert colours["tag-taxonomy:empty"] == "#ffffff"

        taxonomies_repository.disable_taxonomy_tags(db, db_taxonomy)
        tags = (
            db.query(tags_models.Tag)
            .filter(tags_models.Tag.name.startswith("tag-taxonomy:"))
            .all()
        )
        for tag in tags:
            db.refresh(tag)
        assert len(tags) == 4
        assert all(tag.hide_tag for tag in tags)
