from app.models import attribute as attribute_models
from app.models import event as event_models
from app.models import tag as tag_models
from app.models import user as user_models
from app.schemas import tag as tag_schemas
from fastapi import HTTPException, status
from pymisp import MISPTag
from sqlalchemy import func
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

    tag_patch = tag.model_dump(exclude_unset=True)
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

    db_attribute_tag = (
        db.query(tag_models.AttributeTag)
        .filter(
            tag_models.AttributeTag.attribute_id == attribute.id,
            tag_models.AttributeTag.tag_id == tag.id,
        )
        .first()
    )

    if db_attribute_tag is not None:
        return db_attribute_tag

    db_attribute_tag = tag_models.AttributeTag(
        event_id=attribute.event_id,
        attribute_id=attribute.id,
        tag_id=tag.id,
    )

    db.add(db_attribute_tag)
    db.commit()
    db.refresh(db_attribute_tag)

    return db_attribute_tag


def untag_attribute(
    db: Session,
    attribute: attribute_models.Attribute,
    tag: tag_models.Tag,
):
    db_attribute_tag = (
        db.query(tag_models.AttributeTag)
        .filter(
            tag_models.AttributeTag.attribute_id == attribute.id,
            tag_models.AttributeTag.tag_id == tag.id,
        )
        .first()
    )

    if db_attribute_tag is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="AttributeTag not found"
        )

    db.delete(db_attribute_tag)
    db.commit()


def tag_event(
    db: Session,
    event: event_models.Event,
    tag: tag_models.Tag,
):

    db_event_tag = (
        db.query(tag_models.EventTag)
        .filter(
            tag_models.EventTag.event_id == event.id,
            tag_models.EventTag.tag_id == tag.id,
        )
        .first()
    )

    if db_event_tag is not None:
        return db_event_tag

    db_event_tag = tag_models.EventTag(
        event_id=event.id,
        tag_id=tag.id,
    )

    db.add(db_event_tag)
    db.commit()
    db.refresh(db_event_tag)

    return db_event_tag


def untag_event(
    db: Session,
    event: event_models.Event,
    tag: tag_models.Tag,
):
    db_event_tag = (
        db.query(tag_models.EventTag)
        .filter(
            tag_models.EventTag.event_id == event.id,
            tag_models.EventTag.tag_id == tag.id,
        )
        .first()
    )

    if db_event_tag is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="EventTag not found"
        )

    db.delete(db_event_tag)
    db.commit()


def capture_tag(db: Session, tag: MISPTag, user: user_models.User) -> tag_models.Tag:
    # see: app/Model/Tag.php::captureTag

    if not user.role.perm_site_admin and (
        tag.org_id != user.org_id or tag.user_id != user.id
    ):
        return False

    db_tag = get_tag_by_name(db, tag_name=tag.name)

    # TODO: handle setting MISP.incoming_tags_disabled_by_default

    if db_tag is None and user.role.perm_tag_editor:
        db_tag = create_tag(
            db,
            tag=tag_schemas.TagCreate(
                name=tag.name,
                colour=tag.colour,
                exportable=tag.exportable,
                org_id=user.org_id,
                user_id=user.id,
                hide_tag=tag.hide_tag,
                # numerical_value=tag.numerical_value, # TODO: MISPTag has no numerical_value
                is_galaxy=tag.is_galaxy,
                is_custom_galaxy=tag.is_custom_galaxy,
                local_only=tag.local_only,
            ),
        )

    db.add(db_tag)
    db.commit()
    db.refresh(db_tag)

    return db_tag


def get_tag_by_name(db: Session, tag_name: str):
    return (
        db.query(tag_models.Tag)
        .filter(func.lower(tag_models.Tag.name) == func.lower(tag_name))
        .first()
    )
