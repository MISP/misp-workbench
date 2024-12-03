import json
import os

from app.models import taxonomy as taxonomies_models
from fastapi_pagination.ext.sqlalchemy import paginate
from sqlalchemy.orm import Session


def get_taxonomies(db: Session):
    query = db.query(taxonomies_models.Taxonomy)

    return paginate(query)


def update_taxonomies(db: Session):
    taxonomies = []
    objects_dir = "app/submodules/misp-taxonomies"

    for root, dirs, __ in os.walk(objects_dir):
        for taxonomy_dir in dirs:
            if not os.path.exists(os.path.join(root, taxonomy_dir, "machinetag.json")):
                continue

            template_def = os.path.join(root, taxonomy_dir, "machinetag.json")
            raw_taxonomy = open(template_def)
            raw_taxonomy = json.load(raw_taxonomy)

            # check if the taxonomy exists
            db_taxonomy = (
                db.query(taxonomies_models.Taxonomy)
                .filter(
                    taxonomies_models.Taxonomy.namespace == raw_taxonomy["namespace"]
                )
                .first()
            )

            if db_taxonomy is None:
                db_taxonomy = taxonomies_models.Taxonomy(
                    namespace=raw_taxonomy["namespace"],
                    description=raw_taxonomy["description"],
                    version=raw_taxonomy["version"],
                    enabled=False,
                    exclusive=False,
                    required=False,
                    highlighted=False,
                )

            if db_taxonomy.version != raw_taxonomy["version"] or db_taxonomy.id is None:
                # create/update the taxonomy
                db_taxonomy.version = raw_taxonomy["version"]

                db.add(db_taxonomy)
                db.commit()
                db.refresh(db_taxonomy)

            taxonomies.append(db_taxonomy)

            # process predicates
            predicates = []
            if "predicates" not in raw_taxonomy:
                continue
            for raw_predicate in raw_taxonomy["predicates"]:

                # check if the predicate exists
                db_predicate = (
                    db.query(taxonomies_models.TaxonomyPredicate)
                    .filter(
                        taxonomies_models.TaxonomyPredicate.taxonomy_id
                        == db_taxonomy.id,
                        taxonomies_models.TaxonomyPredicate.value
                        == raw_predicate["value"],
                    )
                    .first()
                )

                if db_predicate is None:
                    db_predicate = taxonomies_models.TaxonomyPredicate(
                        taxonomy_id=db_taxonomy.id,
                        expanded=(
                            raw_predicate["expanded"]
                            if "expanded" in raw_predicate
                            else raw_predicate["value"]
                        ),
                        value=raw_predicate["value"],
                    )

                    db.add(db_predicate)
                    db.commit()
                    db.refresh(db_predicate)

                predicates.append(db_predicate)

            # process entries
            entries = []
            if "values" not in raw_taxonomy:
                continue

            for raw_predicate_entries in raw_taxonomy["values"]:

                # get the predicate
                db_predicate = [
                    p
                    for p in predicates
                    if p.value == raw_predicate_entries["predicate"]
                ][0]

                for raw_entry in raw_predicate_entries["entry"]:
                    # check if the entry exists
                    db_entry = (
                        db.query(taxonomies_models.TaxonomyEntry)
                        .filter(
                            taxonomies_models.TaxonomyEntry.taxonomy_predicate_id
                            == db_predicate.id,
                            taxonomies_models.TaxonomyEntry.value == raw_entry["value"],
                        )
                        .first()
                    )

                    if db_entry is None:
                        db_entry = taxonomies_models.TaxonomyEntry(
                            taxonomy_predicate_id=db_predicate.id,
                            expanded=(
                                raw_entry["expanded"]
                                if "expanded" in raw_entry
                                else raw_entry["value"]
                            ),
                            value=raw_entry["value"],
                            description=(
                                raw_entry["description"]
                                if "description" in raw_entry
                                else ""
                            ),
                        )

                        db.add(db_entry)
                        db.commit()
                        db.refresh(db_entry)

                    entries.append(db_entry)

    return taxonomies
