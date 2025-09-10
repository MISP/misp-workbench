import logging
import uuid
from datetime import datetime
from typing import Union
from uuid import UUID

from app.models import organisation as organisation_models
from app.schemas import organisations as organisations_schemas
from app.schemas import user as user_schemas
from fastapi import HTTPException, status
from pymisp import MISPOrganisation
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


def get_organisations(
    db: Session, skip: int = 0, limit: int = 100
) -> list[organisation_models.Organisation]:
    return db.query(organisation_models.Organisation).offset(skip).limit(limit).all()


def get_organisation_by_id(
    db: Session, organisation_id: int
) -> Union[organisation_models.Organisation, None]:
    return (
        db.query(organisation_models.Organisation)
        .filter(organisation_models.Organisation.id == organisation_id)
        .first()
    )


def get_organisation_by_uuid(
    db: Session, organisation_uuid: uuid.UUID
) -> Union[organisation_models.Organisation, None]:
    return (
        db.query(organisation_models.Organisation)
        .filter(organisation_models.Organisation.uuid == organisation_uuid)
        .first()
    )


def get_organisation_by_name(
    db: Session, organisation_name: str
) -> Union[organisation_models.Organisation, None]:
    return (
        db.query(organisation_models.Organisation)
        .filter(organisation_models.Organisation.name == organisation_name)
        .first()
    )


def create_organisation(
    db: Session, organisation: organisations_schemas.OrganisationCreate
) -> organisation_models.Organisation:
    # TODO: Organisation::beforeValidate() && Organisation::$validate
    db_organisation = organisation_models.Organisation(
        name=organisation.name,
        description=organisation.description,
        date_created=organisation.date_created or datetime.now(),
        date_modified=organisation.date_modified or datetime.now(),
        type=organisation.type,
        nationality=organisation.nationality,
        sector=organisation.sector,
        created_by=organisation.created_by,
        uuid=organisation.uuid,
        contacts=organisation.contacts,
        local=organisation.local,
        restricted_to_domain=organisation.restricted_to_domain,
        landing_page=organisation.landing_page,
    )

    db.add(db_organisation)
    db.commit()
    db.refresh(db_organisation)

    return db_organisation


def update_organisation(
    db: Session,
    organisation_id: int,
    organisation: organisations_schemas.OrganisationUpdate,
) -> organisation_models.Organisation:
    # TODO: Organisation::beforeValidate() && Organisation::$validate
    db_organisation = get_organisation_by_id(db, organisation_id=organisation_id)

    if db_organisation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Organisation not found"
        )

    organisation_patch = organisation.model_dump(exclude_unset=True)
    for key, value in organisation_patch.items():
        setattr(db_organisation, key, value)

    db.add(db_organisation)
    db.commit()
    db.refresh(db_organisation)

    return db_organisation


def delete_organisation(db: Session, organisation_id: Union[int, UUID]) -> None:

    if isinstance(organisation_id, int):
        db_organisation = get_organisation_by_id(db, organisation_id=organisation_id)
    else:
        db_organisation = get_organisation_by_uuid(
            db, organisation_uuid=organisation_id
        )

    if db_organisation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Organisation not found"
        )

    db.delete(db_organisation)
    db.commit()


def capture_sharing_group_organisation(
    db: Session, sharing_group_organisation: MISPOrganisation, user_id: int
) -> organisation_models.Organisation:
    # TODO: app/Model/Organisation.php::captureOrg

    db_organisation = get_organisation_by_uuid(
        db, organisation_uuid=sharing_group_organisation.Organisation.uuid
    )

    if db_organisation is None:
        db_organisation = create_organisation(
            db=db,
            organisation=organisations_schemas.OrganisationCreate(
                name=sharing_group_organisation.Organisation.name,
                uuid=sharing_group_organisation.Organisation.uuid,
                local=False,
                created_by=user_id,
            ),
        )
    else:
        db_organisation = update_organisation(
            db,
            db_organisation.id,
            organisations_schemas.OrganisationUpdate(
                name=sharing_group_organisation.Organisation.name,
            ),
        )

    return db_organisation


def get_or_create_organisation_from_feed(
    db: Session, Orgc: MISPOrganisation, user: user_schemas.User
):
    orgc = get_organisation_by_uuid(
        db,
        organisation_uuid=Orgc["uuid"],
    )

    if orgc is None:
        logger.info(f"Creating Organisation {Orgc['name']} ({Orgc['uuid']})")
        orgc = organisation_models.Organisation(
            uuid=Orgc["uuid"],
            name=Orgc["name"],
            date_created=datetime.now(),
            date_modified=datetime.now(),
            created_by=user.id,
            local=False,
        )
        db.add(orgc)
        db.commit()
        db.flush()
        db.refresh(orgc)

    return orgc
