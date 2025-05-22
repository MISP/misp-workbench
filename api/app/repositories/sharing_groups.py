import logging
import uuid
from datetime import datetime
from functools import lru_cache
from typing import Union

from app.models import sharing_groups as sharing_groups_models
from app.models import user as user_models
from app.repositories import organisations as organisations_repository
from app.schemas import server as server_schemas
from app.schemas import sharing_groups as sharing_groups_schemas
from app.settings import get_settings
from fastapi import HTTPException, status
from pymisp import MISPSharingGroup
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


def get_sharing_group_by_uuid(db: Session, sharing_group_uuid: uuid.UUID):
    return (
        db.query(sharing_groups_models.SharingGroup)
        .filter(sharing_groups_models.SharingGroup.uuid == sharing_group_uuid)
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


def add_organisation_to_sharing_group(
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
    # TODO: app/Model/SharingGroup.php::beforeValidate() && app/Model/SharingGroup.php::$validate
    db_sharing_group = get_sharing_group_by_id(db, sharing_group_id=sharing_group_id)

    if db_sharing_group is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Sharing Group not found"
        )

    sharing_group_patch = sharing_group.model_dump(exclude_unset=True)
    for key, value in sharing_group_patch.items():
        setattr(db_sharing_group, key, value)

    db.add(db_sharing_group)
    db.commit()
    db.refresh(db_sharing_group)

    return db_sharing_group


def delete_sharing_group(db: Session, sharing_group_id: int) -> None:
    db_sharing_group = get_sharing_group_by_id(db, sharing_group_id=sharing_group_id)

    if db_sharing_group is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Sharing Group not found"
        )

    db.delete(db_sharing_group)
    db.commit()


@lru_cache
def server_is_authorised(db: Session, sharing_group_id: int):
    # see: app/Model/SharingGroup.php::checkIfAuthorisedServer
    if (
        db.query(sharing_groups_models.SharingGroupServer)
        .filter(
            sharing_groups_models.SharingGroupServer.sharing_group_id
            == sharing_group_id
            and sharing_groups_models.SharingGroupServer.all_orgs is True
            and sharing_groups_models.SharingGroupServer.server_id == 0
        )
        .one_or_none()
        is not None
    ):  # TODO: check if this is correct
        return True

    return False


@lru_cache
def organisation_is_authorised(db: Session, sharing_group_id: int, org_id: int):
    # see: app/Model/SharingGroup.php::checkIfAuthorisedOrg
    if (
        db.query(sharing_groups_models.SharingGroupOrganisation)
        .filter(
            sharing_groups_models.SharingGroupOrganisation.sharing_group_id
            == sharing_group_id
            and sharing_groups_models.SharingGroupOrganisation.org_id == org_id
        )
        .one_or_none()
        is not None
    ):
        return True

    return False


@lru_cache
def is_authorised(
    db: Session, user: user_models.User, sharing_group_uuid: uuid.UUID
) -> bool:
    # see: app/Model/SharingGroup.php::checkIfAuthorised
    db_sharing_group = get_sharing_group_by_uuid(
        db, sharing_group_uuid=sharing_group_uuid
    )

    if user.role.perm_site_admin:
        return True

    if user.org_id == db_sharing_group.org_id:
        return True

    if server_is_authorised(db=db, user=user, sharing_group_id=db_sharing_group.id):
        return True

    if organisation_is_authorised(
        db=db, user=user, sharing_group_id=db_sharing_group.id, org_id=user.org_id
    ):
        return True

    return False


@lru_cache
def is_owner(db: Session, user: user_models.User, sharing_group_id: int) -> bool:
    # see: app/Model/SharingGroup.php::checkIfOwner
    pass


@lru_cache
def is_authorised_to_extend(
    db: Session, user: user_models.User, sharing_group_id: int
) -> bool:
    # see: app/Model/SharingGroup.php::checkIfAuthorisedExtend
    if user.role.perm_site_admin:
        return True

    if not user.role.perm_sharing_group:
        return False

    if is_owner(db=db, user=user, sharing_group_id=sharing_group_id):
        return True

    db_sharing_group = get_sharing_group_by_id(db, sharing_group_id=sharing_group_id)

    if db_sharing_group is None:
        return False

    if user.role.perm_sync and db_sharing_group.sync_user_id == user.id:
        return True

    return (
        db.query(sharing_groups_models.SharingGroup)
        .filter(
            sharing_groups_models.SharingGroup.id == sharing_group_id
            and sharing_groups_models.SharingGroup.org_id == user.org_id
            and sharing_groups_models.SharingGroup.extend is True
        )
        .one_or_none()
        is not None
    )


@lru_cache
def is_authorised_to_save(
    db: Session, user: user_models.User, sharing_group_uuid: uuid.UUID
) -> bool:
    # see: app/Model/SharingGroup.php::checkIfAuthorisedToSave

    settings = get_settings()
    if user.role.perm_site_admin:
        return True

    if not user.role.perm_sharing_group:
        return False

    db_sharing_group = get_sharing_group_by_uuid(
        db, sharing_group_uuid=sharing_group_uuid
    )

    if db_sharing_group is None:
        organisation_check = False
        server_check = False
        for sharing_group_org in db_sharing_group.sharing_group_organisations:
            if (
                db_sharing_group.sharing_group_organisations.uuid
                == user.organisation.uuid
            ):
                if user.role.perm_sync or sharing_group_org.extend:
                    organisation_check = True
                    break

        for sharing_group_server in db_sharing_group.sharing_group_servers:
            if (
                sharing_group_server.server.url == settings.MISP.baseurl
                or sharing_group_server.server.url == settings.MISP.external_baseurl
            ):
                server_check = True
                if user.role.perm_sync and sharing_group_server.all_orgs:
                    organisation_check = True

        if db_sharing_group.sharing_group_servers is None:
            server_check = True  # TODO: check this is correct

        if organisation_check and server_check:
            return True
    else:
        return is_authorised_to_extend(
            db=db, user=user, sharing_group_id=db_sharing_group.id
        )

    return False


