import json
import logging
import os
from datetime import datetime
from uuid import UUID

from app.models import event as events_models
from app.models import galaxy as galaxies_models
from app.models import tag as tags_models
from app.repositories import tags as tags_repository
from app.schemas import galaxy as galaxies_schemas
from app.schemas import user as users_schemas
from fastapi import HTTPException, Query, status
from fastapi_pagination.ext.sqlalchemy import paginate
from sqlalchemy.orm import Session
from sqlalchemy.sql import select

logger = logging.getLogger(__name__)


def get_galaxies(
    db: Session, enabled: bool = Query(None), filter: str = Query(None)
) -> galaxies_models.Galaxy:
    query = select(galaxies_models.Galaxy)

    if filter:
        query = query.where(galaxies_models.Galaxy.name.ilike(f"%{filter}%"))

    if enabled is not None:
        query = query.where(galaxies_models.Galaxy.enabled == enabled)

    query = query.order_by(galaxies_models.Galaxy.name)

    return paginate(
        db,
        query,
        additional_data={"query": {"filter": filter}},
    )


def get_galaxy_by_id(db: Session, galaxy_id: int) -> galaxies_models.Galaxy:
    return (
        db.query(galaxies_models.Galaxy)
        .filter(galaxies_models.Galaxy.id == galaxy_id)
        .first()
    )


