import logging
import math
import time
from typing import Optional, Union
from uuid import UUID, uuid4

from app.models import attribute as attribute_models
from app.models import feed as feed_models
from app.models import object as object_models
from app.models import user as user_models
from app.models import object_reference as object_reference_models
from app.repositories import attributes as attributes_repository
from app.repositories import object_references as object_references_repository
from app.repositories import events as events_repository
from app.schemas import event as event_schemas
from app.schemas import object as object_schemas
from app.schemas import attribute as attribute_schemas
from app.schemas import user as user_schemas
from app.worker import tasks
from app.services.opensearch import get_opensearch_client
from fastapi import HTTPException, status
from fastapi_pagination import Page, Params
from fastapi_pagination.ext.sqlalchemy import paginate
from pymisp import MISPObject
from sqlalchemy.orm import Session
from collections import defaultdict
from opensearchpy.exceptions import NotFoundError

logger = logging.getLogger(__name__)


def enrich_object_attributes_with_correlations(
    attributes: list[attribute_schemas.Attribute],
) -> list[attribute_schemas.Attribute]:
    OpenSearchClient = get_opensearch_client()

    uuids = [attr.uuid for attr in attributes]
    if not uuids:
        return attributes

    query = {
        "query": {"terms": {"source_attribute_uuid.keyword": uuids}},
        "size": 10000,  # results should be less than MAX_CORRELATIONS_PER_DOC * page_size
    }

    try:
        response = OpenSearchClient.search(
            index="misp-attribute-correlations", body=query
        )
        hits = response["hits"]["hits"]
    except NotFoundError:
        for attr in attributes:
            attr.correlations = []
        return attributes

    correlation_map = defaultdict(list)
    for hit in hits:
        source_attribute_uuid = hit["_source"]["source_attribute_uuid"]
        correlation_map[source_attribute_uuid].append(hit)

    for attr in attributes:
        attr.correlations = correlation_map.get(str(attr.uuid), [])

    return attributes


def get_objects(
    db: Session,
    event_uuid: str = None,
    deleted: bool = False,
    template_uuid: list[UUID] = None,
) -> list[object_models.Object]:
    query = db.query(object_models.Object)

    if event_uuid is not None:
        os_client = get_opensearch_client()
        _resp = os_client.search(
            index="misp-objects",
            body={
                "query": {"term": {"event_uuid.keyword": str(event_uuid)}},
                "size": 10000,
                "_source": ["uuid"],
            },
        )
        object_uuids = [h["_source"]["uuid"] for h in _resp["hits"]["hits"]]
        if not object_uuids:
            from fastapi_pagination import Page as _Page
            return _Page(items=[], total=0, page=1, size=50, pages=0)
        query = query.filter(object_models.Object.uuid.in_(object_uuids))

    if template_uuid is not None:
        query = query.filter(object_models.Object.template_uuid.in_(template_uuid))

    query = query.filter(object_models.Object.deleted.is_(bool(deleted)))

    objects_page = paginate(db, query)

    for obj in objects_page.items:
        obj.attributes = enrich_object_attributes_with_correlations(obj.attributes)

    return objects_page


