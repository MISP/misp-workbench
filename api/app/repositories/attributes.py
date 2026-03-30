import math
import time
from datetime import datetime
from typing import Iterable, Optional
from uuid import UUID, uuid4
from app.models.event import DistributionLevel
from app.services.opensearch import get_opensearch_client
from app.models import tag as tag_models
from app.models import user as user_models
from app.schemas import tag as tag_schemas
from app.repositories import attachments as attachments_repository
from app.schemas import attribute as attribute_schemas
from app.schemas import event as event_schemas
from app.worker import tasks
from fastapi import HTTPException, status
from fastapi_pagination import Page, Params
from pymisp import MISPAttribute, MISPTag
from sqlalchemy.orm import Session
from collections import defaultdict
from opensearchpy.exceptions import NotFoundError


def enrich_attributes_page_with_correlations(
    attributes_page: Page[attribute_schemas.Attribute],
) -> Page[attribute_schemas.Attribute]:
    OpenSearchClient = get_opensearch_client()

    uuids = [attr.uuid for attr in attributes_page.items]
    if not uuids:
        return attributes_page

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
        for attr in attributes_page.items:
            attr.correlations = []
        return attributes_page

    correlation_map = defaultdict(list)
    for hit in hits:
        source_attribute_uuid = hit["_source"]["source_attribute_uuid"]
        correlation_map[source_attribute_uuid].append(hit)

    for attr in attributes_page.items:
        attr.correlations = correlation_map.get(str(attr.uuid), [])

    return attributes_page


def get_attributes_from_opensearch(
    params: Params,
    event_uuid: str = None,
    deleted: bool = None,
    object_uuid: UUID = None,
    type: str = None,
) -> Page[attribute_schemas.Attribute]:
    client = get_opensearch_client()

    must_clauses = []
    if event_uuid is not None:
        must_clauses.append({"term": {"event_uuid.keyword": event_uuid}})
    if deleted is not None:
        must_clauses.append({"term": {"deleted": deleted}})
    if type is not None:
        must_clauses.append({"term": {"type.keyword": type}})

    # None → standalone attributes only (no parent object)
    if object_uuid is None:
        must_clauses.append(
            {"bool": {"must_not": [{"exists": {"field": "object_uuid"}}]}}
        )
    else:
        must_clauses.append({"term": {"object_uuid": str(object_uuid)}})

    query_body = {
        "query": {"bool": {"must": must_clauses}},
        "from": (params.page - 1) * params.size,
        "size": params.size,
        "sort": [{"timestamp": {"order": "desc"}}],
    }

    response = client.search(index="misp-attributes", body=query_body)
    total = response["hits"]["total"]["value"]
    hits = response["hits"]["hits"]

    items = [attribute_schemas.Attribute.model_validate(hit["_source"]) for hit in hits]

    pages = math.ceil(total / params.size) if params.size > 0 else 0
    attributes_page = Page(
        items=items, total=total, page=params.page, size=params.size, pages=pages
    )
    return enrich_attributes_page_with_correlations(attributes_page)


def get_attribute_from_opensearch(
    attribute_uuid: UUID,
) -> Optional[attribute_schemas.Attribute]:
    client = get_opensearch_client()

    try:
        doc = client.get(index="misp-attributes", id=str(attribute_uuid))
        source = doc["_source"]
    except NotFoundError:
        return None

    return attribute_schemas.Attribute.model_validate(source)


def get_attribute_by_uuid(
    db: Session, attribute_uuid: UUID
) -> Optional[attribute_schemas.Attribute]:
    return get_attribute_from_opensearch(attribute_uuid)


def create_attribute(
    db: Session, attribute: attribute_schemas.AttributeCreate
) -> attribute_schemas.Attribute:
    client = get_opensearch_client()
    attribute_uuid = str(attribute.uuid or uuid4())
    now = int(time.time())

    event_uuid = str(attribute.event_uuid) if attribute.event_uuid else None

    dist = attribute.distribution
    dist_val = dist.value if hasattr(dist, "value") else (dist if dist is not None else 5)

    attr_doc = {
        "uuid": attribute_uuid,
        "event_uuid": event_uuid,
        "object_uuid": str(attribute.object_uuid) if attribute.object_uuid else None,
        "object_relation": attribute.object_relation,
        "category": attribute.category,
        "type": attribute.type,
        "value": attribute.value,
        "to_ids": attribute.to_ids if attribute.to_ids is not None else True,
        "timestamp": attribute.timestamp or now,
        "distribution": dist_val,
        "sharing_group_id": attribute.sharing_group_id,
        "comment": attribute.comment or "",
        "deleted": attribute.deleted or False,
        "disable_correlation": attribute.disable_correlation or False,
        "first_seen": attribute.first_seen,
        "last_seen": attribute.last_seen,
        "data": "",
        "tags": [],
        "@timestamp": datetime.fromtimestamp(attribute.timestamp or now).isoformat(),
    }

    client.index(index="misp-attributes", id=attribute_uuid, body=attr_doc, refresh=True)

    tasks.handle_created_attribute(attribute_uuid, attr_doc["object_uuid"], event_uuid)

    return attribute_schemas.Attribute.model_validate(attr_doc)


