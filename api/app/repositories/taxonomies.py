import json
import os
import logging

from app.models import tag as tags_models
from app.models import taxonomy as taxonomies_models
from app.schemas import taxonomy as taxonomies_schemas
from fastapi import HTTPException, Query, status
from fastapi_pagination.ext.sqlalchemy import paginate
from sqlalchemy.orm import Session
from sqlalchemy.sql import select

logger = logging.getLogger(__name__)


def get_taxonomies(
    db: Session, enabled: bool = Query(None), filter: str = Query(None)
) -> taxonomies_models.Taxonomy:
    query = select(taxonomies_models.Taxonomy)

    if filter:
        query = query.where(taxonomies_models.Taxonomy.namespace.ilike(f"%{filter}%"))

    if enabled is not None:
        query = query.where(taxonomies_models.Taxonomy.enabled == enabled)

    query = query.order_by(taxonomies_models.Taxonomy.namespace)

    return paginate(
        db,
        query,
        additional_data={"query": {"enabled": enabled, "filter": filter}},
    )


def get_taxonomy_by_id(db: Session, taxonomy_id: int) -> taxonomies_models.Taxonomy:
    return (
        db.query(taxonomies_models.Taxonomy)
        .filter(taxonomies_models.Taxonomy.id == taxonomy_id)
        .first()
    )


def get_taxonomy_by_uuid(db: Session, taxonomy_uuid: str) -> taxonomies_models.Taxonomy:
    return (
        db.query(taxonomies_models.Taxonomy)
        .filter(taxonomies_models.Taxonomy.uuid == str(taxonomy_uuid))
        .first()
    )


def get_or_create_predicate(db: Session, db_taxonomy, raw_predicate):
    db_predicate = (
        db.query(taxonomies_models.TaxonomyPredicate)
        .filter(
            taxonomies_models.TaxonomyPredicate.taxonomy_id == db_taxonomy.id,
            taxonomies_models.TaxonomyPredicate.value == raw_predicate["value"],
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
            uuid=raw_predicate["uuid"],
            value=raw_predicate["value"],
            colour=(
                raw_predicate["colour"] if "colour" in raw_predicate else "#ffffff"
            ),
        )
    return db_predicate


def get_or_create_predicate_tag(db: Session, db_taxonomy, db_predicate):
    predicate_tag = f"{db_taxonomy.namespace}:{db_predicate.value}"
    db_predicate_tag = (
        db.query(tags_models.Tag)
        .filter(
            tags_models.Tag.name == predicate_tag,
        )
        .first()
    )

    if db_predicate_tag is None:
        db_predicate_tag = tags_models.Tag(
            name=predicate_tag,
            colour=db_predicate.colour or "#ffffff",
            exportable=False,
            hide_tag=False,
            is_galaxy=False,
            is_custom_galaxy=False,
            local_only=False,
        )

    return db_predicate_tag


def get_or_create_entry(db: Session, db_predicate, raw_entry):
    db_entry = (
        db.query(taxonomies_models.TaxonomyEntry)
        .filter(
            taxonomies_models.TaxonomyEntry.taxonomy_predicate_id == db_predicate.id,
            taxonomies_models.TaxonomyEntry.value == raw_entry["value"],
        )
        .first()
    )

    if db_entry is None:
        db_entry = taxonomies_models.TaxonomyEntry(
            taxonomy_predicate_id=db_predicate.id,
            uuid=raw_entry["uuid"],
            expanded=(
                raw_entry["expanded"] if "expanded" in raw_entry else raw_entry["value"]
            ),
            value=raw_entry["value"],
            description=(
                raw_entry["description"] if "description" in raw_entry else ""
            ),
        )

    return db_entry


def get_or_create_predicate_entry_tag(
    db: Session, db_taxonomy, db_predicate, db_predicate_entry
):
    predicate_entry_tag = (
        f"{db_taxonomy.namespace}:{db_predicate.value}:{db_predicate_entry.value}"
    )
    db_predicate_entry_tag = (
        db.query(tags_models.Tag)
        .filter(
            tags_models.Tag.name == predicate_entry_tag,
        )
        .first()
    )

    if db_predicate_entry_tag is None:
        db_predicate_entry_tag = tags_models.Tag(
            name=predicate_entry_tag,
            colour=db_predicate_entry.colour or "#ffffff",
            exportable=False,
            hide_tag=False,
            is_galaxy=False,
            is_custom_galaxy=False,
            local_only=False,
        )

    return db_predicate_entry_tag


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
                    uuid=raw_taxonomy["uuid"],
                    namespace=raw_taxonomy["namespace"],
                    description=raw_taxonomy["description"],
                    version=raw_taxonomy["version"],
                    enabled=False,
                    exclusive=(
                        raw_taxonomy["exclusive"]
                        if "exclusive" in raw_taxonomy
                        else False
                    ),
                    required=False,
                    highlighted=False,
                )

            if db_taxonomy.version != raw_taxonomy["version"] or db_taxonomy.id is None:
                # create/update the taxonomy
                db_taxonomy.version = raw_taxonomy["version"]

                db.add(db_taxonomy)
                db.commit()
                db.refresh(db_taxonomy)
            else:
                logger.debug(
                    f"Taxonomy {db_taxonomy.namespace} is up to date. Skipping."
                )
                continue

            taxonomies.append(db_taxonomy)

            # process predicates
            predicates = []
            if "predicates" not in raw_taxonomy:
                continue
            for raw_predicate in raw_taxonomy["predicates"]:
                # check if the predicate exists
                db_predicate = get_or_create_predicate(db, db_taxonomy, raw_predicate)
                db.add(db_predicate)
                db.commit()
                db.refresh(db_predicate)

                predicates.append(db_predicate)

            # process entries
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
                    db_entry = get_or_create_entry(db, db_predicate, raw_entry)
                    db.add(db_entry)

                db.commit()
                logger.debug(
                    f"Processed {len(raw_predicate_entries['entry'])} entries for predicate {db_predicate.value} in taxonomy {db_taxonomy.namespace}"
                )

    return taxonomies