def update_galaxies(
    db: Session, user: users_schemas.User
) -> list[galaxies_schemas.Galaxy]:
    galaxies = []
    galaxies_dir = "app/submodules/misp-galaxy/galaxies"
    galaxies_clusters_dir = "app/submodules/misp-galaxy/clusters"

    # read all galaxy files and upsert them. The function is idempotent:
    # - if a galaxy with the same uuid exists and the version matches, skip it
    # - otherwise update fields and upsert clusters
    for root, __, files in os.walk(galaxies_dir):
        for galaxy_file in files:
            if not galaxy_file.endswith(".json"):
                continue

            galaxy_path = os.path.join(root, galaxy_file)
            clusters_path = os.path.join(galaxies_clusters_dir, galaxy_file)

            try:
                with open(galaxy_path) as f:
                    galaxy_data = json.load(f)
            except Exception as e:
                logger.warning("Failed to read galaxy file %s: %s", galaxy_path, e)
                continue

            # try to find an existing galaxy by uuid
            db_galaxy = (
                db.query(galaxies_models.Galaxy)
                .filter(galaxies_models.Galaxy.uuid == galaxy_data["uuid"])
                .first()
            )

            # if exists and same version, skip to save time
            if db_galaxy and getattr(db_galaxy, "version", None) == galaxy_data.get("version"):
                logger.debug("Skipping galaxy %s (version unchanged)", galaxy_data.get("name"))
                galaxies.append(db_galaxy)
                continue

            # create or update the galaxy
            if not db_galaxy:
                db_galaxy = galaxies_models.Galaxy(
                    name=galaxy_data.get("name"),
                    uuid=galaxy_data.get("uuid"),
                    namespace=galaxy_data.get("namespace", "missing-namespace"),
                    version=galaxy_data.get("version"),
                    description=galaxy_data.get("description"),
                    icon=galaxy_data.get("icon"),
                    type=galaxy_data.get("type"),
                    kill_chain_order=galaxy_data.get("kill_chain_order"),
                    org_id=user.org_id,
                    orgc_id=user.org_id,
                    created=datetime.now(),
                    modified=datetime.now(),
                )
                db.add(db_galaxy)
                db.flush()
            else:
                # update fields
                db_galaxy.name = galaxy_data.get("name")
                db_galaxy.namespace = galaxy_data.get("namespace", db_galaxy.namespace)
                db_galaxy.version = galaxy_data.get("version")
                db_galaxy.description = galaxy_data.get("description")
                db_galaxy.icon = galaxy_data.get("icon")
                db_galaxy.type = galaxy_data.get("type")
                db_galaxy.kill_chain_order = galaxy_data.get("kill_chain_order")
                db_galaxy.modified = datetime.now()

            # parse galaxy clusters file if present
            if not os.path.exists(clusters_path):
                logger.debug("Clusters file not found for galaxy %s", galaxy_file)
                try:
                    db.commit()
                    db.refresh(db_galaxy)
                    galaxies.append(db_galaxy)
                except Exception:
                    db.rollback()
                continue

            try:
                with open(clusters_path) as f:
                    clusters_data_raw = json.load(f)
            except Exception as e:
                logger.warning("Failed to read clusters file %s: %s", clusters_path, e)
                try:
                    db.commit()
                    db.refresh(db_galaxy)
                    galaxies.append(db_galaxy)
                except Exception:
                    db.rollback()
                continue

            if "values" in clusters_data_raw:
                for cluster in clusters_data_raw["values"]:
                    # try to find existing cluster by uuid
                    db_cluster = (
                        db.query(galaxies_models.GalaxyCluster)
                        .filter(galaxies_models.GalaxyCluster.uuid == cluster["uuid"]) 
                        .first()
                    )

                    if not db_cluster:
                        db_cluster = galaxies_models.GalaxyCluster(
                            uuid=cluster["uuid"],
                            value=cluster.get("value"),
                            type=clusters_data_raw.get("type", db_galaxy.type),
                            description=cluster.get("description", ""),
                            source=clusters_data_raw.get("source"),
                            version=clusters_data_raw.get("version"),
                            authors=clusters_data_raw.get("authors"),
                            tag_name=f"misp-galaxy:{db_galaxy.type}={cluster['uuid']}",
                            org_id=user.org_id,
                            orgc_id=user.org_id,
                            collection_uuid=clusters_data_raw.get("collection_uuid"),
                            extends_uuid=clusters_data_raw.get("extends_uuid"),
                            extends_version=clusters_data_raw.get("extends_version"),
                        )
                        # set foreign key explicitly (no backref on GalaxyCluster)
                        db_cluster.galaxy_id = db_galaxy.id
                        db.add(db_cluster)
                        db.flush()
                    else:
                        # update cluster fields and ensure association
                        db_cluster.value = cluster.get("value")
                        db_cluster.type = clusters_data_raw.get("type", db_cluster.type)
                        db_cluster.description = cluster.get("description", db_cluster.description)
                        db_cluster.source = clusters_data_raw.get("source", db_cluster.source)
                        db_cluster.version = clusters_data_raw.get("version", db_cluster.version)
                        db_cluster.authors = clusters_data_raw.get("authors", db_cluster.authors)
                        db_cluster.tag_name = f"misp-galaxy:{db_galaxy.type}={cluster['uuid']}"
                        db_cluster.collection_uuid = clusters_data_raw.get("collection_uuid", db_cluster.collection_uuid)
                        db_cluster.extends_uuid = clusters_data_raw.get("extends_uuid", db_cluster.extends_uuid)
                        db_cluster.extends_version = clusters_data_raw.get("extends_version", db_cluster.extends_version)
                        # ensure cluster is associated with the parent galaxy
                        db_cluster.galaxy_id = db_galaxy.id

                    # replace elements: delete existing then add current ones
                    db.query(galaxies_models.GalaxyElement).filter(
                        galaxies_models.GalaxyElement.galaxy_cluster_id == db_cluster.id
                    ).delete(synchronize_session=False)

                    if "meta" in cluster:
                        for element_key in cluster["meta"]:
                            value = cluster["meta"][element_key]
                            elem_value = (
                                value if isinstance(value, str) else json.dumps(value)
                            )
                            galaxy_element = galaxies_models.GalaxyElement(
                                key=element_key,
                                value=elem_value,
                                galaxy_cluster_id=db_cluster.id,
                            )
                            db.add(galaxy_element)

                    # replace relations for this cluster: delete existing relation tags then relations, then recreate
                    existing_relations = db.query(galaxies_models.GalaxyClusterRelation).filter(
                        galaxies_models.GalaxyClusterRelation.galaxy_cluster_uuid == cluster["uuid"]
                    ).all()

                    # delete tags that reference the relations first to avoid FK constraint errors
                    for rel in existing_relations:
                        db.query(galaxies_models.GalaxyClusterRelationTag).filter(
                            galaxies_models.GalaxyClusterRelationTag.galaxy_cluster_relation_id == rel.id
                        ).delete(synchronize_session=False)

                    # now delete the relations themselves
                    db.query(galaxies_models.GalaxyClusterRelation).filter(
                        galaxies_models.GalaxyClusterRelation.galaxy_cluster_uuid == cluster["uuid"]
                    ).delete(synchronize_session=False)

                    if "related" in cluster:
                        for relation in cluster["related"]:
                            # validate dest uuid
                            dest_uuid = relation.get("dest-uuid")
                            if not dest_uuid:
                                logger.warning(
                                    "Missing dest-uuid %s for galaxy %s",
                                    relation, db_galaxy.name,
                                )
                                continue
                            try:
                                UUID(dest_uuid)
                            except ValueError:
                                logger.warning(
                                    "Invalid dest-uuid %s for galaxy %s",
                                    dest_uuid, db_galaxy.name,
                                )
                                continue

                            galaxy_relation = galaxies_models.GalaxyClusterRelation(
                                galaxy_cluster_uuid=cluster["uuid"],
                                referenced_galaxy_cluster_uuid=dest_uuid,
                                referenced_galaxy_cluster_type=relation.get("type"),
                                default=True,
                                distribution=events_models.DistributionLevel.ALL_COMMUNITIES,
                            )

                            # attach tags to relation
                            if "tags" in relation:
                                for related_tag in relation["tags"]:
                                    tag = tags_repository.get_tag_by_name(db, tag_name=related_tag)
                                    if not tag:
                                        logger.warning("Tag %s not found for galaxy %s", related_tag, db_galaxy.name)
                                        tag = tags_repository.create_tag(
                                            db,
                                            tag=tags_repository.tag_schemas.TagCreate(
                                                name=related_tag,
                                                colour="#000000",
                                                exportable=True,
                                                org_id=user.org_id,
                                                user_id=user.id,
                                                hide_tag=False,
                                                is_galaxy=False,
                                                is_custom_galaxy=False,
                                                local_only=False,
                                            ),
                                        )

                                    galaxy_relation_tag = galaxies_models.GalaxyClusterRelationTag(tag=tag)
                                    galaxy_relation.tags.append(galaxy_relation_tag)

                            db_cluster.relations.append(galaxy_relation)

            # commit per-galaxy to avoid long-running transactions and reduce duplicates
            try:
                db.commit()
                db.refresh(db_galaxy)
                galaxies.append(db_galaxy)
            except Exception as e:
                logger.error("Error writing galaxy %s: %s", galaxy_data.get("name"), e)
                db.rollback()

    # fix galaxy cluster relations references to galaxy clusters (single pass)
    relations = db.query(galaxies_models.GalaxyClusterRelation).all()
    for relation in relations:
        galaxy_cluster = (
            db.query(galaxies_models.GalaxyCluster)
            .filter(
                galaxies_models.GalaxyCluster.uuid
                == relation.referenced_galaxy_cluster_uuid
            )
            .first()
        )

        if not galaxy_cluster:
            logger.warning(
                f"Galaxy cluster {relation.referenced_galaxy_cluster_uuid} not found"
            )
            continue

        relation.referenced_galaxy_cluster_id = galaxy_cluster.id
        db.add(relation)
    db.commit()

    return galaxies


