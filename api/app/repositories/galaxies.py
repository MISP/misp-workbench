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

    for root, __, files in os.walk(galaxies_dir):
        for galaxy_file in files:
            if not galaxy_file.endswith(".json"):
                continue

            with open(os.path.join(root, galaxy_file)) as f:
                galaxy_data = json.load(f)

                # check galaxy version
                if (
                    db.query(galaxies_models.Galaxy)
                    .filter(
                        galaxies_models.Galaxy.uuid == galaxy_data["uuid"],
                        galaxies_models.Galaxy.version == galaxy_data["version"],
                    )
                    .first()
                ):
                    logger.debug(
                        f"Galaxy {galaxy_data['name']} version {galaxy_data['version']} already exists. Skipping."
                    )
                    continue

                galaxy = galaxies_models.Galaxy(
                    name=galaxy_data["name"],
                    uuid=galaxy_data["uuid"],
                    namespace=(
                        galaxy_data["namespace"]
                        if "namespace" in galaxy_data
                        else "missing-namespace"
                    ),
                    version=galaxy_data["version"],
                    description=galaxy_data["description"],
                    icon=galaxy_data["icon"],
                    type=galaxy_data["type"],
                    kill_chain_order=(
                        galaxy_data["kill_chain_order"]
                        if "kill_chain_order" in galaxy_data
                        else None
                    ),
                    org_id=user.org_id,
                    orgc_id=user.org_id,
                    created=datetime.now(),
                    modified=datetime.now(),
                )

                # parse galaxy clusters file
                with open(os.path.join(galaxies_clusters_dir, galaxy_file)) as f:
                    clusters_data_raw = json.load(f)

                    if "values" in clusters_data_raw:
                        for cluster in clusters_data_raw["values"]:
                            galaxy_cluster = galaxies_models.GalaxyCluster(
                                uuid=cluster["uuid"],
                                value=cluster["value"],
                                type=(
                                    clusters_data_raw["type"]
                                    if "type" in clusters_data_raw
                                    else galaxy.type
                                ),
                                description=(
                                    cluster["description"]
                                    if "description" in cluster
                                    else ""
                                ),
                                source=(
                                    clusters_data_raw["source"]
                                    if "source" in clusters_data_raw
                                    else None
                                ),
                                version=clusters_data_raw["version"],
                                authors=(
                                    clusters_data_raw["authors"]
                                    if "authors" in clusters_data_raw
                                    else None
                                ),
                                tag_name=f"misp-galaxy:{galaxy.type}={cluster['uuid']}",
                                org_id=user.org_id,
                                orgc_id=user.org_id,
                                collection_uuid=(
                                    clusters_data_raw["collection_uuid"]
                                    if "collection_uuid" in clusters_data_raw
                                    else None
                                ),
                                extends_uuid=(
                                    clusters_data_raw["extends_uuid"]
                                    if "extends_uuid" in clusters_data_raw
                                    else None
                                ),
                                extends_version=(
                                    clusters_data_raw["extends_version"]
                                    if "extends_version" in clusters_data_raw
                                    else None
                                ),
                            )
                            galaxy.clusters.append(galaxy_cluster)

                            # add galaxy elements
                            if "meta" in cluster:
                                for element in cluster["meta"]:
                                    galaxy_element = galaxies_models.GalaxyElement(
                                        key=element,
                                        value=(
                                            cluster["meta"][element]
                                            if isinstance(cluster["meta"][element], str)
                                            else json.dumps(cluster["meta"][element])
                                        ),
                                    )
                                    galaxy_cluster.elements.append(galaxy_element)

                            # TODO: fix import galaxy cluster relations
                            # # add galaxy relations
                            # if "related" in cluster:
                            #     for relation in cluster["related"]:

                            #         # check if valid uuid
                            #         if (
                            #             "dest-uuid" not in relation
                            #             or not relation["dest-uuid"]
                            #         ):
                            #             logger.warning(
                            #                 f"Missing dest-uuid {relation['dest-uuid']} for galaxy {galaxy.name}"
                            #             )
                            #             continue

                            #         try:
                            #             UUID(relation["dest-uuid"])
                            #         except ValueError:
                            #             logger.warning(
                            #                 f"Invalid dest-uuid {relation['dest-uuid']} for galaxy {galaxy.name}"
                            #             )
                            #             continue

                            #         galaxy_relation = galaxies_models.GalaxyClusterRelation(
                            #             galaxy_cluster_uuid=cluster["uuid"],
                            #             referenced_galaxy_cluster_uuid=relation[
                            #                 "dest-uuid"
                            #             ],
                            #             referenced_galaxy_cluster_type=relation["type"],
                            #             default=True,
                            #             distribution=events_models.DistributionLevel.ALL_COMMUNITIES,
                            #         )

                            #         if "tags" in relation:
                            #             for related_tag in relation["tags"]:
                            #                 tag = tags_repository.get_tag_by_name(
                            #                     db, tag_name=related_tag
                            #                 )

                            #                 if not tag:
                            #                     logger.warning(
                            #                         f"Tag {related_tag} not found for galaxy {galaxy.name}"
                            #                     )
                            #                     tag = tags_repository.create_tag(
                            #                         db,
                            #                         tag=tags_repository.tag_schemas.TagCreate(
                            #                             name=related_tag,
                            #                             colour="#000000",
                            #                             exportable=True,
                            #                             org_id=user.org_id,
                            #                             user_id=user.id,
                            #                             hide_tag=False,
                            #                             is_galaxy=False,
                            #                             is_custom_galaxy=False,
                            #                             local_only=False,
                            #                         ),
                            #                     )

                            #                 galaxy_relation_tag = galaxies_models.GalaxyClusterRelationTag(
                            #                     tag=tag,
                            #                 )

                            #                 galaxy_relation.tags.append(
                            #                     galaxy_relation_tag
                            #                 )

                            #         galaxy_cluster.relations.append(galaxy_relation)
                try:
                    db.add(galaxy)
                    db.commit()
                    db.refresh(galaxy)
                    galaxies.append(galaxy)
                    logger.debug(f"Imported galaxy {galaxy.name}")
                except Exception as e:
                    logger.error(f"Error creating galaxy {galaxy.name}: {e}")
                    db.rollback()

    # TODO: fix galaxy cluster relations references to galaxy clusters
    # relations = db.query(galaxies_models.GalaxyClusterRelation).all()
    # for relation in relations:
    #     galaxy_cluster = (
    #         db.query(galaxies_models.GalaxyCluster)
    #         .filter(
    #             galaxies_models.GalaxyCluster.uuid
    #             == relation.referenced_galaxy_cluster_uuid
    #         )
    #         .first()
    #     )

    #     if not galaxy_cluster:
    #         logger.warning(
    #             f"Galaxy cluster {relation.referenced_galaxy_cluster_uuid} not found"
    #         )
    #         continue

    #     relation.referenced_galaxy_cluster_id = galaxy_cluster.id
    #     db.add(relation)
    # db.commit()

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
