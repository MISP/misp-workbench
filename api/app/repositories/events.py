import logging
import math
import time
from datetime import datetime
from uuid import UUID, uuid4
from typing import Optional, Union, Iterable
from app.worker import tasks
from app.services.opensearch import get_opensearch_client
from app.services.vulnerability_lookup import lookup as vulnerability_lookup
from app.services.rulezet import lookup as rulezet_lookup
from app.models import feed as feed_models
from app.models import tag as tag_models
from app.models import organisation as org_models
from app.repositories import tags as tags_repository
from app.repositories import attributes as attributes_repository
from app.schemas import event as event_schemas
from app.schemas import user as user_schemas
from app.schemas import organisations as org_schemas
import app.schemas.attribute as attribute_schemas
import app.schemas.vulnerability as vulnerability_schemas
from fastapi import HTTPException, status, Query
from fastapi_pagination import Page, Params
from opensearchpy.exceptions import NotFoundError
from pymisp import MISPEvent, MISPOrganisation
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


def get_events_from_opensearch(
    params: Params,
    info: str = None,
    deleted: bool = None,
    uuid: str = None,
) -> Page[event_schemas.Event]:
    client = get_opensearch_client()

    must_clauses = []
    if info is not None:
        must_clauses.append({"match": {"info": info}})
    if deleted is not None:
        must_clauses.append({"term": {"deleted": deleted}})
    if uuid is not None:
        must_clauses.append({"term": {"uuid.keyword": uuid}})

    query_body = {
        "query": {"bool": {"must": must_clauses}},
        "from": (params.page - 1) * params.size,
        "size": params.size,
        "sort": [{"timestamp": {"order": "desc"}}],
    }

    response = client.search(index="misp-events", body=query_body)
    total = response["hits"]["total"]["value"]
    hits = response["hits"]["hits"]

    items = []
    for hit in hits:
        source = hit["_source"]
        source.setdefault("attributes", [])
        source.setdefault("objects", [])
        items.append(event_schemas.Event.model_validate(source))

    pages = math.ceil(total / params.size) if params.size > 0 else 0
    return Page(items=items, total=total, page=params.page, size=params.size, pages=pages)


def get_event_from_opensearch(event_id: Union[int, UUID]) -> Optional[event_schemas.Event]:
    client = get_opensearch_client()

    if isinstance(event_id, int):
        response = client.search(
            index="misp-events",
            body={"query": {"term": {"id": event_id}}, "size": 1},
        )
        hits = response["hits"]["hits"]
        if not hits:
            return None
        source = hits[0]["_source"]
    else:
        try:
            doc = client.get(index="misp-events", id=str(event_id))
            source = doc["_source"]
        except NotFoundError:
            return None

    source.setdefault("attributes", [])
    source.setdefault("objects", [])
    return event_schemas.Event.model_validate(source)


def search_events(
    query: str = None,
    page: int = 0,
    from_value: int = 0,
    size: int = 10,
    sort_by: str = "@timestamp",
    sort_order: str = "desc",
    searchAttributes: bool = False,
):
    OpenSearchClient = get_opensearch_client()

    index = "misp-attributes" if searchAttributes else "misp-events"
    search_body = {
        "query": {"query_string": {"query": query, "default_field": "info"}},
        "from": from_value,
        "size": size,
        "sort": [{sort_by: {"order": sort_order}}],
    }
    response = OpenSearchClient.search(index=index, body=search_body)

    return {
        "page": page,
        "size": size,
        "total": response["hits"]["total"]["value"],
        "took": response["took"],
        "timed_out": response["timed_out"],
        "max_score": response["hits"]["max_score"],
        "results": response["hits"]["hits"],
    }


def export_events(
    query: str = None,
    format: str = "json",
    page_size: int = 1000,
) -> Iterable:
    client = get_opensearch_client()

    index = "misp-events"
    default_field = "info"

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


def get_event_by_info(info: str) -> Optional[event_schemas.Event]:
    client = get_opensearch_client()
    response = client.search(
        index="misp-events",
        body={"query": {"term": {"info.keyword": info}}, "size": 1},
    )
    hits = response["hits"]["hits"]
    if not hits:
        return None
    source = hits[0]["_source"]
    source.setdefault("attributes", [])
    source.setdefault("objects", [])
    return event_schemas.Event.model_validate(source)


