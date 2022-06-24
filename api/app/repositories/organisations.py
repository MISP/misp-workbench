from typing import Union

from app.models import organisations as organisation_models
from app.schemas import organisations as organisations_schemas
from fastapi import HTTPException, status
from sqlalchemy.orm import Session


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


def create_organisation(
    db: Session, organisation: organisations_schemas.OrganisationCreate
) -> organisation_models.Organisation:
    # TODO: Organisation::beforeValidate() && Organisation::$validate
    db_organisation = organisation_models.Organisation(
        name=organisation.name,
        description=organisation.description,
        date_created=organisation.date_created,
        date_modified=organisation.date_modified,
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

    organisation_patch = organisation.dict(exclude_unset=True)
    for key, value in organisation_patch.items():
        setattr(db_organisation, key, value)

    db.add(db_organisation)
    db.commit()
    db.refresh(db_organisation)

    return db_organisation
