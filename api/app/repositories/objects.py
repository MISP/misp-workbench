import logging
import math
import time
from typing import Optional
from uuid import UUID, uuid4

from app.models import feed as feed_models
from app.models import user as user_models
from app.repositories import attributes as attributes_repository
from app.repositories import object_references as object_references_repository
from app.repositories import events as events_repository
from app.schemas import event as event_schemas
from app.schemas import object as object_schemas
from app.schemas import attribute as attribute_schemas
from app.schemas import object_reference as object_reference_schemas
from app.schemas import user as user_schemas
from app.worker import tasks
from app.services.opensearch import get_opensearch_client
from fastapi import HTTPException, status
from fastapi_pagination import Page, Params
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

    try:
        response = client.search(index="misp-objects", body=query_body)
    except NotFoundError:
        return Page(items=[], total=0, page=params.page, size=params.size, pages=0)

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
    object_uuid: UUID,
) -> Optional[object_schemas.Object]:
    client = get_opensearch_client()

    try:
        doc = client.get(index="misp-objects", id=str(object_uuid))
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


def get_object_by_uuid(db: Session, object_uuid: UUID):
    return get_object_from_opensearch(object_uuid)


def get_objects(
    db: Session,
    event_uuid=None,
    deleted: bool = False,
    template_uuid: list = None,
) -> Page[object_schemas.Object]:
    params = Params(page=1, size=100)
    return get_objects_from_opensearch(
        params,
        event_uuid=str(event_uuid) if event_uuid else None,
        deleted=deleted,
        template_uuid=template_uuid,
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
) -> object_schemas.Object:
    from datetime import datetime as _datetime

    client = get_opensearch_client()
    object_uuid = str(pulled_object.uuid)

    dist = pulled_object.distribution
    dist_val = event_schemas.DistributionLevel(dist).value if dist is not None else 5
    ts_raw = pulled_object.timestamp
    ts = int(ts_raw.timestamp()) if hasattr(ts_raw, "timestamp") else int(ts_raw or 0)

    obj_doc = {
        "uuid": object_uuid,
        "event_uuid": event_uuid,
        "name": pulled_object.name,
        "meta_category": pulled_object["meta-category"],
        "description": pulled_object.description,
        "template_uuid": str(pulled_object.template_uuid) if pulled_object.template_uuid else None,
        "template_version": pulled_object.template_version,
        "timestamp": ts,
        "distribution": dist_val,
        "sharing_group_id": None,
        "comment": pulled_object.comment or "",
        "deleted": pulled_object.deleted or False,
        "first_seen": (
            int(pulled_object.first_seen.timestamp())
            if hasattr(pulled_object, "first_seen") and pulled_object.first_seen
            else None
        ),
        "last_seen": (
            int(pulled_object.last_seen.timestamp())
            if hasattr(pulled_object, "last_seen") and pulled_object.last_seen
            else None
        ),
        "object_references": [],
        "@timestamp": _datetime.fromtimestamp(ts).isoformat(),
    }

    client.index(index="misp-objects", id=object_uuid, body=obj_doc, refresh=True)

    for pulled_attribute in pulled_object.attributes:
        local_attribute = attributes_repository.create_attribute_from_pulled_attribute(
            db, pulled_attribute, event_uuid, user
        )
        if local_attribute:
            client.update(
                index="misp-attributes",
                id=str(local_attribute.uuid),
                body={"doc": {"object_uuid": object_uuid}},
                refresh=True,
            )

    for pulled_object_reference in pulled_object.ObjectReference:
        object_references_repository.create_object_reference_from_pulled_object_reference(
            db, pulled_object_reference, event_uuid
        )

    tasks.handle_created_object(object_uuid, event_uuid)

    return get_object_from_opensearch(UUID(object_uuid))