def get_objects_from_opensearch(
    params: Params,
    event_uuid: str = None,
    deleted: bool = False,
    template_uuid: list = None,
) -> Page[object_schemas.Object]:
    client = get_opensearch_client()

    must_clauses = [{"term": {"deleted": bool(deleted)}}]
    if event_uuid is not None:
        must_clauses.append({"term": {"event_uuid.keyword": event_uuid}})
    if template_uuid is not None:
        must_clauses.append(
            {"terms": {"template_uuid.keyword": [str(u) for u in template_uuid]}}
        )

    query_body = {
        "query": {"bool": {"must": must_clauses}},
        "from": (params.page - 1) * params.size,
        "size": params.size,
        "sort": [{"timestamp": {"order": "desc"}}],
    }

    response = client.search(index="misp-objects", body=query_body)
    total = response["hits"]["total"]["value"]
    hits = response["hits"]["hits"]

    if not hits:
        return Page(items=[], total=total, page=params.page, size=params.size, pages=0)

    # Batch-fetch attributes for all returned objects
    object_uuids = [str(hit["_source"]["uuid"]) for hit in hits]
    attr_response = client.search(
        index="misp-attributes",
        body={
            "query": {"terms": {"object_uuid": object_uuids}},
            "size": 10000,
        },
    )

    raw_by_uuid: dict = {}
    for attr_hit in attr_response["hits"]["hits"]:
        src = attr_hit["_source"]
        key = src.get("object_uuid")
        if key:
            raw_by_uuid.setdefault(key, []).append(src)

    # Build and correlate per-object attribute lists
    attrs_by_uuid: dict = {}
    for obj_uuid, raw_attrs in raw_by_uuid.items():
        built = [attribute_schemas.Attribute.model_validate(s) for s in raw_attrs]
        attrs_by_uuid[obj_uuid] = enrich_object_attributes_with_correlations(built)

    items = []
    for hit in hits:
        source = hit["_source"]
        obj_uuid = str(source.get("uuid", ""))
        source["attributes"] = attrs_by_uuid.get(obj_uuid, [])
        source.setdefault("object_references", [])
        items.append(object_schemas.Object.model_validate(source))

    pages = math.ceil(total / params.size) if params.size > 0 else 0
    return Page(items=items, total=total, page=params.page, size=params.size, pages=pages)


def get_object_from_opensearch(
    object_id: Union[int, UUID],
) -> Optional[object_schemas.Object]:
    client = get_opensearch_client()

    if isinstance(object_id, int):
        response = client.search(
            index="misp-objects",
            body={"query": {"term": {"id": object_id}}, "size": 1},
        )
        hits = response["hits"]["hits"]
        if not hits:
            return None
        source = hits[0]["_source"]
    else:
        try:
            doc = client.get(index="misp-objects", id=str(object_id))
            source = doc["_source"]
        except NotFoundError:
            return None

    obj_uuid = str(source.get("uuid", ""))
    attr_response = client.search(
        index="misp-attributes",
        body={"query": {"term": {"object_uuid": obj_uuid}}, "size": 10000},
    )

    attributes = []
    attributes = [
        attribute_schemas.Attribute.model_validate(h["_source"])
        for h in attr_response["hits"]["hits"]
    ]
    attributes = enrich_object_attributes_with_correlations(attributes)
    source["attributes"] = attributes
    source.setdefault("object_references", [])

    return object_schemas.Object.model_validate(source)


def get_object_by_id(db: Session, object_id: int):
    return (
        db.query(object_models.Object)
        .filter(object_models.Object.id == object_id)
        .first()
    )


def get_object_by_uuid(db: Session, object_uuid: UUID):
    return (
        db.query(object_models.Object)
        .filter(object_models.Object.uuid == object_uuid)
        .first()
    )


def create_object(
    db: Session, object: object_schemas.ObjectCreate
) -> object_schemas.Object:
    from datetime import datetime as _datetime

    client = get_opensearch_client()
    object_uuid = str(object.uuid or uuid4())

    event_uuid = str(object.event_uuid) if object.event_uuid else None

    dist = object.distribution
    dist_val = dist.value if hasattr(dist, "value") else (dist if dist is not None else 5)

    obj_doc = {
        "uuid": object_uuid,
        "event_uuid": event_uuid,
        "name": object.name,
        "meta_category": object.meta_category,
        "description": object.description,
        "template_uuid": object.template_uuid,
        "template_version": object.template_version,
        "timestamp": object.timestamp,
        "distribution": dist_val,
        "sharing_group_id": object.sharing_group_id,
        "comment": object.comment or "",
        "deleted": object.deleted or False,
        "first_seen": object.first_seen,
        "last_seen": object.last_seen,
        "object_references": [],
        "@timestamp": _datetime.fromtimestamp(object.timestamp).isoformat(),
    }

    client.index(index="misp-objects", id=object_uuid, body=obj_doc, refresh=True)

    built_attrs = []
    for attr in (object.attributes or []):
        attr.object_id = None
        attr.event_uuid = event_uuid
        attr_schema = attributes_repository.create_attribute(db, attr)
        client.update(
            index="misp-attributes",
            id=str(attr_schema.uuid),
            body={"doc": {"object_uuid": object_uuid}},
            refresh=True,
        )
        built_attrs.append(attr_schema)

    for object_reference in (object.object_references or []):
        object_reference.event_uuid = event_uuid
        object_references_repository.create_object_reference(db, object_reference)

    tasks.handle_created_object(object_uuid, event_uuid)

    obj_doc["attributes"] = built_attrs
    return object_schemas.Object.model_validate(obj_doc)


