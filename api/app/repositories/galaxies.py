import json
import os
from datetime import datetime

from app.models import galaxy as galaxies_models
from app.schemas import galaxy as galaxies_schemas
from app.schemas import user as users_schemas
from fastapi import HTTPException, Query, status
from fastapi_pagination.ext.sqlalchemy import paginate
from sqlalchemy.orm import Session


def get_galaxies(db: Session, filter: str = Query(None)) -> galaxies_models.Galaxy:
    query = db.query(galaxies_models.Galaxy)

    if filter:
        query = query.filter(galaxies_models.Galaxy.namespace.ilike(f"%{filter}%"))

    query = query.order_by(galaxies_models.Galaxy.namespace)

    return paginate(
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

    for root, __, files in os.walk(galaxies_dir):
        for galaxy_file in files:
            if not galaxy_file.endswith(".json"):
                continue

            with open(os.path.join(root, galaxy_file)) as f:
                galaxy_data = json.load(f)
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
                db.add(galaxy)
                db.commit()
                db.refresh(galaxy)

                galaxies.append(galaxy)

        # db.add(db_entry)
        # db.commit()
        # db.refresh(db_entry)

    return galaxies


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

    db.add(db_galaxy)
    db.commit()
    db.refresh(db_galaxy)

    return db_galaxy
