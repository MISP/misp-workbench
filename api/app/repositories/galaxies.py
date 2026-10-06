import json
import logging
import os
from datetime import datetime

from fastapi import HTTPException, Query, status
from fastapi_pagination.ext.sqlalchemy import paginate
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session, noload
from sqlalchemy.sql import delete, func, insert, select, update

from app.models import galaxy as galaxies_models
from app.models import tag as tags_models
from app.schemas import galaxy as galaxies_schemas
from app.schemas import user as users_schemas

logger = logging.getLogger(__name__)

GALAXIES_DIR = "app/submodules/misp-galaxy/galaxies"
GALAXY_CLUSTERS_DIR = "app/submodules/misp-galaxy/clusters"


def get_galaxies(
    db: Session,
    enabled: bool = Query(None),
    filter: str = Query(None),
    include_clusters: bool = Query(False),
) -> galaxies_models.Galaxy:
    if include_clusters:
        query = select(galaxies_models.Galaxy)
    else:
        # avoid loading child relationships (clusters/elements) to keep the query lightweight
        query = select(galaxies_models.Galaxy).options(
            noload(galaxies_models.Galaxy.clusters)
        )

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


def get_mitre_attack_patterns(
    db: Session, filter: str | None = None, limit: int = 1000
) -> list[dict]:
    """Return mitre-attack-pattern clusters with their external_id for selectors."""
    query = (
        db.query(
            galaxies_models.GalaxyCluster.uuid,
            galaxies_models.GalaxyCluster.value,
            galaxies_models.GalaxyCluster.description,
            galaxies_models.GalaxyElement.value.label("external_id"),
        )
        .join(
            galaxies_models.GalaxyElement,
            galaxies_models.GalaxyElement.galaxy_cluster_id
            == galaxies_models.GalaxyCluster.id,
        )
        .filter(
            galaxies_models.GalaxyCluster.type == "mitre-attack-pattern",
            galaxies_models.GalaxyElement.key == "external_id",
        )
    )
    if filter:
        pattern = f"%{filter}%"
        query = query.filter(
            (galaxies_models.GalaxyCluster.value.ilike(pattern))
            | (galaxies_models.GalaxyElement.value.ilike(pattern))
        )
    query = query.order_by(galaxies_models.GalaxyElement.value.asc()).limit(limit)
    return [
        {
            "uuid": str(row.uuid),
            "value": row.value,
            "description": row.description,
            "external_id": row.external_id,
        }
        for row in query.all()
    ]


def get_galaxy_by_id(db: Session, galaxy_id: int) -> galaxies_models.Galaxy:
    return (
        db.query(galaxies_models.Galaxy)
        .filter(galaxies_models.Galaxy.id == galaxy_id)
        .first()
    )


def get_galaxy_by_uuid(db: Session, galaxy_uuid: str) -> galaxies_models.Galaxy:
    return (
        db.query(galaxies_models.Galaxy)
        .filter(galaxies_models.Galaxy.uuid == galaxy_uuid)
        .first()
    )


def _galaxy_fields(galaxy_data: dict) -> dict:
    return {
        "name": galaxy_data["name"],
        "namespace": galaxy_data.get("namespace", "missing-namespace"),
        "version": galaxy_data["version"],
        "description": galaxy_data["description"],
        "icon": galaxy_data["icon"],
        "type": galaxy_data["type"],
        "kill_chain_order": galaxy_data.get("kill_chain_order"),
    }


def _cluster_row(galaxy, clusters_data: dict, cluster: dict) -> dict:
    cluster_type = clusters_data.get("type", galaxy.type)
    return {
        "galaxy_id": galaxy.id,
        "uuid": cluster["uuid"],
        "value": cluster["value"],
        "type": cluster_type,
        "description": cluster.get("description", ""),
        "source": clusters_data.get("source"),
        "version": clusters_data["version"],
        "authors": clusters_data.get("authors"),
        # as MISP names the tags of the clusters it ships
        "tag_name": f'misp-galaxy:{cluster_type}="{cluster["value"]}"',
        "org_id": galaxy.org_id,
        "orgc_id": galaxy.orgc_id,
        "collection_uuid": clusters_data.get("collection_uuid"),
        "extends_uuid": clusters_data.get("extends_uuid"),
        "extends_version": clusters_data.get("extends_version"),
    }