def enable_taxonomy_tags(db: Session, db_taxonomy):

    for db_predicate in db_taxonomy.predicates:
        # check if the predicate exists in the tags table
        db_predicate_tag = get_or_create_predicate_tag(db, db_taxonomy, db_predicate)
        db.add(db_predicate_tag)

        for db_predicate_entry in db_predicate.entries:
            # check if the predicate entry exists in the tags table
            db_predicate_entry_tag = get_or_create_predicate_entry_tag(
                db,
                db_taxonomy,
                db_predicate,
                db_predicate_entry,
            )
            db.add(db_predicate_entry_tag)

        db.commit()


def disable_taxonomy_tags(db: Session, db_taxonomy):
    # delete all tags from the taxonomy
    db_taxonomy_tags = (
        db.query(tags_models.Tag)
        .filter(tags_models.Tag.name.ilike(f"{db_taxonomy.namespace}:%"))
        .all()
    )

    for tag in db_taxonomy_tags:
        tag.hide_tag = True
        db.add(tag)

    db.commit()


def update_taxonomy(
    db: Session,
    taxonomy_id: int,
    taxonomy: taxonomies_schemas.TaxonomyUpdate,
) -> taxonomies_models.Taxonomy:
    db_taxonomy = get_taxonomy_by_id(db, taxonomy_id=taxonomy_id)

    if db_taxonomy is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Taxonomy not found"
        )

    taxonomy_patch = taxonomy.model_dump(exclude_unset=True)
    for key, value in taxonomy_patch.items():
        setattr(db_taxonomy, key, value)

    # if taxonomy is enabled, update the tags
    if db_taxonomy.enabled and taxonomy_patch["enabled"]:
        enable_taxonomy_tags(db, db_taxonomy)
    elif not db_taxonomy.enabled and not taxonomy_patch["enabled"]:
        disable_taxonomy_tags(db, db_taxonomy)

    db.add(db_taxonomy)
    db.commit()
    db.refresh(db_taxonomy)

    return db_taxonomy