def get_event_uuids_from_opensearch() -> list[str]:
    """Return all event UUIDs from OpenSearch (used for server push)."""
    client = get_opensearch_client()
    response = client.search(
        index="misp-events",
        body={"query": {"match_all": {}}, "size": 10000, "_source": ["uuid"]},
    )
    return [hit["_source"]["uuid"] for hit in response["hits"]["hits"]]


def get_events_by_uuids_from_opensearch(uuids) -> list[event_schemas.Event]:
    """Return events matching the given UUIDs from OpenSearch."""
    client = get_opensearch_client()
    uuids = [str(u) for u in uuids]
    if not uuids:
        return []
    response = client.search(
        index="misp-events",
        body={"query": {"terms": {"uuid.keyword": uuids}}, "size": len(uuids)},
    )
    events = []
    for hit in response["hits"]["hits"]:
        source = hit["_source"]
        source.setdefault("attributes", [])
        source.setdefault("objects", [])
        events.append(event_schemas.Event.model_validate(source))
    return events


def create_event(db: Session, event: event_schemas.EventCreate) -> event_schemas.Event:
    client = get_opensearch_client()
    event_uuid = str(event.uuid or uuid4())
    now = int(time.time())
    ts = event.timestamp or now

    org = db.query(org_models.Organisation).filter_by(id=event.org_id).first()
    org_dict = org_schemas.Organisation.model_validate(org).model_dump(mode="json") if org else None

    event_doc = {
        "uuid": event_uuid,
        "org_id": event.org_id,
        "date": (event.date or datetime.now()).strftime("%Y-%m-%d") if event.date else datetime.now().strftime("%Y-%m-%d"),
        "info": event.info,
        "user_id": event.user_id,
        "published": event.published or False,
        "analysis": event.analysis.value if hasattr(event.analysis, "value") else (event.analysis or 0),
        "attribute_count": 0,
        "object_count": 0,
        "orgc_id": event.orgc_id or event.org_id,
        "timestamp": ts,
        "distribution": event.distribution.value if hasattr(event.distribution, "value") else (event.distribution or 0),
        "sharing_group_id": event.sharing_group_id,
        "sharing_group": None,
        "proposal_email_lock": event.proposal_email_lock or False,
        "locked": event.locked or False,
        "threat_level": event.threat_level.value if hasattr(event.threat_level, "value") else (event.threat_level or 4),
        "publish_timestamp": event.publish_timestamp or 0,
        "sighting_timestamp": event.sighting_timestamp,
        "disable_correlation": event.disable_correlation or False,
        "extends_uuid": str(event.extends_uuid) if event.extends_uuid else None,
        "protected": event.protected or False,
        "deleted": event.deleted or False,
        "tags": [],
        "attributes": [],
        "objects": [],
        "organisation": org_dict,
        "@timestamp": datetime.fromtimestamp(ts).isoformat(),
    }

    client.index(index="misp-events", id=event_uuid, body=event_doc, refresh=True)
    tasks.handle_created_event(event_uuid)

    return event_schemas.Event.model_validate(event_doc)


def create_event_from_pulled_event(pulled_event: MISPEvent) -> event_schemas.Event:
    client = get_opensearch_client()
    event_uuid = str(pulled_event.uuid)
    ts = int(pulled_event.timestamp.timestamp())

    event_doc = {
        "uuid": event_uuid,
        "org_id": pulled_event.org_id,
        "orgc_id": pulled_event.orgc_id or pulled_event.org_id,
        "date": pulled_event.date.isoformat() if hasattr(pulled_event.date, "isoformat") else str(pulled_event.date),
        "info": pulled_event.info,
        "user_id": pulled_event.user_id,
        "published": pulled_event.published or False,
        "analysis": int(pulled_event.analysis) if pulled_event.analysis is not None else 0,
        "attribute_count": pulled_event.attribute_count or 0,
        "object_count": len(pulled_event.objects),
        "timestamp": ts,
        "distribution": int(pulled_event.distribution) if pulled_event.distribution is not None else 0,
        "sharing_group_id": int(pulled_event.sharing_group_id) if pulled_event.sharing_group_id and int(pulled_event.sharing_group_id) > 0 else None,
        "proposal_email_lock": pulled_event.proposal_email_lock or False,
        "locked": pulled_event.locked or False,
        "threat_level": int(pulled_event.threat_level_id) if pulled_event.threat_level_id else 4,
        "publish_timestamp": int(pulled_event.publish_timestamp.timestamp()),
        "disable_correlation": pulled_event.disable_correlation or False,
        "extends_uuid": str(pulled_event.extends_uuid) if pulled_event.extends_uuid else None,
        "protected": getattr(pulled_event, "protected", False) or False,
        "deleted": pulled_event.deleted or False,
        "tags": [],
        "attributes": [],
        "objects": [],
        "organisation": None,
        "sharing_group": None,
        "@timestamp": datetime.fromtimestamp(ts).isoformat(),
    }

    client.index(index="misp-events", id=event_uuid, body=event_doc, refresh=True)
    tasks.handle_created_event.delay(event_uuid)

    return event_schemas.Event.model_validate(event_doc)


