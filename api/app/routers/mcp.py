import logging
from typing import Optional

from app.database import SessionLocal
from app.models import tag as tag_models
from app.repositories import attributes as attributes_repository
from app.repositories import correlations as correlations_repository
from app.repositories import events as events_repository
from app.repositories import freetext as freetext_repository
from app.schemas import event as event_schemas
from app.schemas import tag as tag_schemas
from app.schemas.correlation import CorrelationQueryParams
from app.services.opensearch import get_opensearch_client
from fastmcp import FastMCP
from sqlalchemy.sql import select

logger = logging.getLogger(__name__)

mcp = FastMCP(
    name="MISP Workbench",
    instructions=(
        "You are connected to a MISP-compatible threat intelligence platform. "
        "Use these tools to search events, attributes (IOCs), correlations, "
        "and classify indicators.\n\n"
        "Key concepts:\n"
        "- IOCs (indicators of compromise) are stored as **attributes**. "
        "When a user asks about IOCs, IPs, hashes, domains, URLs, or any "
        "indicator, use search_attributes.\n"
        "- Events are containers that group related attributes together. "
        "When a user asks about incidents, campaigns, threat reports, or "
        "investigations, use search_events.\n"
        "- Use get_index_mapping to discover searchable fields before writing "
        "complex queries.\n\n"
        "When working with tool results, write down any important information "
        "you might need later in your response, as the original tool result "
        "may be cleared later."
    ),
)


# ── Helpers ──────────────────────────────────────────────────────────────────


def _summarize_event_hit(source: dict) -> dict:
    """Strip an event search hit down to essential fields."""
    return {
        "uuid": source.get("uuid"),
        "info": source.get("info"),
        "date": source.get("date"),
        "threat_level": source.get("threat_level"),
        "analysis": source.get("analysis"),
        "published": source.get("published"),
        "attribute_count": source.get("attribute_count"),
        "object_count": source.get("object_count"),
        "tags": [t["name"] for t in source.get("tags", [])],
    }


def _summarize_attribute_hit(source: dict) -> dict:
    """Strip an attribute search hit down to essential fields."""
    result = {
        "uuid": source.get("uuid"),
        "value": source.get("value"),
        "type": source.get("type"),
        "category": source.get("category"),
        "event_uuid": source.get("event_uuid"),
        "to_ids": source.get("to_ids"),
        "comment": source.get("comment") or None,
        "tags": [t["name"] for t in source.get("tags", [])],
    }
    # Include GeoIP enrichment if present
    ip2geo = source.get("expanded", {}).get("ip2geo")
    if ip2geo:
        result["geo"] = {
            "country": ip2geo.get("country_name"),
            "country_code": ip2geo.get("country_iso_code"),
            "city": ip2geo.get("city_name"),
        }
    # Drop None values
    return {k: v for k, v in result.items() if v is not None}


# ── Tools ───────────────────────────────────────────────────────────────────


@mcp.tool
def search_events(query: str, page: int = 1, size: int = 10) -> dict:
    """Search threat intelligence events by keyword or OpenSearch query string.

    The default search field is "info" (event description/title).
    You can target specific fields using field:value syntax.

    Known indexed fields:
      - info (str): event title/description — this is the default search field
      - uuid (str): event UUID
      - org_id, orgc_id (int): organisation IDs
      - date (date): event date
      - threat_level (int): 1=Low, 2=Medium, 3=High, 4=Undefined
      - analysis (int): 0=Initial, 1=Ongoing, 2=Completed
      - published (bool): whether the event is published
      - distribution (int): sharing level
      - attribute_count, object_count (int)
      - tags.name (str): associated tag names

    Use get_index_mapping with index="misp-events" to discover all fields.

    Example queries:
      - "ransomware" — search event info for "ransomware"
      - "info:apt28 AND threat_level:3" — high-threat APT28 events
      - "tags.name:tlp\\:white" — events tagged TLP:WHITE (escape the colon)
      - "published:true AND analysis:2" — published, completed events
    """
    size = min(size, 100)
    from_value = (page - 1) * size
    result = events_repository.search_events(
        query=query, page=page, from_value=from_value, size=size
    )
    return {
        "total": result["total"],
        "page": page,
        "size": size,
        "results": [_summarize_event_hit(hit["_source"]) for hit in result["results"]],
    }


@mcp.tool
def search_attributes(query: str, page: int = 1, size: int = 10) -> dict:
    """Search indicators of compromise (IOCs) in the attribute index.

    The default search field is "value" (the IOC value itself).
    You can target specific fields using field:value syntax.

    Known indexed fields:
      - value (str): the IOC value (IP, hash, domain, URL, etc.) — default field
      - type (str): MISP attribute type, e.g. "ip-src", "ip-dst", "domain",
        "md5", "sha256", "url", "email-src", "vulnerability", etc.
      - category (str): e.g. "Network activity", "Payload delivery",
        "External analysis", "Persistence"
      - event_uuid (str): UUID of parent event
      - event_id (int): ID of parent event
      - to_ids (bool): whether this is an IDS-exportable indicator
      - comment (str): analyst comment
      - tags.name (str): associated tag names
      - uuid (str): attribute UUID
      - deleted (bool)
      - disable_correlation (bool)

    If OpenSearch ingest pipelines are configured, enrichment fields may
    also be available (e.g. expanded.ip2geo.country_iso_code for GeoIP).
    Use get_index_mapping with index="misp-attributes" to discover all fields.

    Example queries:
      - "192.168.1.1" — search by IP value
      - "type:ip-src AND value:10.*" — source IPs in 10.x range
      - "type:ip* AND expanded.ip2geo.country_iso_code:RU" — IPs geolocated in Russia
      - "type:domain AND value:*.ru" — Russian domains
      - "type:sha256" — all SHA256 hashes
      - "category:\\"Network activity\\" AND to_ids:true" — network IOCs flagged for IDS
      - "comment:apt*" — attributes with APT-related comments
      - "tags.name:tlp\\:red" — attributes tagged TLP:RED
    """
    size = min(size, 100)
    from_value = (page - 1) * size
    result = attributes_repository.search_attributes(
        query=query, page=page, from_value=from_value, size=size
    )
    return {
        "total": result["total"],
        "page": page,
        "size": size,
        "results": [_summarize_attribute_hit(hit["_source"]) for hit in result["results"]],
    }