def create_attribute_from_pulled_attribute(
    db: Session,
    pulled_attribute: MISPAttribute,
    event_uuid: str,
    user: user_models.User,
) -> attribute_schemas.Attribute:
    # TODO: process sharing group // captureSG
    # TODO: enforce warninglist

    dist = pulled_attribute.distribution
    dist_val = (
        event_schemas.DistributionLevel(dist)
        if dist is not None
        else event_schemas.DistributionLevel.INHERIT_EVENT
    )

    attr_create = attribute_schemas.AttributeCreate(
        category=pulled_attribute.category,
        type=pulled_attribute.type,
        value=(
            pulled_attribute.value
            if isinstance(pulled_attribute.value, str)
            else str(pulled_attribute.value)
        ),
        to_ids=pulled_attribute.to_ids,
        uuid=pulled_attribute.uuid,
        timestamp=pulled_attribute.timestamp.timestamp(),
        distribution=dist_val,
        comment=pulled_attribute.comment,
        sharing_group_id=None,
        deleted=pulled_attribute.deleted,
        disable_correlation=pulled_attribute.disable_correlation,
        object_relation=getattr(pulled_attribute, "object_relation", None),
        first_seen=(
            pulled_attribute.first_seen.timestamp()
            if hasattr(pulled_attribute, "first_seen") and pulled_attribute.first_seen
            else None
        ),
        last_seen=(
            pulled_attribute.last_seen.timestamp()
            if hasattr(pulled_attribute, "last_seen") and pulled_attribute.last_seen
            else None
        ),
        event_uuid=event_uuid,
    )

    local_attribute = create_attribute(db, attr_create)

    if pulled_attribute.data is not None:
        attachments_repository.store_attachment(
            str(pulled_attribute.uuid), pulled_attribute.data.getvalue()
        )

    # TODO: process sightings
    # TODO: process galaxies

    capture_attribute_tags(db, pulled_attribute.tags, user, str(local_attribute.uuid))

    return local_attribute


def update_attribute_from_pulled_attribute(
    db: Session,
    local_attribute: attribute_schemas.Attribute,
    pulled_attribute: MISPAttribute,
    user: user_models.User,
) -> attribute_schemas.Attribute:

    if local_attribute.timestamp < pulled_attribute.timestamp.timestamp():
        attribute_patch = attribute_schemas.AttributeUpdate(
            category=pulled_attribute.category,
            type=pulled_attribute.type,
            value=(
                pulled_attribute.value
                if isinstance(pulled_attribute.value, str)
                else str(pulled_attribute.value)
            ),
            to_ids=pulled_attribute.to_ids,
            timestamp=pulled_attribute.timestamp.timestamp(),
            distribution=event_schemas.DistributionLevel(
                pulled_attribute.distribution or DistributionLevel.INHERIT_EVENT
            ),
            comment=pulled_attribute.comment,
            sharing_group_id=None,
            deleted=pulled_attribute.deleted,
            disable_correlation=pulled_attribute.disable_correlation,
            object_relation=getattr(
                pulled_attribute, "object_relation", local_attribute.object_relation
            ),
            first_seen=(
                pulled_attribute.first_seen.timestamp()
                if hasattr(pulled_attribute, "first_seen") and pulled_attribute.first_seen
                else local_attribute.first_seen
            ),
            last_seen=(
                pulled_attribute.last_seen.timestamp()
                if hasattr(pulled_attribute, "last_seen") and pulled_attribute.last_seen
                else local_attribute.last_seen
            ),
        )
        update_attribute(db, local_attribute.uuid, attribute_patch)

    if pulled_attribute.data is not None:
        attachments_repository.store_attachment(
            str(pulled_attribute.uuid), pulled_attribute.data.getvalue()
        )

    capture_attribute_tags(db, pulled_attribute.tags, user, str(local_attribute.uuid))

    # TODO: process sightings
    # TODO: process galaxies

    return get_attribute_from_opensearch(local_attribute.uuid)