def update_event_from_pulled_event(
    existing_event: event_schemas.Event, pulled_event: MISPEvent
) -> event_schemas.Event:
    client = get_opensearch_client()
    event_uuid = str(existing_event.uuid)
    ts = int(pulled_event.timestamp.timestamp())

    patch = {
        "date": pulled_event.date.isoformat() if hasattr(pulled_event.date, "isoformat") else str(pulled_event.date),
        "info": pulled_event.info,
        "published": pulled_event.published or False,
        "analysis": int(pulled_event.analysis) if pulled_event.analysis is not None else 0,
        "attribute_count": pulled_event.attribute_count or 0,
        "object_count": len(pulled_event.objects),
        "timestamp": ts,
        "distribution": int(pulled_event.distribution) if pulled_event.distribution is not None else 0,
        "sharing_group_id": int(pulled_event.sharing_group_id) if pulled_event.sharing_group_id and int(pulled_event.sharing_group_id) > 0 else None,
        "threat_level": int(pulled_event.threat_level_id) if pulled_event.threat_level_id else 4,
        "disable_correlation": pulled_event.disable_correlation or False,
        "extends_uuid": str(pulled_event.extends_uuid) if pulled_event.extends_uuid else None,
        "@timestamp": datetime.fromtimestamp(ts).isoformat(),
    }

    client.update(index="misp-events", id=event_uuid, body={"doc": patch}, refresh=True)
    tasks.handle_updated_event.delay(event_uuid)

    return get_event_from_opensearch(UUID(event_uuid))


def create_event_from_fetched_event(
    db: Session,
    fetched_event: MISPEvent,
    Orgc: MISPOrganisation,
    feed: feed_models.Feed,
    user: user_schemas.User,
) -> event_schemas.Event:
    client = get_opensearch_client()
    event_uuid = str(fetched_event.uuid)
    ts = int(fetched_event.timestamp.timestamp())

    event_doc = {
        "uuid": event_uuid,
        "org_id": Orgc.id,
        "orgc_id": Orgc.id,
        "date": fetched_event.date.isoformat() if hasattr(fetched_event.date, "isoformat") else str(fetched_event.date),
        "info": fetched_event.info,
        "user_id": user.id,
        "published": fetched_event.published or False,
        "analysis": int(fetched_event.analysis) if fetched_event.analysis is not None else 0,
        "attribute_count": 0,
        "object_count": len(fetched_event.objects),
        "timestamp": ts,
        "distribution": feed.distribution.value if hasattr(feed.distribution, "value") else int(feed.distribution),
        "sharing_group_id": feed.sharing_group_id,
        "locked": (fetched_event.locked if hasattr(fetched_event, "locked") else False),
        "threat_level": int(fetched_event.threat_level_id) if fetched_event.threat_level_id else 4,
        "publish_timestamp": int(fetched_event.publish_timestamp.timestamp()),
        "disable_correlation": getattr(fetched_event, "disable_correlation", False),
        "extends_uuid": (
            str(fetched_event.extends_uuid)
            if hasattr(fetched_event, "extends_uuid") and fetched_event.extends_uuid != ""
            else None
        ),
        "protected": False,
        "deleted": False,
        "proposal_email_lock": False,
        "tags": [],
        "attributes": [],
        "objects": [],
        "organisation": None,
        "sharing_group": None,
        "@timestamp": datetime.fromtimestamp(ts).isoformat(),
    }

    client.index(index="misp-events", id=event_uuid, body=event_doc, refresh=True)

    # process tags into OS event doc
    for tag in fetched_event.tags:
        db_tag = tags_repository.get_tag_by_name(db, tag.name)
        if db_tag is None:
            db_tag = tag_models.Tag(
                name=tag.name,
                colour=tag.colour,
                org_id=user.org_id,
                user_id=user.id,
                local_only=tag.local,
            )
            db.add(db_tag)
            db.commit()
            db.refresh(db_tag)
        tags_repository.tag_event(db, event_schemas.Event.model_validate(event_doc), db_tag)

    return event_schemas.Event.model_validate(event_doc)