@mcp.tool
def get_event(event_uuid: str, summary: bool = True) -> dict:
    """Retrieve details of a threat intelligence event by UUID.

    Args:
        event_uuid: UUID of the event to retrieve.
        summary: If True (default), returns event metadata with attribute/object
            counts and tag names only — much smaller response. If False, returns
            the full event with all attributes, objects, and nested details.
            Use summary=True first to understand the event, then summary=False
            only if you need the raw attribute data.
    """
    db = SessionLocal()
    try:
        event = events_repository.get_event_by_uuid(db, event_uuid)
        if not event:
            return {"error": f"Event with UUID {event_uuid} not found"}
        data = event_schemas.Event.model_validate(event).model_dump(mode="json")

        if summary:
            return {
                "uuid": data["uuid"],
                "info": data["info"],
                "date": data["date"],
                "threat_level": data.get("threat_level"),
                "analysis": data.get("analysis"),
                "published": data.get("published"),
                "distribution": data.get("distribution"),
                "attribute_count": data.get("attribute_count"),
                "object_count": data.get("object_count"),
                "organisation": data.get("organisation", {}).get("name"),
                "tags": [t["name"] for t in data.get("tags", [])],
            }

        return data
    finally:
        db.close()


@mcp.tool
def get_correlations(
    attribute_value: Optional[str] = None,
    event_uuid: Optional[str] = None,
    page: int = 1,
    size: int = 10,
) -> dict:
    """Find correlations between threat indicators.

    Search by attribute_value to discover related events and indicators
    across the database. Or filter by event_uuid to see all correlations
    for a specific event. Provide at least one of the two parameters.

    Correlation fields:
      - source_attribute_uuid, target_attribute_uuid
      - source_attribute_value, target_attribute_value
      - source_attribute_type, target_attribute_type
      - source_event_uuid, target_event_uuid
      - match_type: "term" (exact), "prefix", "fuzzy", "cidr"
      - score (float)
    """
    if not attribute_value and not event_uuid:
        return {"error": "Provide either attribute_value or event_uuid"}

    size = min(size, 100)
    from_value = (page - 1) * size

    if attribute_value:
        client = get_opensearch_client()
        search_body = {
            "query": {
                "query_string": {
                    "query": attribute_value,
                    "fields": [
                        "source_attribute_value",
                        "target_attribute_value",
                    ],
                }
            },
            "from": from_value,
            "size": size,
        }
        response = client.search(
            index="misp-attribute-correlations", body=search_body
        )
        return {
            "total": response["hits"]["total"]["value"],
            "page": page,
            "size": size,
            "results": [hit["_source"] for hit in response["hits"]["hits"]],
        }

    params = CorrelationQueryParams(source_event_uuid=event_uuid)
    result = correlations_repository.get_correlations(
        params, page=page, from_value=from_value, size=size
    )
    return {
        "total": result["total"],
        "page": page,
        "size": size,
        "results": [hit["_source"] for hit in result["results"]],
    }


@mcp.tool
def detect_indicator_type(values: list[str]) -> list[dict]:
    """Classify freetext values into MISP attribute types.

    Automatically detects: IPv4/IPv6 addresses, MD5/SHA1/SHA256/SHA512 hashes,
    URLs, domains, email addresses, CVE identifiers, and more.
    Accepts up to 100 values at a time.
    """
    values = values[:100]
    return [
        {"value": v, "type": freetext_repository.detect_type(v)} for v in values
    ]


@mcp.tool
def get_statistics() -> dict:
    """Get an overview of the threat intelligence database.

    Returns correlation statistics including total correlation count,
    top correlated events, and top correlated attributes.
    """
    return correlations_repository.get_correlations_stats()


@mcp.tool
def get_tags(filter: Optional[str] = None) -> list[dict]:
    """List available tags for classifying threat intelligence.

    Optionally filter by name substring (case-insensitive).
    Returns up to 100 tags sorted by name.
    """
    db = SessionLocal()
    try:
        query = select(tag_models.Tag).where(
            tag_models.Tag.hide_tag == False  # noqa: E712
        )

        if filter:
            query = query.where(tag_models.Tag.name.ilike(f"%{filter}%"))

        query = query.order_by(tag_models.Tag.name).limit(100)
        results = db.execute(query).scalars().all()

        return [
            tag_schemas.Tag.model_validate(t).model_dump(mode="json")
            for t in results
        ]
    finally:
        db.close()


@mcp.tool
def get_index_mapping(index: str) -> dict:
    """Get the OpenSearch index mapping to discover all available fields.

    Use this to find out what fields are searchable in a given index
    before writing queries.

    Available indices:
      - "misp-attributes" — IOCs and indicators
      - "misp-events" — threat intelligence events
      - "misp-attribute-correlations" — correlations between attributes

    Returns the full field mapping including any enrichment fields added
    by ingest pipelines (e.g. GeoIP, ASN lookups).
    """
    client = get_opensearch_client()
    mapping = client.indices.get_mapping(index=index)
    return mapping
