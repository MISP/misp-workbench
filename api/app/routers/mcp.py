import json
import logging
import os
from pathlib import Path
from typing import Optional

from app.auth.auth import is_token_revoked
from app.database import SessionLocal
from app.models.event import AnalysisLevel, DistributionLevel, ThreatLevel
from app.models import tag as tag_models
from app.repositories import attributes as attributes_repository
from app.repositories import correlations as correlations_repository
from app.repositories import events as events_repository
from app.repositories import freetext as freetext_repository
from app.repositories import hunts as hunts_repository
from app.repositories import modules as modules_repository
from app.repositories import reports as reports_repository
from app.repositories import sightings as sightings_repository
from app.repositories import users as users_repository
from app.models import hunt as hunt_models
from app.schemas import event as event_schemas
from app.schemas import hunt as hunt_schemas
from app.schemas import module as module_schemas
from app.schemas import sighting as sighting_schemas
from app.schemas import tag as tag_schemas
from app.schemas.attribute import AttributeType
from app.schemas.correlation import CorrelationQueryParams
from app.services.opensearch import get_opensearch_client
from app.settings import get_settings
from app.auth.auth import create_access_token, get_scopes_for_user
from app.auth.security import get_current_active_user, oauth2_scheme
from app.schemas import user as user_schemas
from app.settings import get_settings
from datetime import timedelta
from fastapi import APIRouter, Depends, Request, Security
from fastmcp import FastMCP
from fastmcp.server.auth import AccessToken, TokenVerifier
from fastmcp.server.dependencies import get_access_token
from jwt import decode as jwt_decode
from jwt.exceptions import InvalidTokenError
from sqlalchemy.sql import select

logger = logging.getLogger(__name__)

MCP_AUTH_ENABLED = os.environ.get("MCP_AUTH_ENABLED", "false").lower() == "true"

router = APIRouter()


@router.get("/mcp/config")
def get_mcp_config(
    request: Request,
    user: user_schemas.User = Security(get_current_active_user, scopes=["mcp:config"]),
):
    """Return a ready-to-use MCP client configuration for this server.

    Requires the mcp:config scope. Generates a dedicated MCP token scoped to
    mcp:* only, valid for the configured refresh token lifetime. Save the
    response as .mcp.json to use it directly with the MCP client.
    """
    settings = get_settings()
    user_scopes = get_scopes_for_user(user)
    if "*" in user_scopes or "mcp:*" in user_scopes:
        mcp_scopes = ["mcp:*"]
    else:
        mcp_scopes = [s for s in user_scopes if s.startswith("mcp:")]
    mcp_token = create_access_token(
        data={"sub": user.email, "scopes": mcp_scopes},
        expires_delta=timedelta(days=settings.OAuth2.refresh_token_expire_days),
    )
    base_url = str(request.base_url).rstrip("/")
    return {
        "mcpServers": {
            "misp-workbench": {
                "type": "http",
                "url": f"{base_url}/mcp",
                "headers": {
                    "Authorization": f"Bearer {mcp_token}",
                },
            }
        }
    }


# ── Auth ────────────────────────────────────────────────────────────────────


class AuthTokenVerifier(TokenVerifier):
    """Validates JWT tokens using the existing MISP Workbench OAuth2 auth flow."""

    async def verify_token(self, token: str) -> Optional[AccessToken]:
        settings = get_settings()
        try:
            payload = jwt_decode(
                token,
                settings.OAuth2.secret_key,
                algorithms=[settings.OAuth2.algorithm],
            )

            if is_token_revoked(payload):
                logger.debug("MCP auth: token revoked")
                return None

            username: str = payload.get("sub")
            if not username:
                return None

            db = SessionLocal()
            try:
                user = users_repository.get_user_by_email(db, email=username)
                if user is None or user.disabled:
                    logger.debug("MCP auth: user not found or disabled")
                    return None
            finally:
                db.close()

            scopes = payload.get("scopes", [])
            return AccessToken(
                token=token,
                client_id=username,
                scopes=scopes,
                expires_at=payload.get("exp"),
                claims=payload,
            )
        except InvalidTokenError:
            logger.debug("MCP auth: invalid token")
            return None


def _check_scope(scope: str) -> None:
    """Check that the current request has the required MCP scope.

    Skipped when MCP_AUTH_ENABLED is false (dev mode).
    Accepts wildcard scopes: ``*`` (full access) and ``mcp:*`` (all MCP tools).
    """
    if not MCP_AUTH_ENABLED:
        return

    token = get_access_token()
    if token is None:
        raise PermissionError("Authentication required")

    if "*" in token.scopes or "mcp:*" in token.scopes or scope in token.scopes:
        return

    raise PermissionError(f"Missing required scope: {scope}")