def _element_rows(cluster_id: int, cluster: dict) -> list[dict]:
    return [
        {
            "galaxy_cluster_id": cluster_id,
            "key": key,
            "value": value if isinstance(value, str) else json.dumps(value),
        }
        for key, value in cluster.get("meta", {}).items()
    ]


def import_galaxy_clusters(db: Session, galaxy, clusters_data: dict) -> None:
    """Sync the clusters and elements of a galaxy with its clusters file.

    Clusters are matched by uuid: new ones are bulk inserted and the ones
    already in this galaxy are bulk updated, with their elements replaced.
    Cluster uuids are unique, but some (MITRE) clusters are shipped in more than
    one galaxy; those stay with the galaxy that imported them first."""
    Cluster = galaxies_models.GalaxyCluster
    Element = galaxies_models.GalaxyElement

    raw_clusters = {
        str(cluster["uuid"]): cluster for cluster in clusters_data.get("values", [])
    }

    existing_ids = {
        str(cluster_uuid): cluster_id
        for cluster_uuid, cluster_id in db.execute(
            select(Cluster.uuid, Cluster.id).where(Cluster.galaxy_id == galaxy.id)
        ).all()
    }

    new_clusters, updated_clusters = [], []
    for cluster_uuid, cluster in raw_clusters.items():
        row = _cluster_row(galaxy, clusters_data, cluster)
        cluster_id = existing_ids.get(cluster_uuid)
        if cluster_id is None:
            new_clusters.append(row)
        else:
            updated_clusters.append({"id": cluster_id, **row})

    cluster_ids = {}
    if updated_clusters:
        db.execute(update(Cluster), updated_clusters)
        db.execute(
            delete(Element)
            .where(Element.galaxy_cluster_id.in_([c["id"] for c in updated_clusters]))
            .execution_options(synchronize_session=False)
        )
        cluster_ids.update({c["uuid"]: c["id"] for c in updated_clusters})

    if new_clusters:
        inserted = db.execute(
            pg_insert(Cluster)
            .on_conflict_do_nothing(index_elements=[Cluster.uuid])
            .returning(Cluster.uuid, Cluster.id),
            new_clusters,
        ).all()
        cluster_ids.update(
            {str(cluster_uuid): cluster_id for cluster_uuid, cluster_id in inserted}
        )
        if len(inserted) < len(new_clusters):
            logger.debug(
                f"Galaxy {galaxy.name}: skipped {len(new_clusters) - len(inserted)} clusters already imported by another galaxy"
            )

    elements = [
        element
        for cluster_uuid, cluster_id in cluster_ids.items()
        for element in _element_rows(cluster_id, raw_clusters[cluster_uuid])
    ]
    if elements:
        db.execute(insert(Element), elements)

    logger.debug(
        f"Galaxy {galaxy.name}: inserted {len(cluster_ids) - len(updated_clusters)} clusters, "
        f"updated {len(updated_clusters)} clusters, inserted {len(elements)} elements"
    )