def update_event_from_fetched_event(
    db: Session,
    fetched_event: MISPEvent,
    Orgc: MISPOrganisation,
    feed: feed_models.Feed,
    user: user_schemas.User,
) -> event_schemas.Event:
    client = get_opensearch_client()
    event_uuid = str(fetched_event.uuid)

    existing = get_event_from_opensearch(UUID(event_uuid))
    if existing is None:
        logger.error(f"Event {event_uuid} not found in OpenSearch")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

    ts = int(fetched_event.timestamp.timestamp())
    patch = {
        "date": fetched_event.date.isoformat() if hasattr(fetched_event.date, "isoformat") else str(fetched_event.date),
        "info": fetched_event.info,
        "published": fetched_event.published or False,
        "analysis": int(fetched_event.analysis) if fetched_event.analysis is not None else 0,
        "object_count": len(fetched_event.objects),
        "org_id": Orgc.id,
        "orgc_id": Orgc.id,
        "timestamp": ts,
        "distribution": feed.distribution.value if hasattr(feed.distribution, "value") else int(feed.distribution),
        "sharing_group_id": feed.sharing_group_id,
        "locked": (fetched_event.locked if hasattr(fetched_event, "locked") else False),
        "threat_level": int(fetched_event.threat_level_id) if fetched_event.threat_level_id else 4,
        "publish_timestamp": int(fetched_event.publish_timestamp.timestamp()),
        "disable_correlation": getattr(fetched_event, "disable_correlation", False),
        "extends_uuid": (
            str(fetched_event.extends_uuid)
            if hasattr(fetched_event, "extends_uuid") and fetched_event.extends_uuid != ""
            else None
        ),
        "@timestamp": datetime.fromtimestamp(ts).isoformat(),
    }

    client.update(index="misp-events", id=event_uuid, body={"doc": patch}, refresh=True)

    # process tags
    for tag in fetched_event.tags:
        db_tag = tags_repository.get_tag_by_name(db, tag.name)
        if db_tag is None:
            db_tag = tag_models.Tag(
                name=tag.name,
                colour=tag.colour,
                org_id=user.org_id,
                user_id=user.id,
                local_only=tag.local,
            )
            db.add(db_tag)
            db.commit()
            db.refresh(db_tag)
        tags_repository.tag_event(db, existing, db_tag)

    return get_event_from_opensearch(UUID(event_uuid))


def update_event(db: Session, event_id: Union[int, UUID], event: event_schemas.EventUpdate) -> event_schemas.Event:
    client = get_opensearch_client()
    os_event = get_event_from_opensearch(event_id)
    if os_event is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

    patch = event.model_dump(exclude_unset=True)
    for k, v in list(patch.items()):
        if hasattr(v, "value"):
            patch[k] = v.value

    client.update(index="misp-events", id=str(os_event.uuid), body={"doc": patch}, refresh=True)
    tasks.handle_updated_event(str(os_event.uuid))

    return get_event_from_opensearch(os_event.uuid)


def delete_event(db: Session, event_id: Union[int, UUID], force: bool = False) -> None:
    client = get_opensearch_client()
    os_event = get_event_from_opensearch(event_id)
    if os_event is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

    event_uuid = str(os_event.uuid)

    if force:
        tasks.delete_indexed_event(event_uuid)
        return

    # Soft delete: mark deleted=True in OS but keep the document so it remains searchable
    client.update(index="misp-events", id=event_uuid, body={"doc": {"deleted": True}}, refresh=True)


def increment_attribute_count(db: Session, event_uuid: str, attributes_count: int = 1) -> None:
    client = get_opensearch_client()
    client.update_by_query(
        index="misp-events",
        body={
            "script": {"source": f"ctx._source.attribute_count += {attributes_count}", "lang": "painless"},
            "query": {"term": {"uuid.keyword": event_uuid}},
        },
        refresh=True,
    )