def create_object_from_pulled_object(
    db: Session, pulled_object: MISPObject, event_uuid: str, user: user_models.User
) -> object_models.Object:
    # TODO: process sharing group // captureSG
    # TODO: enforce warninglist

    db_object = object_models.Object(
        name=pulled_object.name,
        meta_category=pulled_object["meta-category"],
        description=pulled_object.description,
        template_uuid=pulled_object.template_uuid,
        template_version=pulled_object.template_version,
        uuid=pulled_object.uuid,
        timestamp=pulled_object.timestamp.timestamp(),
        distribution=event_schemas.DistributionLevel(pulled_object.distribution),
        sharing_group_id=None,
        comment=pulled_object.comment,
        deleted=pulled_object.deleted,
        first_seen=(
            pulled_object.first_seen.timestamp()
            if hasattr(pulled_object, "first_seen")
            else None
        ),
        last_seen=(
            pulled_object.last_seen.timestamp()
            if hasattr(pulled_object, "last_seen")
            else None
        ),
    )

    for pulled_attribute in pulled_object.attributes:
        local_object_attribute = (
            attributes_repository.create_attribute_from_pulled_attribute(
                db, pulled_attribute, event_uuid, user
            )
        )
        db_object.attributes.append(local_object_attribute)

    for pulled_object_reference in pulled_object.ObjectReference:
        local_object_reference = object_references_repository.create_object_reference_from_pulled_object_reference(
            db, pulled_object_reference, event_uuid
        )
        db_object.object_references.append(local_object_reference)

    db.add(db_object)

    return db_object


def update_object_from_pulled_object(
    db: Session,
    local_object: object_models.Object,
    pulled_object: MISPObject,
    event_uuid: str,
    user: user_models.User,
):

    if local_object.timestamp < pulled_object.timestamp.timestamp():
        # find object attributes to delete
        local_object_attribute_uuids = [
            attribute.uuid for attribute in local_object.attributes
        ]
        pulled_object_attribute_uuids = [
            attribute.uuid for attribute in pulled_object.attributes
        ]
        delete_attributes = [
            str(uuid)
            for uuid in local_object_attribute_uuids
            if uuid not in pulled_object_attribute_uuids
        ]

        for pulled_object_attribute in pulled_object.attributes:
            pulled_object_attribute.object_id = local_object.id
            local_attribute = attributes_repository.get_attribute_by_uuid(
                db, pulled_object_attribute.uuid
            )
            if local_attribute is None:
                local_attribute = (
                    attributes_repository.create_attribute_from_pulled_attribute(
                        db, pulled_object_attribute, event_uuid, user
                    )
                )
            else:
                pulled_object_attribute.id = local_attribute.id
                attributes_repository.update_attribute_from_pulled_attribute(
                    db, local_attribute, pulled_object_attribute, event_uuid, user
                )

        object_patch = object_schemas.ObjectUpdate(
            name=pulled_object.name,
            meta_category=pulled_object["meta-category"],
            description=pulled_object.description,
            template_uuid=pulled_object.template_uuid,
            template_version=pulled_object.template_version,
            timestamp=pulled_object.timestamp.timestamp(),
            distribution=event_schemas.DistributionLevel(pulled_object.distribution),
            sharing_group_id=None,
            comment=pulled_object.comment,
            deleted=pulled_object.deleted,
            first_seen=(
                pulled_object.first_seen.timestamp()
                if hasattr(pulled_object, "first_seen")
                else local_object.first_seen
            ),
            last_seen=(
                pulled_object.last_seen.timestamp()
                if hasattr(pulled_object, "last_seen")
                else local_object.last_seen
            ),
            delete_attributes=delete_attributes,
        )

        for pulled_object_reference in pulled_object.ObjectReference:
            local_object_reference = (
                object_references_repository.get_object_reference_by_uuid(
                    db, pulled_object_reference.uuid
                )
            )

            if local_object_reference is None:
                local_object_reference = object_references_repository.create_object_reference_from_pulled_object_reference(
                    db, pulled_object_reference, event_uuid
                )
                local_object.object_references.append(local_object_reference)
            else:
                if (
                    local_object_reference.timestamp
                    < pulled_object.timestamp.timestamp()
                ):
                    pulled_object_reference.id = local_object_reference.id
                    local_object_reference = object_references_repository.update_object_reference_from_pulled_object_reference(
                        db,
                        local_object_reference,
                        pulled_object_reference,
                        event_uuid,
                    )

        update_object(db, local_object.id, object_patch)