def update_attribute(
    db: Session, attribute_uuid: UUID, attribute: attribute_schemas.AttributeUpdate
) -> attribute_schemas.Attribute:
    client = get_opensearch_client()
    os_attr = get_attribute_from_opensearch(attribute_uuid)
    if os_attr is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attribute not found")

    patch = attribute.model_dump(exclude_unset=True)
    for k, v in list(patch.items()):
        if hasattr(v, "value"):
            patch[k] = v.value

    client.update(index="misp-attributes", id=str(os_attr.uuid), body={"doc": patch}, refresh=True)

    tasks.handle_updated_attribute(str(os_attr.uuid), os_attr.object_uuid, str(os_attr.event_uuid) if os_attr.event_uuid else None)

    return get_attribute_from_opensearch(os_attr.uuid)


def delete_attribute(db: Session, attribute_uuid: UUID) -> None:
    client = get_opensearch_client()

    os_attr = get_attribute_from_opensearch(attribute_uuid)

    if os_attr is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attribute not found")

    client.update(
        index="misp-attributes",
        id=str(os_attr.uuid),
        body={"doc": {"deleted": True}},
        refresh=True,
    )

    tasks.handle_deleted_attribute(str(os_attr.uuid), os_attr.object_uuid, str(os_attr.event_uuid) if os_attr.event_uuid else None)


def capture_attribute_tags(
    db: Session,
    tags: list[MISPTag],
    user: user_models.User,
    attribute_uuid: str = None,
):
    tag_name_to_db_tag = {}

    tag_names = [tag.name for tag in tags if not tag.local]

    existing_tags = (
        db.query(tag_models.Tag).filter(tag_models.Tag.name.in_(tag_names)).all()
    )

    for tag in existing_tags:
        tag_name_to_db_tag[tag.name] = tag

    new_tags = []
    for tag in tags:
        if tag.local:
            continue

        if tag.name not in tag_name_to_db_tag:
            new_tag = tag_models.Tag(
                name=tag.name,
                colour=tag.colour,
                org_id=user.org_id,
                user_id=user.id,
                local_only=False,
            )
            new_tags.append(new_tag)
            tag_name_to_db_tag[tag.name] = new_tag

    if new_tags:
        db.add_all(new_tags)
        db.commit()

    if attribute_uuid and tag_name_to_db_tag:
        client = get_opensearch_client()
        tag_dicts = [
            tag_schemas.Tag.model_validate(db_tag).model_dump()
            for db_tag in tag_name_to_db_tag.values()
        ]
        client.update(
            index="misp-attributes",
            id=attribute_uuid,
            body={"doc": {"tags": tag_dicts}},
            refresh=True,
        )


def get_vulnerability_attributes(
    db: Session, event_uuid: str = None
) -> list[attribute_schemas.Attribute]:
    client = get_opensearch_client()
    must_clauses = [{"term": {"type.keyword": "vulnerability"}}]
    if event_uuid is not None:
        must_clauses.append({"term": {"event_uuid.keyword": event_uuid}})

    response = client.search(
        index="misp-attributes",
        body={"query": {"bool": {"must": must_clauses}}, "size": 10000},
    )
    return [
        attribute_schemas.Attribute.model_validate(h["_source"])
        for h in response["hits"]["hits"]
    ]


def search_attributes(
    query: str = None,
    page: int = 0,
    from_value: int = 0,
    size: int = 10,
    sort_by: str = "@timestamp",
    sort_order: str = "desc",
):
    OpenSearchClient = get_opensearch_client()

    search_body = {
        "query": {"query_string": {"query": query, "default_field": "value"}},
        "from": from_value,
        "size": size,
        "sort": [{sort_by: {"order": sort_order}}],
    }
    response = OpenSearchClient.search(index="misp-attributes", body=search_body)

    return {
        "page": page,
        "size": size,
        "total": response["hits"]["total"]["value"],
        "took": response["took"],
        "timed_out": response["timed_out"],
        "max_score": response["hits"]["max_score"],
        "results": response["hits"]["hits"],
    }

def export_attributes(
    query: str = None,
    format: str = "json",
    page_size: int = 1000,
) -> Iterable:
    client = get_opensearch_client()

    index = "misp-attributes"
    default_field = "value"

    search_body = {
        "query": {
            "query_string": {
                "query": query or "*",
                "default_field": default_field,
            }
        },
        "size": page_size,
        "sort": [{"_id": "asc"}],
    }

    search_after = None

    while True:
        if search_after:
            search_body["search_after"] = search_after

        response = client.search(index=index, body=search_body)
        hits = response["hits"]["hits"]

        if not hits:
            break

        for hit in hits:
            if format == "json":
                yield hit

        search_after = hits[-1].get("sort")
