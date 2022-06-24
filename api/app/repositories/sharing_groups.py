import logging

from app.models import sharing_groups as sharing_groups_models
from app.schemas import sharing_groups as sharing_groups_schemas
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


def get_sharing_groups(db: Session, skip: int = 0, limit: int = 100):
    return db.query(sharing_groups_models.SharingGroup).offset(skip).limit(limit).all()


def get_sharing_group_by_id(db: Session, sharing_group_id: int):
    return (
        db.query(sharing_groups_models.SharingGroup)
        .filter(sharing_groups_models.SharingGroup.id == sharing_group_id)
        .first()
    )


def create_sharing_group(
    db: Session, sharing_group: sharing_groups_schemas.SharingGroupCreate
):
    db_sharing_group = sharing_groups_models.SharingGroup(
        name=sharing_group.name,
        releasability=sharing_group.releasability,
        description=sharing_group.description,
        uuid=sharing_group.uuid,
        organisation_uuid=sharing_group.organisation_uuid,
        org_id=sharing_group.org_id,
        sync_user_id=sharing_group.sync_user_id,
        active=sharing_group.active,
        created=sharing_group.created,
        modified=sharing_group.modified,
        local=sharing_group.local,
        roaming=sharing_group.roaming,
    )

    db.add(db_sharing_group)
    db.commit()
    db.refresh(db_sharing_group)

    return db_sharing_group


def add_server_sharing_group(
    db: Session, sharing_group_server: sharing_groups_schemas.SharingGroupServerCreate
):
    db_sharing_group_server = sharing_groups_models.SharingGroupServer(
        sharing_group_id=sharing_group_server.sharing_group_id,
        server_id=sharing_group_server.server_id,
        all_orgs=sharing_group_server.all_orgs,
    )

    db.add(db_sharing_group_server)
    db.commit()
    db.refresh(db_sharing_group_server)

    return db_sharing_group_server


def add_organisaiton_to_sharing_group(
    db: Session,
    sharing_group_organisation: sharing_groups_schemas.SharingGroupOrganisationCreate,
):
    db_sharing_group_organisation = sharing_groups_models.SharingGroupOrganisation(
        sharing_group_id=sharing_group_organisation.sharing_group_id,
        org_id=sharing_group_organisation.org_id,
        extend=sharing_group_organisation.extend,
    )

    db.add(db_sharing_group_organisation)
    db.commit()
    db.refresh(db_sharing_group_organisation)

    return db_sharing_group_organisation


def update_sharing_group(
    db: Session,
    sharing_group_id: int,
    sharing_group: sharing_groups_schemas.SharingGroupUpdate,
) -> sharing_groups_models.SharingGroup:
    # TODO: SharingGroup::beforeValidate() && SharingGroup::$validate
    db_sharing_group = get_sharing_group_by_id(db, sharing_group_id=sharing_group_id)

    if db_sharing_group is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Sharing Group not found"
        )

    sharing_group_patch = sharing_group.dict(exclude_unset=True)
    for key, value in sharing_group_patch.items():
        setattr(db_sharing_group, key, value)

    db.add(db_sharing_group)
    db.commit()
    db.refresh(db_sharing_group)

    return db_sharing_group
