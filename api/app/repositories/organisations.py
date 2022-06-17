from sqlalchemy.orm import Session

from ..models import organisations as organisation_models
from ..schemas import organisations as organisations_schemas


def get_organisations(db: Session, skip: int = 0, limit: int = 100):
    return db.query(organisation_models.Organisation).offset(skip).limit(limit).all()


def get_organisation_by_id(db: Session, organisation_id: int):
    return (
        db.query(organisation_models.Organisation)
        .filter(organisation_models.Organisation.id == organisation_id)
        .first()
    )


def create_organisation(
    db: Session, organisation: organisations_schemas.OrganisationCreate
):
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