mcp = FastMCP(
    name="MISP Workbench",
    auth=AuthTokenVerifier() if MCP_AUTH_ENABLED else None,
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
        "Tags on events and attributes come from two sources:\n"
        "- **Taxonomies** — structured labels like `tlp:white`, "
        "`osint:lifetime=\"perpetual\"`, `cert-ist:threat_level=\"medium\"`. "
        "Use misp://taxonomies to browse available taxonomies.\n"
        "- **Galaxies** — knowledge-base entries attached as tags with the "
        "format `misp-galaxy:<type>=\"<value>\"`, e.g. "
        "`misp-galaxy:threat-actor=\"Turla Group\"`, "
        "`misp-galaxy:mitre-attack-pattern=\"Email Collection\"`. "
        "Use misp://galaxies to browse available galaxy types.\n"
        "Both are searchable via the `tags.name` field in search_events and "
        "search_attributes.\n\n"
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


# ── Prompts ─────────────────────────────────────────────────────────────────


@mcp.prompt
def threat_report(keyword: str) -> str:
    """Build a threat intelligence report for a keyword or indicator."""
    return (
        f"Search for events and attributes related to \"{keyword}\". "
        "Summarize your findings as a threat intelligence report with: "
        "1) Overview of related events (dates, threat levels, descriptions). "
        "2) Key IOCs found (IPs, domains, hashes) with their types and geo info. "
        "3) Correlations between indicators. "
        "4) Associated tags (taxonomy and galaxy labels). "
        "5) Assessment and recommended actions."
    )


@mcp.prompt
def ioc_lookup(value: str) -> str:
    """Look up an IOC value and provide context."""
    return (
        f"Look up the indicator \"{value}\": "
        "1) Detect its type using detect_indicator_type. "
        "2) Search for it in attributes. "
        "3) If found, get the parent event(s) for context. "
        "4) Check for correlations with other indicators. "
        "5) Summarize what is known about this indicator."
    )


@mcp.prompt
def threat_actor_profile(name: str) -> str:
    """Profile a threat actor with all available intelligence."""
    return (
        f"Build a profile for threat actor \"{name}\": "
        "1) Search events tagged with this actor "
        f'(tags.name:misp-galaxy\\:threat-actor\\="{name}"). '
        "2) Search for related attributes/IOCs in those events. "
        "3) Check correlations to find linked indicators and campaigns. "
        "4) List associated MITRE ATT&CK techniques from tags. "
        "5) Summarize: known aliases, targeted sectors, TTPs, and key IOCs."
    )


@mcp.prompt
def country_exposure(country_code: str) -> str:
    """Analyze threat exposure for a country using GeoIP data."""
    return (
        f"Analyze threat exposure for country code \"{country_code}\": "
        f"1) Search for IP attributes geolocated in {country_code} "
        f"(type:ip* AND expanded.ip2geo.country_iso_code:{country_code}). "
        "2) Get the parent events to understand the threat context. "
        "3) Break down by threat level and attribute type. "
        "4) Highlight the most correlated indicators. "
        "5) Summarize the threat landscape for this country."
    )


@mcp.prompt
def daily_summary() -> str:
    """Generate a daily threat intelligence summary."""
    return (
        "Generate a daily threat intelligence summary: "
        "1) Get overall statistics using get_statistics. "
        "2) Search for the most recent published events "
        "(published:true, sorted by date). "
        "3) Highlight high-threat events (threat_level:1). "
        "4) List newly seen IOC types and categories. "
        "5) Summarize key findings and recommended watch items."
    )


@mcp.prompt
def enrich_indicator_prompt(value: str, module: str) -> str:
    """Enrich an indicator with a MISP expansion module and summarize the results."""
    return (
        f"Enrich the indicator \"{value}\" using the \"{module}\" module: "
        f"1) Detect its MISP attribute type using detect_indicator_type. "
        f"2) Call enrich_indicator with the detected type and module \"{module}\". "
        "3) If the module returns an error, check that it is enabled and suggest alternatives. "
        "4) Summarize the enrichment results in a concise report: key facts, "
        "geo/ASN data if present, related domains or IPs, reputation scores, "
        "and any other relevant context returned by the module."
    )


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
      - 'tags.name:misp-galaxy\\:threat-actor\\="Turla Group"' — events linked to a threat actor
      - "tags.name:misp-galaxy\\:mitre-attack-pattern*" — events with any MITRE ATT&CK tag

    Tags come from taxonomies (e.g. tlp:white) and galaxies
    (e.g. misp-galaxy:threat-actor="APT28"). Use the misp://taxonomies and
    misp://galaxies resources to discover available tag values.
    """
    _check_scope("mcp:search_events")
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
      - 'tags.name:misp-galaxy\\:threat-actor\\="Turla Group"' — IOCs linked to a threat actor
      - "tags.name:misp-galaxy\\:mitre-attack-pattern*" — IOCs with any MITRE ATT&CK tag

    Tags come from taxonomies (e.g. tlp:white) and galaxies
    (e.g. misp-galaxy:threat-actor="APT28"). Use the misp://taxonomies and
    misp://galaxies resources to discover available tag values.
    """
    _check_scope("mcp:search_attributes")
    logger.info(f"Searching attributes with query: {query}, page: {page}, size: {size}")
    size = min(size, 100)
    from_value = (page - 1) * size
    result = attributes_repository.search_attributes(
        query=query, page=page, from_value=from_value, size=size
    )
    logger.info(f"Found {result['total']} attributes matching query: {query}")
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
    _check_scope("mcp:get_event")
    logger.debug(f"Retrieving event with UUID: {event_uuid}, summary: {summary}")
    db = SessionLocal()
    try:
        event = events_repository.get_event_by_uuid(db, event_uuid)
        if not event:
            logger.debug(f"Event with UUID {event_uuid} not found")
            return {"error": f"Event with UUID {event_uuid} not found"}
        data = event_schemas.Event.model_validate(event).model_dump(mode="json")

        if summary:
            result = {
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
            logger.debug(f"Returning summary for event {event_uuid}")
            return result

        logger.debug(f"Returning full event data for {event_uuid}")
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
    _check_scope("mcp:get_correlations")
    logger.debug(f"Getting correlations for attribute_value: {attribute_value}, event_uuid: {event_uuid}")
    if not attribute_value and not event_uuid:
        error_msg = "Provide either attribute_value or event_uuid"
        logger.debug(error_msg)
        return {"error": error_msg}

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
        total = response["hits"]["total"]["value"]
        logger.debug(f"Found {total} correlations for attribute value: {attribute_value}")
        return {
            "total": total,
            "page": page,
            "size": size,
            "results": [hit["_source"] for hit in response["hits"]["hits"]],
        }

    params = CorrelationQueryParams(source_event_uuid=event_uuid)
    result = correlations_repository.get_correlations(
        params, page=page, from_value=from_value, size=size
    )
    logger.debug(f"Found {result['total']} correlations for event_uuid: {event_uuid}")
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
    _check_scope("mcp:detect_indicator_type")
    logger.debug(f"Detecting indicator types for {len(values)} values")
    values = values[:100]
    result = [
        {"value": v, "type": freetext_repository.detect_type(v)} for v in values
    ]
    logger.debug(f"Detected types for {len(result)} values")
    return result


@mcp.tool
def get_statistics() -> dict:
    """Get an overview of the threat intelligence database.

    Returns correlation statistics including total correlation count,
    top correlated events, and top correlated attributes.
    """
    _check_scope("mcp:get_statistics")
    logger.debug("Retrieving database statistics")
    result = correlations_repository.get_correlations_stats()
    logger.debug(f"Retrieved statistics with {result.get('total_correlations', 0)} total correlations")
    return result


@mcp.tool
def get_tags(filter: Optional[str] = None) -> list[dict]:
    """List available tags for classifying threat intelligence.

    Optionally filter by name substring (case-insensitive).
    Returns up to 100 tags sorted by name.
    """
    _check_scope("mcp:get_tags")
    logger.debug(f"Retrieving tags with filter: {filter}")
    db = SessionLocal()
    try:
        query = select(tag_models.Tag).where(
            tag_models.Tag.hide_tag == False  # noqa: E712
        )

        if filter:
            query = query.where(tag_models.Tag.name.ilike(f"%{filter}%"))

        query = query.order_by(tag_models.Tag.name).limit(100)
        results = db.execute(query).scalars().all()

        result = [
            tag_schemas.Tag.model_validate(t).model_dump(mode="json")
            for t in results
        ]
        logger.debug(f"Retrieved {len(result)} tags")
        return result
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
    _check_scope("mcp:get_index_mapping")
    logger.debug(f"Retrieving index mapping for index: {index}")
    client = get_opensearch_client()
    mapping = client.indices.get_mapping(index=index)
    logger.debug(f"Retrieved mapping for index: {index}")
    return mapping


@mcp.tool
def search_galaxy(
    galaxy_type: str,
    query: str,
    size: int = 10,
) -> dict:
    """Search for entries in a MISP galaxy cluster by name or synonym.

    Performs a case-insensitive substring match against cluster values,
    their synonyms, and descriptions. Use this instead of reading the
    full misp://galaxies/{type} resource when looking for specific entries.

    Args:
        galaxy_type: Galaxy type to search in, e.g. "threat-actor", "mitre-attack-pattern",
            "malware", "tool", "sector", "country", "botnet", "ransomware", etc.
            Use the misp://galaxies resource to discover available types.
        query: Search string to match against value names, synonyms, and descriptions.
        size: Maximum number of results to return (default 10, max 50).

    Example usage:
      - search_galaxy("threat-actor", "APT1") — find APT1 and its synonyms
      - search_galaxy("threat-actor", "ShadyRAT") — find actors with ShadyRAT as synonym
      - search_galaxy("mitre-attack-pattern", "phishing") — MITRE ATT&CK phishing techniques
      - search_galaxy("malware", "emotet") — look up the Emotet malware family
    """
    _check_scope("mcp:search_galaxy")
    logger.debug(f"Searching galaxy {galaxy_type} with query: {query}, size: {size}")
    size = min(size, 50)
    cluster_file = _CLUSTERS_DIR / f"{galaxy_type}.json"
    if not cluster_file.is_file():
        error_msg = f"Galaxy cluster '{galaxy_type}' not found"
        logger.debug(error_msg)
        return {"error": error_msg}

    cluster_data = json.loads(cluster_file.read_text())
    query_lower = query.lower()
    matches = []

    for v in cluster_data.get("values", []):
        value_name = v.get("value", "")
        synonyms = v.get("meta", {}).get("synonyms", [])
        description = v.get("description", "")

        searchable = [value_name.lower(), description.lower()]
        searchable.extend(s.lower() for s in synonyms)

        if any(query_lower in s for s in searchable):
            entry = {
                "value": value_name,
                "description": description[:300] + "..." if len(description) > 300 else description,
                "uuid": v.get("uuid"),
            }
            if synonyms:
                entry["synonyms"] = synonyms
            meta = v.get("meta", {})
            country = meta.get("country") or meta.get("cfr-suspected-state-sponsor")
            if country:
                entry["country"] = country
            matches.append(entry)
            if len(matches) >= size:
                break

    result = {
        "galaxy_type": galaxy_type,
        "query": query,
        "total": len(matches),
        "results": matches,
    }
    logger.debug(f"Found {len(matches)} matches in galaxy {galaxy_type}")
    return result


@mcp.tool
def search_taxonomy(query: str, size: int = 20) -> dict:
    """Search across all MISP taxonomies for matching tags.

    Performs a case-insensitive substring match against taxonomy namespaces,
    predicate names, value labels, and descriptions. Returns matching tags
    in their usable format (e.g. "tlp:white", "cert-ist:threat_level=\\"medium\\"").

    Args:
        query: Search string, e.g. "threat level", "white", "tlp", "phishing".
        size: Maximum number of results to return (default 20, max 100).

    Example usage:
      - search_taxonomy("tlp") — find all TLP tags
      - search_taxonomy("threat level") — find threat-level related tags
      - search_taxonomy("phishing") — find tags related to phishing
      - search_taxonomy("osint") — find OSINT-related taxonomy tags
    """
    _check_scope("mcp:search_taxonomy")
    logger.debug(f"Searching taxonomy with query: {query}, size: {size}")
    size = min(size, 100)
    query_lower = query.lower()
    matches = []

    for path in sorted(_TAXONOMIES_DIR.iterdir()):
        mt = path / "machinetag.json"
        if not mt.is_file():
            continue
        data = json.loads(mt.read_text())
        namespace = data.get("namespace", path.name)
        tax_desc = data.get("description", "")

        # Check if taxonomy-level metadata matches
        tax_matches = query_lower in namespace.lower() or query_lower in tax_desc.lower()

        values_by_predicate = {}
        for group in data.get("values", []):
            for e in group.get("entry", []):
                values_by_predicate.setdefault(group["predicate"], []).append(e)

        for p in data.get("predicates", []):
            pred_value = p["value"]
            pred_expanded = p.get("expanded", pred_value)
            pred_desc = p.get("description", "")
            pred_searchable = f"{pred_value} {pred_expanded} {pred_desc}".lower()
            pred_matches = tax_matches or query_lower in pred_searchable

            entries = values_by_predicate.get(pred_value)
            if entries:
                for e in entries:
                    e_value = e["value"]
                    e_expanded = e.get("expanded", e_value)
                    e_desc = e.get("description", "")
                    e_searchable = f"{e_value} {e_expanded} {e_desc}".lower()

                    if pred_matches or query_lower in e_searchable:
                        matches.append({
                            "tag": f'{namespace}:{pred_value}="{e_value}"',
                            "expanded": f"{pred_expanded}: {e_expanded}",
                            "namespace": namespace,
                            "description": e_desc[:200] + "..." if len(e_desc) > 200 else e_desc or None,
                        })
                        if len(matches) >= size:
                            result = {"query": query, "total": len(matches), "results": matches}
                            logger.debug(f"Found {len(matches)} taxonomy matches")
                            return result
            else:
                # Predicate-only tag (no sub-values)
                if pred_matches:
                    matches.append({
                        "tag": f"{namespace}:{pred_value}",
                        "expanded": pred_expanded,
                        "namespace": namespace,
                        "description": pred_desc[:200] + "..." if len(pred_desc) > 200 else pred_desc or None,
                    })
                    if len(matches) >= size:
                        result = {"query": query, "total": len(matches), "results": matches}
                        logger.debug(f"Found {len(matches)} taxonomy matches")
                        return result

    result = {"query": query, "total": len(matches), "results": matches}
    logger.debug(f"Found {len(matches)} taxonomy matches")
    return result


@mcp.tool
def get_sightings(
    value: Optional[str] = None,
    attribute_uuid: Optional[str] = None,
    type: Optional[str] = None,
    page: int = 1,
    size: int = 10,
) -> dict:
    """Search for sightings of an indicator.

    Sightings record when and where an IOC was observed. Use this to answer
    "has this indicator been seen before?" and "how many times?".

    Args:
        value: IOC value to search for (e.g. an IP, domain, hash).
            Searches via OpenSearch query_string against the value field.
        attribute_uuid: Filter by specific attribute UUID.
        type: Sighting type filter — "positive" (confirmed seen),
            "negative" (confirmed not seen), or "expiration".
        page: Page number (default 1).
        size: Results per page (default 10, max 100).

    Returns sighting records with value, type, timestamp, observer org,
    and linked attribute UUID.
    """
    _check_scope("mcp:get_sightings")
    logger.debug(f"Retrieving sightings for value: {value}, attribute_uuid: {attribute_uuid}, type: {type}")
    size = min(size, 100)
    from_value = (page - 1) * size

    if value:
        client = get_opensearch_client()
        query_body: dict = {
            "from": from_value,
            "size": size,
            "query": {"bool": {"must": [{"query_string": {"query": value, "default_field": "value"}}]}},
            "sort": [{"@timestamp": {"order": "desc"}}],
        }
        if type:
            query_body["query"]["bool"]["must"].append({"term": {"type.keyword": type}})
        response = client.search(index="misp-sightings", body=query_body)
        total = response["hits"]["total"]["value"]
        logger.debug(f"Found {total} sightings for value: {value}")
        return {
            "total": total,
            "page": page,
            "size": size,
            "results": [hit["_source"] for hit in response["hits"]["hits"]],
        }

    params = sighting_schemas.SightingQueryParams(
        attribute_uuid=attribute_uuid, type=type
    )
    result = sightings_repository.get_sightings(
        params=params, page=page, from_value=from_value, size=size
    )
    logger.debug(f"Found {result['total']} sightings for attribute_uuid: {attribute_uuid}")
    return {
        "total": result["total"],
        "page": page,
        "size": size,
        "results": [hit["_source"] for hit in result["results"]],
    }


@mcp.tool
def get_sighting_activity(
    value: str,
    period: str = "7d",
    interval: str = "1d",
) -> dict:
    """Get a sighting activity histogram for an indicator over time.

    Shows how often an IOC was observed (positive sightings) across
    time buckets — useful for spotting activity spikes or trends.

    Args:
        value: The IOC value to get activity for.
        period: Time window to look back, e.g. "7d", "30d", "90d" (default "7d").
        interval: Bucket size, e.g. "1h", "1d", "1w" (default "1d").

    Returns time-series buckets with doc_count per interval.
    """
    _check_scope("mcp:get_sightings")
    logger.debug(f"Getting sighting activity for value: {value}, period: {period}, interval: {interval}")
    params = sighting_schemas.SightingActivityParams(
        value=value, period=period, interval=interval
    )
    activity = sightings_repository.get_sightings_activity_by_value(params)
    buckets = activity.get("sightings_over_time", {}).get("buckets", [])
    result = {
        "value": value,
        "period": period,
        "interval": interval,
        "buckets": [
            {"date": b["key_as_string"], "count": b["doc_count"]}
            for b in buckets
        ],
    }
    logger.debug(f"Retrieved sighting activity with {len(buckets)} time buckets")
    return result


@mcp.tool
def list_hunts(filter: Optional[str] = None) -> list[dict]:
    """List saved threat hunts.

    Hunts are saved queries that run against the OpenSearch indices
    (attributes, events, or correlations) or against Rulezet. They track
    match counts over time so analysts can spot emerging threats.

    Args:
        filter: Optional name substring to filter hunts (case-insensitive).

    Returns hunt metadata: id, name, description, query, hunt_type,
    index_target, status, last_run_at, last_match_count.
    """
    _check_scope("mcp:list_hunts")
    logger.debug(f"Listing hunts with filter: {filter}")
    db = SessionLocal()
    try:
        query = db.query(hunt_models.Hunt)
        if filter:
            query = query.where(hunt_models.Hunt.name.ilike(f"%{filter}%"))
        query = query.order_by(hunt_models.Hunt.created_at.desc()).limit(100)
        hunts = query.all()
        result = [
            hunt_schemas.Hunt.model_validate(h).model_dump(mode="json")
            for h in hunts
        ]
        logger.debug(f"Retrieved {len(result)} hunts")
        return result
    finally:
        db.close()


@mcp.tool
def get_hunt_results(hunt_id: int) -> dict:
    """Get the latest results from a saved hunt.

    Returns the cached results from the most recent run of the hunt,
    including total match count and the matching hits (up to 100).
    Use list_hunts first to find the hunt ID.

    Args:
        hunt_id: The hunt ID (from list_hunts).
    """
    _check_scope("mcp:get_hunt_results")
    logger.debug(f"Retrieving results for hunt ID: {hunt_id}")
    results = hunts_repository.get_hunt_results(hunt_id)
    if results is None:
        error_msg = f"No results available for hunt {hunt_id}. It may not have been run yet."
        logger.debug(error_msg)
        return {"error": error_msg}
    logger.debug(f"Retrieved results for hunt ID: {hunt_id}")
    return results


@mcp.tool
def get_hunt_history(hunt_id: int) -> dict:
    """Get the run history for a hunt showing match counts over time.

    Returns up to 90 recent runs with timestamps and match counts.
    Useful for spotting trends — a rising match count may indicate
    an emerging threat.

    Args:
        hunt_id: The hunt ID (from list_hunts).
    """
    _check_scope("mcp:get_hunt_history")
    logger.debug(f"Retrieving history for hunt ID: {hunt_id}")
    db = SessionLocal()
    try:
        history = hunts_repository.get_hunt_history(db, hunt_id)
        result = {
            "hunt_id": hunt_id,
            "total_runs": len(history),
            "history": history,
        }
        logger.debug(f"Retrieved history for hunt ID: {hunt_id} with {len(history)} runs")
        return result
    finally:
        db.close()


@mcp.tool
def run_hunt(hunt_id: int) -> dict:
    """Execute a saved hunt and return the results.

    Runs the hunt query against its configured index and returns
    matching hits. Also updates the hunt's last_run_at and
    last_match_count, and appends to the run history.

    Args:
        hunt_id: The hunt ID (from list_hunts).
    """
    _check_scope("mcp:run_hunt")
    logger.debug(f"Running hunt with ID: {hunt_id}")
    db = SessionLocal()
    try:
        result = hunts_repository.execute_hunt_system(db, hunt_id)
        if result is None:
            error_msg = f"Hunt {hunt_id} not found"
            logger.debug(error_msg)
            return {"error": error_msg}
        logger.debug(f"Completed hunt {hunt_id} with {result['total']} matches")
        return {
            "hunt_id": hunt_id,
            "name": result["hunt"].name,
            "total": result["total"],
            "hits": result["hits"],
        }
    finally:
        db.close()


@mcp.tool
def get_event_reports(event_uuid: str) -> dict:
    """Retrieve event reports attached to a specific MISP event.

    Event reports are textual documents (markdown or plain text) attached to
    events, containing analysis, context, or narrative descriptions.

    Args:
        event_uuid: The UUID of the event whose reports to retrieve.
    """
    _check_scope("mcp:get_event_reports")
    logger.debug(f"Retrieving event reports for event_uuid: {event_uuid}")
    hits = reports_repository.get_event_reports_by_event_uuid(event_uuid)
    results = [h["_source"] for h in hits]
    logger.debug(f"Found {len(results)} reports for event {event_uuid}")
    return {"event_uuid": event_uuid, "total": len(results), "results": results}


@mcp.tool
def search_event_reports(
    query: Optional[str] = None,
    name: Optional[str] = None,
    event_uuid: Optional[str] = None,
    page: int = 1,
    size: int = 10,
) -> dict:
    """Search event reports across all MISP events.

    Supports full-text search on report content and name, filtering by event
    UUID, and pagination. Results are sorted by most recent first.

    Args:
        query: Full-text search query across report name and content.
        name: Filter by report name (partial match).
        event_uuid: Filter reports belonging to a specific event UUID.
        page: Page number (1-based).
        size: Number of results per page (max 100).
    """
    _check_scope("mcp:search_event_reports")
    logger.debug(
        f"Searching event reports: query={query}, name={name}, event_uuid={event_uuid}"
    )
    size = min(size, 100)
    from_value = (page - 1) * size

    client = get_opensearch_client()
    must_clauses: list = [{"term": {"deleted": False}}]

    if query:
        must_clauses.append(
            {"multi_match": {"query": query, "fields": ["name", "content"]}}
        )
    if name:
        must_clauses.append({"match": {"name": name}})
    if event_uuid:
        must_clauses.append({"term": {"event_uuid.keyword": event_uuid}})

    query_body = {
        "from": from_value,
        "size": size,
        "query": {"bool": {"must": must_clauses}},
        "sort": [{"@timestamp": {"order": "desc"}}],
    }

    response = client.search(index="misp-event-reports", body=query_body)
    hits = response["hits"]["hits"]
    total = response["hits"]["total"]["value"]
    results = [h["_source"] for h in hits]
    logger.debug(
        f"Event reports search returned {total} total, {len(results)} in page {page}"
    )
    return {"total": total, "page": page, "size": size, "results": results}


_MODULE_ALIASES = {
    "geolocation": "mmdb_lookup",
    "geoip": "mmdb_lookup",
    "geo": "mmdb_lookup",
    "ip2geo": "mmdb_lookup",
}


@mcp.tool
def enrich_indicator(value: str, type: str, module: str) -> dict:
    """Enrich an indicator using a MISP expansion module.

    Sends the indicator to the specified misp-module for enrichment and returns
    the results (new attributes, objects, related context). The module must be
    enabled in the platform configuration.

    Common aliases are resolved automatically:
        "geolocation", "geoip", "geo", "ip2geo" → mmdb_lookup

    Examples:
        enrich_indicator("8.8.8.8", "ip-dst", "geolocation")
        enrich_indicator("evil.com", "domain", "whois")
        enrich_indicator("d41d8cd98f00b204e9800998ecf8427e", "md5", "virustotal")

    Args:
        value: The indicator value to enrich (e.g. "8.8.8.8", "evil.com").
        type: The MISP attribute type (e.g. "ip-dst", "domain", "md5").
        module: The module name to use for enrichment (e.g. "mmdb_lookup").
    """
    _check_scope("mcp:enrich_indicator")
    module = _MODULE_ALIASES.get(module.lower(), module)
    logger.debug(f"Enriching indicator value={value} type={type} with module={module}")
    db = SessionLocal()
    try:
        query = module_schemas.ModuleQuery(
            module=module,
            attribute={"type": type, "value": value, "uuid": ""},
        )
        result = modules_repository.query_module(db, query)
        logger.debug(f"Enrichment completed for {value} via {module}")
        return result
    except Exception as e:
        error_msg = str(e)
        logger.debug(f"Enrichment failed for {value} via {module}: {error_msg}")
        return {"error": error_msg}
    finally:
        db.close()


# ── Resources ──────────────────────────────────────────────────────────────


@mcp.resource("misp://attribute-types")
def attribute_types() -> dict:
    """All valid MISP attribute types grouped by category."""
    types_by_category = {
        "hashes": [],
        "network": [],
        "email": [],
        "file": [],
        "detection": [],
        "financial": [],
        "person": [],
        "other": [],
    }
    hash_keywords = {"md5", "sha", "ssdeep", "imphash", "tlsh", "vhash", "pehash",
                     "cdhash", "authentihash", "telfhash", "impfuzzy"}
    network_keywords = {"ip-", "domain", "hostname", "url", "uri", "port", "AS",
                        "mac-", "community-id", "snort", "bro", "zeek", "user-agent",
                        "http-method", "ja3", "jarm", "hassh", "ssh-fingerprint",
                        "favicon-mmh3", "cookie"}
    email_keywords = {"email", "dkim"}
    file_keywords = {"filename", "attachment", "malware-sample", "pattern-in-file",
                     "pattern-in-memory", "size-in-bytes", "mime-type"}
    detection_keywords = {"yara", "sigma", "stix2-pattern", "snort", "bro", "zeek",
                          "kusto-query", "vulnerability", "cpe", "weakness", "cve"}
    financial_keywords = {"btc", "dash", "xmr", "iban", "bic", "bank-account",
                          "aba-rtn", "bin", "cc-number", "prtn"}
    person_keywords = {"first-name", "last-name", "middle-name", "full-name",
                       "date-of-birth", "gender", "nationality", "passport",
                       "phone-number", "identity-card"}

    for t in AttributeType:
        v = t.value
        if any(k in v for k in hash_keywords):
            types_by_category["hashes"].append(v)
        elif any(k in v for k in network_keywords):
            types_by_category["network"].append(v)
        elif any(k in v for k in email_keywords):
            types_by_category["email"].append(v)
        elif any(k in v for k in file_keywords):
            types_by_category["file"].append(v)
        elif any(k in v for k in detection_keywords):
            types_by_category["detection"].append(v)
        elif any(k in v for k in financial_keywords):
            types_by_category["financial"].append(v)
        elif any(k in v for k in person_keywords):
            types_by_category["person"].append(v)
        else:
            types_by_category["other"].append(v)

    return {
        "total": len(AttributeType),
        "types": types_by_category,
    }


@mcp.resource("misp://attribute-categories")
def attribute_categories() -> list[str]:
    """All valid MISP attribute categories."""
    return [
        "Antivirus detection",
        "Artifacts dropped",
        "Attribution",
        "External analysis",
        "Financial fraud",
        "Internal reference",
        "Network activity",
        "Other",
        "Payload delivery",
        "Payload installation",
        "Payload type",
        "Persistence mechanism",
        "Person",
        "Social network",
        "Support Tool",
        "Targeting data",
    ]


@mcp.resource("misp://threat-levels")
def threat_levels() -> dict:
    """MISP threat level ID-to-label mapping."""
    return {str(t.value): t.name.capitalize() for t in ThreatLevel}


@mcp.resource("misp://analysis-levels")
def analysis_levels() -> dict:
    """MISP analysis level ID-to-label mapping."""
    return {str(a.value): a.name.capitalize() for a in AnalysisLevel}


@mcp.resource("misp://distribution-levels")
def distribution_levels() -> dict:
    """MISP distribution level ID-to-label mapping."""
    return {
        str(d.value): d.name.replace("_", " ").title() for d in DistributionLevel
    }


@mcp.resource("misp://query-syntax")
def query_syntax() -> str:
    """OpenSearch query string syntax reference for searching events and attributes."""
    return (
        "# OpenSearch Query String Syntax\n\n"
        "The search_events and search_attributes tools accept OpenSearch query strings.\n\n"
        "## Basics\n"
        "- Simple keyword: `ransomware`\n"
        "- Field-qualified: `type:ip-src`\n"
        "- Wildcard: `value:192.168.*`\n"
        "- Boolean: `type:ip-src AND to_ids:true`\n"
        "- OR: `type:ip-src OR type:ip-dst`\n"
        "- NOT: `NOT type:domain`\n"
        "- Grouping: `(type:ip-src OR type:ip-dst) AND to_ids:true`\n"
        "- Phrase: `category:\"Network activity\"`\n"
        "- Escape colons in values: `tags.name:tlp\\:white`\n\n"
        "## Event fields\n"
        "- info (default), uuid, date, org_id, orgc_id\n"
        "- threat_level (1=High, 2=Medium, 3=Low, 4=Undefined)\n"
        "- analysis (0=Initial, 1=Ongoing, 2=Complete)\n"
        "- published (bool), distribution (int)\n"
        "- attribute_count, object_count, tags.name\n\n"
        "## Attribute fields\n"
        "- value (default), type, category, uuid\n"
        "- event_uuid, event_id, to_ids (bool)\n"
        "- comment, tags.name, deleted, disable_correlation\n"
        "- expanded.ip2geo.country_iso_code (GeoIP enrichment)\n"
    )


_SUBMODULES_DIR = Path(__file__).resolve().parent.parent / "submodules"
_TAXONOMIES_DIR = _SUBMODULES_DIR / "misp-taxonomies"
_GALAXIES_DIR = _SUBMODULES_DIR / "misp-galaxy" / "galaxies"
_CLUSTERS_DIR = _SUBMODULES_DIR / "misp-galaxy" / "clusters"


@mcp.resource("misp://taxonomies")
def taxonomies_index() -> list[dict]:
    """List all available MISP taxonomies with namespace and description.

    Use misp://taxonomies/{namespace} to get full details for a specific taxonomy.
    """
    result = []
    for path in sorted(_TAXONOMIES_DIR.iterdir()):
        mt = path / "machinetag.json"
        if not mt.is_file():
            continue
        data = json.loads(mt.read_text())
        result.append({
            "namespace": data.get("namespace", path.name),
            "description": data.get("description", ""),
            "version": data.get("version"),
            "exclusive": data.get("exclusive", False),
        })
    return result


@mcp.resource("misp://taxonomies/{namespace}")
def taxonomy_detail(namespace: str) -> dict:
    """Get full details for a MISP taxonomy including predicates and values.

    Returns the taxonomy namespace, description, predicates (tag stems),
    and their allowed values with expanded labels.
    """
    mt = _TAXONOMIES_DIR / namespace / "machinetag.json"
    if not mt.is_file():
        return {"error": f"Taxonomy '{namespace}' not found"}
    data = json.loads(mt.read_text())

    predicates = []
    for p in data.get("predicates", []):
        predicates.append({
            "value": p["value"],
            "expanded": p.get("expanded", p["value"]),
            "description": p.get("description"),
        })

    values_by_predicate = {}
    for group in data.get("values", []):
        predicate = group["predicate"]
        entries = []
        for e in group.get("entry", []):
            entries.append({
                "value": e["value"],
                "expanded": e.get("expanded", e["value"]),
                "description": e.get("description"),
            })
        values_by_predicate[predicate] = entries

    return {
        "namespace": data.get("namespace", namespace),
        "description": data.get("description", ""),
        "version": data.get("version"),
        "exclusive": data.get("exclusive", False),
        "predicates": predicates,
        "values": values_by_predicate,
    }


@mcp.resource("misp://galaxies")
def galaxies_index() -> list[dict]:
    """List all available MISP galaxies with type and description.

    Galaxies are knowledge-base collections (threat actors, malware families,
    ATT&CK techniques, tools, sectors, etc.).
    Use misp://galaxies/{type} to get cluster entries for a specific galaxy.
    """
    result = []
    for path in sorted(_GALAXIES_DIR.glob("*.json")):
        data = json.loads(path.read_text())
        result.append({
            "type": data.get("type", path.stem),
            "name": data.get("name", ""),
            "description": data.get("description", ""),
            "namespace": data.get("namespace", "misp"),
            "icon": data.get("icon"),
        })
    return result


@mcp.resource("misp://galaxies/{galaxy_type}")
def galaxy_detail(galaxy_type: str) -> dict:
    """Get cluster entries for a MISP galaxy.

    Returns the galaxy metadata and a summarized list of cluster values
    (name, description, synonyms). Clusters can be large (e.g. threat-actor
    has 900+ entries), so descriptions are truncated to 200 chars.
    """
    galaxy_file = _GALAXIES_DIR / f"{galaxy_type}.json"
    if not galaxy_file.is_file():
        return {"error": f"Galaxy '{galaxy_type}' not found"}
    galaxy = json.loads(galaxy_file.read_text())

    cluster_file = _CLUSTERS_DIR / f"{galaxy_type}.json"
    values = []
    if cluster_file.is_file():
        cluster_data = json.loads(cluster_file.read_text())
        for v in cluster_data.get("values", []):
            desc = v.get("description", "")
            entry = {
                "value": v.get("value", ""),
                "description": (desc[:200] + "...") if len(desc) > 200 else desc,
                "uuid": v.get("uuid"),
            }
            synonyms = v.get("meta", {}).get("synonyms")
            if synonyms:
                entry["synonyms"] = synonyms
            values.append(entry)

    return {
        "type": galaxy.get("type", galaxy_type),
        "name": galaxy.get("name", ""),
        "description": galaxy.get("description", ""),
        "namespace": galaxy.get("namespace", "misp"),
        "total_values": len(values),
        "values": values,
    }
