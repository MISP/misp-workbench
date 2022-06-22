import logging

from app.models import sharing_groups as sharing_groups_models
from app.schemas import sharing_groups as sharing_groups_schemas
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