def update_galaxies(
    db: Session,
    user: users_schemas.User,
    galaxies_dir: str = GALAXIES_DIR,
    clusters_dir: str = GALAXY_CLUSTERS_DIR,
) -> list[galaxies_models.Galaxy]:
    galaxies = []

    db_galaxies = {
        str(galaxy.uuid): galaxy
        for galaxy in db.scalars(
            select(galaxies_models.Galaxy).options(
                noload(galaxies_models.Galaxy.clusters)
            )
        ).all()
    }
    clusters_versions = dict(
        db.execute(
            select(
                galaxies_models.GalaxyCluster.galaxy_id,
                func.max(galaxies_models.GalaxyCluster.version),
            ).group_by(galaxies_models.GalaxyCluster.galaxy_id)
        ).all()
    )

    # sorted so clusters shipped in more than one galaxy always end up in the
    # same one
    for galaxy_file in sorted(os.listdir(galaxies_dir)):
        if not galaxy_file.endswith(".json"):
            continue

        with open(os.path.join(galaxies_dir, galaxy_file)) as f:
            galaxy_data = json.load(f)

        clusters_file = os.path.join(clusters_dir, galaxy_file)
        if not os.path.exists(clusters_file):
            logger.warning(f"Galaxy {galaxy_data['name']} has no clusters file")
            clusters_data = {}
        else:
            with open(clusters_file) as f:
                clusters_data = json.load(f)

        # cluster changes bump the clusters file version, not the galaxy one
        galaxy = db_galaxies.get(str(galaxy_data["uuid"]))
        if (
            galaxy is not None
            and galaxy.version == galaxy_data["version"]
            and clusters_versions.get(galaxy.id) == clusters_data.get("version")
        ):
            logger.debug(
                f"Galaxy {galaxy_data['name']} version {galaxy_data['version']} already exists. Skipping."
            )
            continue

        # create/update the galaxy, its clusters and elements in one transaction
        try:
            if galaxy is None:
                galaxy = galaxies_models.Galaxy(
                    uuid=galaxy_data["uuid"],
                    org_id=user.org_id,
                    orgc_id=user.org_id,
                    created=datetime.now(),
                )
            for key, value in _galaxy_fields(galaxy_data).items():
                setattr(galaxy, key, value)
            galaxy.modified = datetime.now()
            db.add(galaxy)
            db.flush()

            import_galaxy_clusters(db, galaxy, clusters_data)

            db.commit()
            galaxies.append(galaxy)
            logger.debug(f"Imported galaxy {galaxy_data['name']}")

            # create the tags of the clusters added to an enabled galaxy
            if galaxy.enabled:
                enable_galaxy_tags(db, galaxy)
        except Exception as e:
            logger.error(f"Error importing galaxy {galaxy_data['name']}: {e}")
            db.rollback()

    return galaxies


def _galaxy_tag_names(galaxy: galaxies_models.Galaxy):
    return select(galaxies_models.GalaxyCluster.tag_name).where(
        galaxies_models.GalaxyCluster.galaxy_id == galaxy.id
    )


def enable_galaxy_tags(db: Session, galaxy: galaxies_models.Galaxy):
    # name -> hide_tag
    existing_tags = dict(
        db.execute(
            select(tags_models.Tag.name, tags_models.Tag.hide_tag).where(
                tags_models.Tag.name.in_(_galaxy_tag_names(galaxy))
            )
        ).all()
    )
    new_tags = [
        {
            "name": name,
            "colour": "#BBBBBB",
            "exportable": True,
            "hide_tag": False,
            "is_galaxy": True,
            "is_custom_galaxy": False,
            "local_only": False,
        }
        for name in set(db.scalars(_galaxy_tag_names(galaxy)).all())
        if name not in existing_tags
    ]

    if new_tags:
        db.execute(insert(tags_models.Tag), new_tags)

    # show again the tags hidden when the galaxy was disabled
    hidden_tags = [name for name, hide_tag in existing_tags.items() if hide_tag]
    if hidden_tags:
        db.execute(
            update(tags_models.Tag)
            .where(tags_models.Tag.name.in_(hidden_tags))
            .values(hide_tag=False)
            .execution_options(synchronize_session=False)
        )

    db.commit()


def disable_galaxy_tags(db: Session, galaxy: galaxies_models.Galaxy):
    # hide all tags from the galaxy
    db.execute(
        update(tags_models.Tag)
        .where(tags_models.Tag.name.in_(_galaxy_tag_names(galaxy)))
        .values(hide_tag=True)
        .execution_options(synchronize_session=False)
    )
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
    if "enabled" in galaxy_patch:
        if db_galaxy.enabled:
            enable_galaxy_tags(db, db_galaxy)
        else:
            disable_galaxy_tags(db, db_galaxy)

    db.add(db_galaxy)
    db.commit()
    db.refresh(db_galaxy)

    return db_galaxy