def update_object_from_pulled_object(
    db: Session,
    local_object: object_schemas.Object,
    pulled_object: MISPObject,
    event_uuid: str,
    user: user_models.User,
):
    ts_raw = pulled_object.timestamp
    pulled_ts = ts_raw.timestamp() if hasattr(ts_raw, "timestamp") else float(ts_raw or 0)

    if local_object.timestamp < pulled_ts:
        client = get_opensearch_client()
        local_attr_uuids = {str(a.uuid) for a in local_object.attributes}
        pulled_attr_uuids = {str(a.uuid) for a in pulled_object.attributes}

        for pulled_attr in pulled_object.attributes:
            local_attribute = attributes_repository.get_attribute_by_uuid(db, pulled_attr.uuid)
            if local_attribute is None:
                new_attr = attributes_repository.create_attribute_from_pulled_attribute(
                    db, pulled_attr, event_uuid, user
                )
                if new_attr:
                    client.update(
                        index="misp-attributes",
                        id=str(new_attr.uuid),
                        body={"doc": {"object_uuid": str(local_object.uuid)}},
                        refresh=True,
                    )
            else:
                attributes_repository.update_attribute_from_pulled_attribute(
                    db, local_attribute, pulled_attr, user
                )

        for uuid_to_delete in local_attr_uuids - pulled_attr_uuids:
            attributes_repository.delete_attribute(db, uuid_to_delete)

        object_patch = object_schemas.ObjectUpdate(
            name=pulled_object.name,
            meta_category=pulled_object["meta-category"],
            description=pulled_object.description,
            template_uuid=pulled_object.template_uuid,
            template_version=pulled_object.template_version,
            timestamp=int(pulled_ts),
            distribution=event_schemas.DistributionLevel(pulled_object.distribution),
            sharing_group_id=None,
            comment=pulled_object.comment,
            deleted=pulled_object.deleted,
            first_seen=(
                int(pulled_object.first_seen.timestamp())
                if hasattr(pulled_object, "first_seen") and pulled_object.first_seen
                else local_object.first_seen
            ),
            last_seen=(
                int(pulled_object.last_seen.timestamp())
                if hasattr(pulled_object, "last_seen") and pulled_object.last_seen
                else local_object.last_seen
            ),
        )

        for pulled_ref in pulled_object.ObjectReference:
            local_ref = object_references_repository.get_object_reference_by_uuid(
                db, pulled_ref.uuid
            )
            if local_ref is None:
                object_references_repository.create_object_reference_from_pulled_object_reference(
                    db, pulled_ref, event_uuid
                )
            elif local_ref.timestamp < int(pulled_ts):
                object_references_repository.update_object_reference_from_pulled_object_reference(
                    db, local_ref, pulled_ref, event_uuid
                )

        update_object(db, local_object.uuid, object_patch)


def update_object(
    db: Session, object_uuid: UUID, object: object_schemas.ObjectUpdate
) -> object_schemas.Object:
    client = get_opensearch_client()
    os_obj = get_object_from_opensearch(object_uuid)
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


def delete_object(db: Session, object_uuid: UUID) -> None:
    client = get_opensearch_client()
    os_obj = get_object_from_opensearch(object_uuid)
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
    client = get_opensearch_client()
    resp = client.search(
        index="misp-objects",
        body={
            "query": {"term": {"event_uuid.keyword": str(local_event.uuid)}},
            "size": 10000,
        },
    )
    local_event_dict = {
        h["_source"]["uuid"]: h["_source"].get("timestamp", 0)
        for h in resp["hits"]["hits"]
    }

    new_objects = [obj for obj in event.objects if str(obj.uuid) not in local_event_dict]
    updated_objects = [
        obj
        for obj in event.objects
        if str(obj.uuid) in local_event_dict
        and obj.timestamp.timestamp() > local_event_dict[str(obj.uuid)]
    ]

    create_objects_from_fetched_event(db, local_event, new_objects, feed, user)

    for updated_object in updated_objects:
        local_obj = get_object_from_opensearch(updated_object.uuid)
        if local_obj is not None:
            update_object_from_pulled_object(
                db, local_obj, updated_object, str(local_event.uuid), user
            )

        for reference in updated_object.references:
            referenced_type = None
            referenced = get_object_from_opensearch(reference.referenced_uuid)
            if referenced is None:
                os_attr = attributes_repository.get_attribute_from_opensearch(
                    reference.referenced_uuid
                )
                if os_attr is not None:
                    referenced = os_attr
                    referenced_type = object_reference_schemas.ReferencedType.ATTRIBUTE
            if referenced is None:
                logger.error(
                    f"Referenced entity not found, skipping object reference uuid: {reference.uuid}"
                )
                continue
            if referenced_type is None:
                referenced_type = object_reference_schemas.ReferencedType.OBJECT

            object_references_repository.create_object_reference(
                db,
                object_reference_schemas.ObjectReferenceCreate(
                    uuid=reference.uuid,
                    event_uuid=UUID(str(local_event.uuid)),
                    source_uuid=getattr(reference, "object_uuid", None),
                    referenced_uuid=reference.referenced_uuid,
                    referenced_id=None,
                    relationship_type=reference.relationship_type,
                    timestamp=int(reference.timestamp) if reference.timestamp else 0,
                    referenced_type=referenced_type,
                    comment=reference.comment or "",
                    deleted=referenced.deleted,
                ),
            )

    return local_event
