from uuid import UUID

from app.models import tag as tag_models
from app.models import user as user_models
from app.schemas import tag as tag_schemas
from app.services.opensearch import get_opensearch_client
from fastapi import HTTPException, Query, status
from fastapi_pagination.ext.sqlalchemy import paginate
from opensearchpy.exceptions import NotFoundError
from pymisp import MISPTag
from sqlalchemy import func
from sqlalchemy.orm import Session
from sqlalchemy.sql import select


def get_tags(db: Session, hidden: bool = Query(None), filter: str = Query(None)):
    query = select(tag_models.Tag)

    if hidden is not None:
        query = query.where(tag_models.Tag.hide_tag == hidden)

    if filter:
        query = query.where(tag_models.Tag.name.ilike(f"%{filter}%"))

    query = query.order_by(tag_models.Tag.name)

    return paginate(db, query)


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


def _tag_dict(tag: tag_models.Tag) -> dict:
    return {
        "id": tag.id,
        "name": tag.name,
        "colour": tag.colour,
        "exportable": tag.exportable,
        "hide_tag": tag.hide_tag,
        "numerical_value": tag.numerical_value,
        "is_galaxy": tag.is_galaxy,
        "is_custom_galaxy": tag.is_custom_galaxy,
        "local_only": tag.local_only,
    }


def tag_attribute(
    db: Session,
    attribute,
    tag: tag_models.Tag,
):
    client = get_opensearch_client()
    attr_uuid = str(getattr(attribute, "uuid", None))

    try:
        doc = client.get(index="misp-attributes", id=attr_uuid)
    except NotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attribute not found")

    current_tags = doc["_source"].get("tags", [])
    if any(t.get("name") == tag.name for t in current_tags):
        return current_tags

    current_tags.append(_tag_dict(tag))
    client.update(
        index="misp-attributes",
        id=attr_uuid,
        body={"doc": {"tags": current_tags}},
        refresh=True,
    )
    return current_tags


def untag_attribute(
    db: Session,
    attribute,
    tag: tag_models.Tag,
):
    client = get_opensearch_client()
    attr_uuid = str(getattr(attribute, "uuid", None))

    try:
        doc = client.get(index="misp-attributes", id=attr_uuid)
    except NotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="AttributeTag not found")

    current_tags = doc["_source"].get("tags", [])
    new_tags = [t for t in current_tags if t.get("name") != tag.name]
    if len(new_tags) == len(current_tags):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="AttributeTag not found")

    client.update(
        index="misp-attributes",
        id=attr_uuid,
        body={"doc": {"tags": new_tags}},
        refresh=True,
    )


def tag_event(
    db: Session,
    event,
    tag: tag_models.Tag,
):
    client = get_opensearch_client()
    event_uuid = str(getattr(event, "uuid", None))

    try:
        doc = client.get(index="misp-events", id=event_uuid)
    except NotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

    current_tags = doc["_source"].get("tags", [])
    if any(t.get("name") == tag.name for t in current_tags):
        return current_tags

    current_tags.append(_tag_dict(tag))
    client.update(
        index="misp-events",
        id=event_uuid,
        body={"doc": {"tags": current_tags}},
        refresh=True,
    )
    return current_tags


def untag_event(
    db: Session,
    event,
    tag: tag_models.Tag,
):
    client = get_opensearch_client()
    event_uuid = str(getattr(event, "uuid", None))

    try:
        doc = client.get(index="misp-events", id=event_uuid)
    except NotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="EventTag not found")

    current_tags = doc["_source"].get("tags", [])
    new_tags = [t for t in current_tags if t.get("name") != tag.name]
    if len(new_tags) == len(current_tags):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="EventTag not found")

    client.update(
        index="misp-events",
        id=event_uuid,
        body={"doc": {"tags": new_tags}},
        refresh=True,
    )


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
