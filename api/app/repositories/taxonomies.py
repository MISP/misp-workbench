import json
import os
import logging

from app.models import tag as tags_models
from app.models import taxonomy as taxonomies_models
from app.schemas import taxonomy as taxonomies_schemas
from fastapi import HTTPException, Query, status
from fastapi_pagination.ext.sqlalchemy import paginate
from sqlalchemy.orm import Session
from sqlalchemy.sql import insert, select, update

logger = logging.getLogger(__name__)

TAXONOMIES_DIR = "app/submodules/misp-taxonomies"


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


def _predicate_row(taxonomy_id: int, raw_predicate: dict) -> dict:
    return {
        "taxonomy_id": taxonomy_id,
        "uuid": raw_predicate["uuid"],
        "value": raw_predicate["value"],
        "expanded": raw_predicate.get("expanded", raw_predicate["value"]),
        "colour": raw_predicate.get("colour", "#ffffff"),
    }


def _entry_row(predicate_id: int, raw_entry: dict) -> dict:
    return {
        "taxonomy_predicate_id": predicate_id,
        "uuid": raw_entry["uuid"],
        "value": raw_entry["value"],
        "expanded": raw_entry.get("expanded", raw_entry["value"]),
        "colour": raw_entry.get("colour"),
        "description": raw_entry.get("description", ""),
    }


def _tag_row(name: str, colour: str) -> dict:
    return {
        "name": name,
        "colour": colour or "#ffffff",
        "exportable": False,
        "hide_tag": False,
        "is_galaxy": False,
        "is_custom_galaxy": False,
        "local_only": False,
    }


def import_taxonomy_predicates(db: Session, db_taxonomy, raw_taxonomy: dict) -> None:
    """Sync the predicates and entries of a taxonomy with its machinetag.json.

    Rows are matched by value: new ones are bulk inserted and existing ones are
    bulk updated with the definition from the file."""
    Predicate = taxonomies_models.TaxonomyPredicate
    Entry = taxonomies_models.TaxonomyEntry

    predicate_ids = dict(
        db.execute(
            select(Predicate.value, Predicate.id).where(
                Predicate.taxonomy_id == db_taxonomy.id
            )
        ).all()
    )

    new_predicates, updated_predicates = {}, {}
    for raw_predicate in raw_taxonomy.get("predicates", []):
        row = _predicate_row(db_taxonomy.id, raw_predicate)
        predicate_id = predicate_ids.get(row["value"])
        if predicate_id is None:
            new_predicates.setdefault(row["value"], row)
        else:
            updated_predicates.setdefault(predicate_id, {"id": predicate_id, **row})

    if updated_predicates:
        db.execute(update(Predicate), list(updated_predicates.values()))

    if new_predicates:
        predicate_ids.update(
            db.execute(
                insert(Predicate).returning(Predicate.value, Predicate.id),
                list(new_predicates.values()),
            ).all()
        )

    raw_values = raw_taxonomy.get("values", [])
    new_entries, updated_entries = {}, {}

    if raw_values and predicate_ids:
        entry_ids = {
            (predicate_id, value): entry_id
            for entry_id, predicate_id, value in db.execute(
                select(Entry.id, Entry.taxonomy_predicate_id, Entry.value).where(
                    Entry.taxonomy_predicate_id.in_(predicate_ids.values())
                )
            ).all()
        }

        for raw_predicate_entries in raw_values:
            predicate_id = predicate_ids.get(raw_predicate_entries["predicate"])
            if predicate_id is None:
                logger.warning(
                    f"Taxonomy {db_taxonomy.namespace} has values for unknown predicate {raw_predicate_entries['predicate']}. Skipping."
                )
                continue

            for raw_entry in raw_predicate_entries.get("entry", []):
                row = _entry_row(predicate_id, raw_entry)
                key = (predicate_id, row["value"])
                entry_id = entry_ids.get(key)
                if entry_id is None:
                    new_entries.setdefault(key, row)
                else:
                    updated_entries.setdefault(entry_id, {"id": entry_id, **row})

        if updated_entries:
            db.execute(update(Entry), list(updated_entries.values()))

        if new_entries:
            db.execute(insert(Entry), list(new_entries.values()))

    logger.debug(
        f"Taxonomy {db_taxonomy.namespace}: inserted {len(new_predicates)} predicates and {len(new_entries)} entries, "
        f"updated {len(updated_predicates)} predicates and {len(updated_entries)} entries"
    )


def update_taxonomies(db: Session, taxonomies_dir: str = TAXONOMIES_DIR):
    taxonomies = []

    for root, dirs, __ in os.walk(taxonomies_dir):
        for taxonomy_dir in dirs:
            template_def = os.path.join(root, taxonomy_dir, "machinetag.json")
            if not os.path.exists(template_def):
                continue

            with open(template_def) as f:
                raw_taxonomy = json.load(f)

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
                    exclusive=raw_taxonomy.get("exclusive", False),
                    required=False,
                    highlighted=False,
                )
            elif db_taxonomy.version == raw_taxonomy["version"]:
                logger.debug(
                    f"Taxonomy {db_taxonomy.namespace} is up to date. Skipping."
                )
                continue

            # create/update the taxonomy, its predicates and entries in one
            # transaction
            db_taxonomy.version = raw_taxonomy["version"]
            db_taxonomy.description = raw_taxonomy["description"]
            db_taxonomy.exclusive = raw_taxonomy.get("exclusive", False)
            db.add(db_taxonomy)
            db.flush()

            import_taxonomy_predicates(db, db_taxonomy, raw_taxonomy)

            db.commit()
            taxonomies.append(db_taxonomy)

    return taxonomies


def enable_taxonomy_tags(db: Session, db_taxonomy):
    existing_tags = set(
        db.scalars(
            select(tags_models.Tag.name).where(
                tags_models.Tag.name.startswith(
                    f"{db_taxonomy.namespace}:", autoescape=True
                )
            )
        ).all()
    )

    new_tags = {}
    for db_predicate in db_taxonomy.predicates:
        predicate_tag = f"{db_taxonomy.namespace}:{db_predicate.value}"
        if predicate_tag not in existing_tags:
            new_tags.setdefault(
                predicate_tag, _tag_row(predicate_tag, db_predicate.colour)
            )

        for db_predicate_entry in db_predicate.entries:
            entry_tag = f"{predicate_tag}:{db_predicate_entry.value}"
            if entry_tag not in existing_tags:
                new_tags.setdefault(
                    entry_tag,
                    _tag_row(
                        entry_tag, db_predicate_entry.colour or db_predicate.colour
                    ),
                )

    if new_tags:
        db.execute(insert(tags_models.Tag), list(new_tags.values()))

    db.commit()


def disable_taxonomy_tags(db: Session, db_taxonomy):
    # hide all tags from the taxonomy
    db.execute(
        update(tags_models.Tag)
        .where(tags_models.Tag.name.ilike(f"{db_taxonomy.namespace}:%"))
        .values(hide_tag=True)
        .execution_options(synchronize_session=False)
    )
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