def enable_galaxy_tags(db: Session, galaxy: galaxies_models.Galaxy):
    for cluster in galaxy.clusters:
        galaxy_cluster_tag = f'misp-galaxy:{galaxy.type}="{cluster.value}"'
        db_galaxy_cluster_tag = (
            db.query(tags_models.Tag)
            .filter(
                tags_models.Tag.name == galaxy_cluster_tag,
            )
            .first()
        )

        if db_galaxy_cluster_tag is None:
            db_galaxy_cluster_tag = tags_models.Tag(
                name=galaxy_cluster_tag,
                colour="#BBBBBB",
                exportable=True,
                hide_tag=False,
                is_galaxy=True,
                is_custom_galaxy=False,
                local_only=False,
            )

            db.add(db_galaxy_cluster_tag)
            db.commit()


def disable_galaxy_tags(db: Session, galaxy: galaxies_models.Galaxy):
    # delete all tags from the galaxy
    db_galaxy_tags = (
        db.query(tags_models.Tag)
        .filter(tags_models.Tag.name.ilike(f"misp-galaxy:{galaxy.type}%"))
        .all()
    )

    for tag in db_galaxy_tags:
        tag.hide_tag = True
        db.add(tag)

    db.commit()


def update_galaxy(
    db: Session,
    galaxy_id: int,
    galaxy: galaxies_schemas.GalaxyUpdate,
) -> galaxies_models.Galaxy:
    db_galaxy = get_galaxy_by_id(db, galaxy_id=galaxy_id)

    if db_galaxy is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Galaxy not found"
        )

    galaxy_patch = galaxy.model_dump(exclude_unset=True)
    for key, value in galaxy_patch.items():
        setattr(db_galaxy, key, value)

    # if galaxy is enabled, update the tags
    if db_galaxy.enabled and galaxy_patch["enabled"]:
        enable_galaxy_tags(db, db_galaxy)
    elif not db_galaxy.enabled and not galaxy_patch["enabled"]:
        disable_galaxy_tags(db, db_galaxy)

    db.add(db_galaxy)
    db.commit()
    db.refresh(db_galaxy)

    return db_galaxy