def update_object(
    db: Session, object_id: Union[int, UUID], object: object_schemas.ObjectUpdate
) -> object_schemas.Object:
    client = get_opensearch_client()
    os_obj = get_object_from_opensearch(object_id)
    if os_obj is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Object not found")

    patch = object.model_dump(
        exclude_unset=True,
        exclude={"attributes", "new_attributes", "update_attributes", "delete_attributes"},
    )
    for k, v in list(patch.items()):
        if hasattr(v, "value"):
            patch[k] = v.value

    if patch:
        client.update(index="misp-objects", id=str(os_obj.uuid), body={"doc": patch}, refresh=True)

    for attr in (object.new_attributes or []):
        attr.object_id = None
        attr.event_uuid = os_obj.event_uuid
        attr_schema = attributes_repository.create_attribute(db, attr)
        client.update(
            index="misp-attributes",
            id=str(attr_schema.uuid),
            body={"doc": {"object_uuid": str(os_obj.uuid)}},
            refresh=True,
        )

    for attr in (object.update_attributes or []):
        attributes_repository.update_attribute(db, attr.uuid, attr)

    for attr_id in (object.delete_attributes or []):
        attributes_repository.delete_attribute(db, attr_id)

    tasks.handle_updated_object(str(os_obj.uuid), str(os_obj.event_uuid) if os_obj.event_uuid else None)

    return get_object_from_opensearch(os_obj.uuid)


def delete_object(db: Session, object_id: Union[int, UUID]) -> None:
    client = get_opensearch_client()
    os_obj = get_object_from_opensearch(object_id)
    if os_obj is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Object not found")

    client.update(index="misp-objects", id=str(os_obj.uuid), body={"doc": {"deleted": True}}, refresh=True)

    for attr in os_obj.attributes:
        client.update(
            index="misp-attributes",
            id=str(attr.uuid),
            body={"doc": {"deleted": True}},
            refresh=True,
        )

    tasks.handle_deleted_object(str(os_obj.uuid), str(os_obj.event_uuid) if os_obj.event_uuid else None)


def create_objects_from_fetched_event(
    db: Session,
    local_event: event_schemas.Event,
    objects: list[MISPObject],
    feed: feed_models.Feed,
    user: user_schemas.User,
):

    for object in objects:
        create_object_from_pulled_object(db, object, str(local_event.uuid), user)


