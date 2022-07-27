from app.models import attribute as attribute_models
from app.models import tag as tag_models
from app.schemas import tag as tag_schemas
from fastapi import HTTPException, status
from sqlalchemy.orm import Session


def get_tags(db: Session, skip: int = 0, limit: int = 100):
    return db.query(tag_models.Tag).offset(skip).limit(limit).all()


def get_tag_by_id(db: Session, tag_id: int):
    return db.query(tag_models.Tag).filter(tag_models.Tag.id == tag_id).first()


def create_tag(db: Session, tag: tag_schemas.TagCreate):
    # TODO: app/Model/Tag.php::beforeValidate() && app/Model/Tag.php::$validate
    db_tag = tag_models.Tag(
        name=tag.name,
        colour=tag.colour,
        exportable=tag.exportable,
        org_id=tag.org_id,
        user_id=tag.user_id,
        hide_tag=tag.hide_tag,
        numerical_value=tag.numerical_value,
        is_galaxy=tag.is_galaxy,
        is_custom_galaxy=tag.is_custom_galaxy,
        local_only=tag.local_only,
    )

    db.add(db_tag)
    db.commit()
    db.refresh(db_tag)

    return db_tag


def update_tag(
    db: Session,
    tag_id: int,
    tag: tag_schemas.TagUpdate,
) -> tag_models.Tag:
    # TODO: app/Model/Tag.php::beforeValidate() && app/Model/Tag.php::$validate
    db_tag = get_tag_by_id(db, tag_id=tag_id)

    if db_tag is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Tag not found"
        )

    tag_patch = tag.dict(exclude_unset=True)
    for key, value in tag_patch.items():
        setattr(db_tag, key, value)

    db.add(db_tag)
    db.commit()
    db.refresh(db_tag)

    return db_tag


def delete_tag(db: Session, tag_id: int) -> None:
    db_tag = get_tag_by_id(db, tag_id=tag_id)

    if db_tag is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Tag not found"
        )

    db.delete(db_tag)
    db.commit()


def tag_attribute(
    db: Session,
    attribute: attribute_models.Attribute,
    tag: tag_models.Tag,
):
    db_attribute_tag = tag_models.AttributeTag(
        event_id=attribute.event_id,
        attribute_id=attribute.id,
        tag_id=tag.id,
    )

    db.add(db_attribute_tag)
    db.commit()
    db.refresh(db_attribute_tag)

    return db_attribute_tag