def decrement_attribute_count(db: Session, event_uuid: str, attributes_count: int = 1) -> None:
    client = get_opensearch_client()
    client.update_by_query(
        index="misp-events",
        body={
            "script": {"source": f"if (ctx._source.attribute_count > 0) {{ ctx._source.attribute_count -= {attributes_count}; }}", "lang": "painless"},
            "query": {"term": {"uuid.keyword": event_uuid}},
        },
        refresh=True,
    )


def increment_object_count(db: Session, event_uuid: str, objects_count: int = 1) -> None:
    client = get_opensearch_client()
    client.update_by_query(
        index="misp-events",
        body={
            "script": {"source": f"ctx._source.object_count += {objects_count}", "lang": "painless"},
            "query": {"term": {"uuid.keyword": event_uuid}},
        },
        refresh=True,
    )


def decrement_object_count(db: Session, event_uuid: str, objects_count: int = 1) -> None:
    client = get_opensearch_client()
    client.update_by_query(
        index="misp-events",
        body={
            "script": {"source": "if (ctx._source.object_count > 0) { ctx._source.object_count -= 1; } else { ctx._source.object_count = 0; }", "lang": "painless"},
            "query": {"term": {"uuid.keyword": event_uuid}},
        },
        refresh=True,
    )


def publish_event(event: event_schemas.Event) -> event_schemas.Event:
    client = get_opensearch_client()
    if event.published:
        return event

    patch = {"published": True, "publish_timestamp": int(time.time())}
    client.update(index="misp-events", id=str(event.uuid), body={"doc": patch}, refresh=True)

    tasks.handle_published_event(str(event.uuid))

    return get_event_from_opensearch(event.uuid)


def unpublish_event(event: event_schemas.Event) -> event_schemas.Event:
    client = get_opensearch_client()
    if not event.published:
        return event

    client.update(index="misp-events", id=str(event.uuid), body={"doc": {"published": False}}, refresh=True)

    tasks.handle_unpublished_event(str(event.uuid))

    return get_event_from_opensearch(event.uuid)


def toggle_event_correlation(event: event_schemas.Event) -> event_schemas.Event:
    client = get_opensearch_client()
    new_val = not event.disable_correlation

    client.update(
        index="misp-events",
        id=str(event.uuid),
        body={"doc": {"disable_correlation": new_val}},
        refresh=True,
    )

    tasks.handle_toggled_event_correlation(str(event.uuid), new_val)

    return get_event_from_opensearch(event.uuid)


def import_data(db: Session, event: event_schemas.Event, data: dict):

    total_imported_attributes = 0
    total_attributes = 0

    if "attributes" in data:
        total_attributes = len(data["attributes"])

        for raw_attribute in data["attributes"]:
            try:
                attribute = attribute_schemas.AttributeCreate(
                    event_uuid=event.uuid,
                    category=raw_attribute.get("category", "External analysis"),
                    type=raw_attribute["type"],
                    value=raw_attribute["value"],
                    distribution=event_schemas.DistributionLevel.INHERIT_EVENT,
                )
                attributes_repository.create_attribute(db, attribute)
                total_imported_attributes += 1
            except Exception as e:
                logger.error(f"Error importing attribute: {e}")
                continue

    return {
        "message": f"Imported {total_imported_attributes} out of {total_attributes} attributes.",
        "imported_attributes": total_imported_attributes,
        "total_attributes": total_attributes,
        "failed_attributes": total_attributes - total_imported_attributes,
        "event_uuid": str(event.uuid),
    }


def get_event_vulnerabilities(
    db: Session,
    event_uuid: str,
) -> list[vulnerability_schemas.Vulnerability]:

    vulnerability_attributes = attributes_repository.get_vulnerability_attributes(
        db, event_uuid=event_uuid
    )

    vulnerabilities = []
    for attribute in vulnerability_attributes:
        vuln_meta = vulnerability_lookup(attribute.value)
        detection_rules = rulezet_lookup(attribute.value)

        vulnerability = vulnerability_schemas.Vulnerability(
            vuln_id=attribute.value,
            attribute_uuid=attribute.uuid,
            description=vuln_meta.get("description", attribute.comment),
            severity=vuln_meta.get("severity", None),
            references=vuln_meta.get("references", None),
            impacted_products=vuln_meta.get("impacted_products", None),
            detection_rules=detection_rules if detection_rules else None,
        )
        vulnerabilities.append(vulnerability)

    return vulnerabilities