def update_objects_from_fetched_event(
    db: Session,
    local_event: event_schemas.Event,
    event: event_schemas.Event,
    feed: feed_models.Feed,
    user: user_schemas.User,
) -> event_schemas.Event:
    from app.services.opensearch import get_opensearch_client as _get_os_client
    _os = _get_os_client()
    _resp = _os.search(
        index="misp-objects",
        body={"query": {"term": {"event_uuid.keyword": str(local_event.uuid)}}, "size": 10000},
    )
    local_event_objects = [
        (h["_source"]["uuid"], h["_source"].get("timestamp", 0))
        for h in _resp["hits"]["hits"]
    ]
    local_event_dict = {str(uuid): timestamp for uuid, timestamp in local_event_objects}

    new_objects = [
        object for object in event.objects if object.uuid not in local_event_dict.keys()
    ]

    updated_objects = [
        object
        for object in event.objects
        if object.uuid in local_event_dict
        and object.timestamp.timestamp() > local_event_dict[object.uuid]
    ]

    # add new objects
    local_event = create_objects_from_fetched_event(
        db, local_event, new_objects, feed, user
    )

    # update existing attributes
    batch_size = 100  # TODO: set the batch size via configuration
    updated_uuids = [object.uuid for object in updated_objects]

    for batch_start in range(0, len(updated_uuids), batch_size):
        batch_uuids = updated_uuids[batch_start : batch_start + batch_size]

        db_objects = (
            db.query(object_models.Object)
            .filter(object_models.Object.uuid.in_(batch_uuids))
            .enable_eagerloads(False)
            .yield_per(batch_size)
        )

        updated_objects_dict = {object.uuid: object for object in updated_objects}

        for db_object in db_objects:
            updated_object = updated_objects_dict[str(db_object.uuid)]
            db_object.name = updated_object.name
            db_object.meta_category = updated_object["meta-category"]
            db_object.description = updated_object.description
            db_object.template_uuid = updated_object.template_uuid
            db_object.template_version = updated_object.template_version
            db_object.timestamp = (updated_object.timestamp.timestamp(),)
            db_object.comment = (updated_object.comment,)
            db_object.deleted = updated_object.deleted
            db_object.first_seen = (
                (
                    updated_object.first_seen.timestamp()
                    if hasattr(updated_object, "first_seen")
                    else None
                ),
            )
            db_object.last_seen = (
                (
                    updated_object.last_seen.timestamp()
                    if hasattr(updated_object, "last_seen")
                    else None
                ),
            )

            for attribute in updated_object.attributes:
                attribute.object_id = db_object.id

            # process attributes
            local_event = attributes_repository.update_attributes_from_fetched_event(
                db, local_event, updated_object.attributes, feed, user
            )

            # TODO: process galaxies
            # TODO: process attribute sightings
            # TODO: process analyst notes

        # process object references
        for updated_object in updated_objects:
            for reference in updated_object.references:
                referenced = (
                    db.query(object_models.Object)
                    .filter_by(uuid=reference.referenced_uuid)
                    .first()
                )
                if referenced is None:
                    referenced = (
                        db.query(attribute_models.Attribute)
                        .filter_by(uuid=reference.referenced_uuid)
                        .first()
                    )
                if referenced is None:
                    logger.error(
                        f"Referenced entity not found, skipping object reference uuid: {reference.uuid}"
                    )
                    break

                db_object_reference = object_reference_models.ObjectReference(
                    uuid=reference.uuid,
                    event_uuid=str(local_event.uuid),
                    object_id=db_object.id,
                    referenced_uuid=referenced.uuid,
                    referenced_id=referenced.id if referenced else None,
                    relationship_type=reference.relationship_type,
                    timestamp=int(reference.timestamp),
                    referenced_type=(
                        object_reference_models.ReferencedType.ATTRIBUTE
                        if referenced.__class__.__name__ == "Attribute"
                        else object_reference_models.ReferencedType.OBJECT
                    ),
                    comment=reference.comment,
                    deleted=referenced.deleted,
                )
                db.add(db_object_reference)

        db.commit()

    db.commit()

    # # TODO: process shadow_attributes

    # db.commit()

    return local_event