def capture_sharing_group_new(
    db: Session,
    user: user_models.User,
    sharing_group: MISPSharingGroup,
    sync_local: bool,
) -> Union[int, bool]:
    # see: app/Model/SharingGroup.php::captureSGNew

    if (
        not is_authorised_to_save(
            db=db, user=user, sharing_group_uuid=sharing_group.uuid
        )
        and not user.role.perm_site_admin
    ):
        return False

    if sharing_group.name == "":
        return False

    now = datetime.now()
    new_sharing_group = create_sharing_group(
        db=db,
        sharing_group=sharing_groups_schemas.SharingGroupCreate(
            name=sharing_group.name,
            releasability=sharing_group.releasability,
            description=sharing_group.description,
            uuid=sharing_group.uuid,
            organisation_uuid=sharing_group.organisation_uuid
            or sharing_group.organisation.uuid,
            created=sharing_group.created or now,
            modified=sharing_group.modified or now,
            active=sharing_group.active or True,
            roaming=sharing_group.roaming or False,
            local=False,
            sync_user_id=user.id,
            org_id=user.org_id,  # TODO: check if __retrieveOrgIdFromCapturedSG is still relevant
        ),
    )

    return new_sharing_group.id


def capture_sharing_group_existing(
    db: Session,
    user: user_models.User,
    existing_sharing_group: sharing_groups_models.SharingGroup,
    sharing_group: sharing_groups_schemas.SharingGroup,
) -> Union[int, bool]:
    # see: app/Model/SharingGroup.php::captureSGExisting

    if (
        not is_authorised(db, user, existing_sharing_group.uuid)
        and not user.role.perm_sync
    ):
        return False

    # we have an up-to-date sharing group, so we can just return the id
    if sharing_group.modified <= existing_sharing_group.modified:
        return existing_sharing_group.id

    is_updatable_by_sync = user.role.perm_sync and not existing_sharing_group.local
    is_sharing_group_owner = (
        not user.role.perm_sync and existing_sharing_group.org_id == user.org_id
    )

    if is_updatable_by_sync or is_sharing_group_owner or user.role.perm_site_admin:
        update_sharing_group(
            db,
            existing_sharing_group.id,
            sharing_groups_schemas.SharingGroupUpdate(
                name=sharing_group.name,
                releasability=sharing_group.releasability,
                description=sharing_group.description,
                created=sharing_group.created,
                modified=sharing_group.modified,
                roaming=sharing_group.roaming,
            ),
        )
        return True
    else:
        existing_sharing_group.id

    return False


def capture_sharing_group_organisations(
    db: Session,
    user: user_models.User,
    sharing_group_id: int,
    sharing_group_organisations: list[dict],
) -> None:
    # see: app/Model/SharingGroup.php::captureSGOrgs
    for sharing_group_organisation in sharing_group_organisations:
        organisation = organisations_repository.capture_sharing_group_organisation(
            db, sharing_group_organisation, user.id
        )
        sharing_group_organisation.org_id = organisation.id
        add_organisation_to_sharing_group(
            db,
            sharing_groups_schemas.SharingGroupOrganisationCreate(
                sharing_group_id=sharing_group_id,
                org_id=organisation.id,
                extend=sharing_group_organisation.extend,
            ),
        )

    return sharing_group_organisations


def capture_sharing_group_servers(
    db: Session,
    user: user_models.User,
    sharing_group_id: int,
    sharing_group_organisations: list[dict],
) -> None:
    # see: app/Model/SharingGroup.php::captureSGServers

    pass


def capture_sharing_group(
    db: Session,
    sharing_group: MISPSharingGroup,
    user: user_models.User,
    server: server_schemas.Server,
) -> Union[int, bool]:
    # see app/Model/SharingGroup.php::captureSG()

    sync_local = False
    if hasattr(server, "local") and server.local:
        sync_local = True

    existing_sharing_group = get_sharing_group_by_uuid(db, sharing_group.uuid)
    if existing_sharing_group is None:
        # see app/Model/SharingGroup.php::captureSGNew()
        if not user.role.perm_sharing_group:
            return False
        sharing_group_id = capture_sharing_group_new(
            db, user, sharing_group, sync_local
        )
    else:
        # see: app/Model/SharingGroup.php::captureSGExisting()
        sharing_group_id = capture_sharing_group_existing(
            db, user, existing_sharing_group, sharing_group
        )

    if sharing_group_id is False:
        return False

    # capture sharing group organisations
    sharing_group.SharingGroupOrg = capture_sharing_group_organisations(
        db, user, sharing_group_id, sharing_group.sharing_group_organisations
    )

    # capture sharing group servers
    # capture_sharing_group_servers(db, sharing_group_id, sharing_group.sharing_group_servers)

    # app/Model/SharingGroup.php::captureCreatorOrg()

    return sharing_group_id
