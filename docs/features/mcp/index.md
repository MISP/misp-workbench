# MCP Server

misp-workbench exposes a [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) server that lets AI assistants (Claude, Cursor, VS Code Copilot, etc.) interact with your threat intelligence database directly from a chat interface.

The MCP server is served at `/mcp` using the [Streamable HTTP transport](https://spec.modelcontextprotocol.io/specification/2025-03-26/basic/transports/#streamable-http). It provides:

- **tools** — search events, attributes, correlations, sightings, hunts, reports, and enrich indicators
- **resources** — static reference data (attribute types, taxonomies, galaxies, query syntax)
- **prompts** — reusable analysis templates (threat reports, IOC lookups, actor profiles)

<video width="1080" controls>
  <source src="../../../screenshots/claude-code/claude-code_4-analyse-ioc-misp-workbench-mcp.webm" type="video/mp4">
</video>

## Quick start

### 1. Get the client configuration

Call the `/mcp/config` endpoint to generate a ready-to-use MCP client config with a scoped bearer token:

```
GET /mcp/config
Authorization: Bearer <your-token>
Required scope: mcp:config
```

Response:

```json
{
  "mcpServers": {
    "misp-workbench": {
      "type": "http",
      "url": "https://your-instance/mcp",
      "headers": {
        "Authorization": "Bearer <mcp-scoped-token>"
      }
    }
  }
}
```

The generated token is scoped to `mcp:*` only (no access to the REST API) and is valid for the configured refresh token lifetime.

### 2. Add to your MCP client

=== "Claude Desktop"

    Save the response as `~/.claude/mcp.json` (or paste the `mcpServers` block into your existing config):

    ```json
    {
      "mcpServers": {
        "misp-workbench": {
          "type": "http",
          "url": "https://your-instance/mcp",
          "headers": {
            "Authorization": "Bearer <mcp-scoped-token>"
          }
        }
      }
    }
    ```

=== "Cursor / VS Code"

    Add the server under **Settings → MCP Servers** or paste into `.cursor/mcp.json` at the project root. Use the same `type: http` configuration.


## Configuration

| Variable | Default | Description |
|---|---|---|
| `MCP_AUTH_ENABLED` | `false` | Set to `true` to require a valid Bearer token on all MCP requests. Without this, the server is open to any caller with network access. |

!!! warning "Enable auth in production"
    Always set `MCP_AUTH_ENABLED=true` when the MCP endpoint is publicly reachable. Without it, any client can call all tools without authentication.


## Tools

Tools are the primary interface for AI assistants to query threat intelligence data.

| Tool | Scope | Description |
|---|---|---|
| `search_events` | `mcp:search_events` | Full-text search across threat intelligence events using Lucene query syntax |
| `search_attributes` | `mcp:search_attributes` | Search IOCs and indicators (IPs, hashes, domains, URLs, etc.) |
| `get_event` | `mcp:get_event` | Retrieve an event by UUID — summary mode (default) or full with all attributes |
| `get_correlations` | `mcp:get_correlations` | Find correlations between indicators by attribute value or event UUID |
| `detect_indicator_type` | `mcp:detect_indicator_type` | Classify freetext values into MISP attribute types (IP, hash, domain, CVE…) |
| `get_statistics` | `mcp:get_statistics` | Overview of the database: total correlations, top events, top attributes |
| `get_tags` | `mcp:get_tags` | List available tags, optionally filtered by name substring |
| `get_index_mapping` | `mcp:get_index_mapping` | Inspect OpenSearch field mappings before writing queries |
| `search_galaxy` | `mcp:search_galaxy` | Search MISP galaxy clusters by name, synonym, or description |
| `search_taxonomy` | `mcp:search_taxonomy` | Search across all MISP taxonomies for matching tag values |
| `get_sightings` | `mcp:get_sightings` | Retrieve sighting records for an indicator value or attribute UUID |
| `get_sighting_activity` | `mcp:get_sightings` | Time-series sighting histogram for an indicator (activity over time) |
| `list_hunts` | `mcp:list_hunts` | List saved threat hunts, optionally filtered by name |
| `get_hunt_results` | `mcp:get_hunt_results` | Retrieve the latest cached results for a hunt |
| `get_hunt_history` | `mcp:get_hunt_history` | Run history (timestamps and match counts) for a hunt |
| `run_hunt` | `mcp:run_hunt` | Execute a hunt immediately and return matching hits |
| `get_event_reports` | `mcp:get_event_reports` | Get all reports attached to a specific event UUID |
| `search_event_reports` | `mcp:search_event_reports` | Full-text search across all event reports |
| `create_event_report` | `mcp:create_event_report` | Write a new Markdown report and attach it to an event |
| `enrich_indicator` | `mcp:enrich_indicator` | Enrich an indicator using a MISP expansion module (e.g. GeoIP, VirusTotal) |
| `list_modules` | `mcp:list_modules` | List available enrichment modules and their supported attribute types |
| `get_notifications` | `mcp:get_notifications` | Get platform notifications for the authenticated user |

### Search tools

`search_events` and `search_attributes` accept [Lucene query string syntax](https://opensearch.org/docs/latest/query-dsl/full-text/query-string/) and support field-targeted queries:

```
# Events
info:ransomware AND threat_level:3
tags.name:tlp\:white AND published:true
tags.name:misp-galaxy\:threat-actor\="Turla Group"

# Attributes
type:ip-src AND value:10.*
type:ip* AND expanded.ip2geo.country_iso_code:RU
type:sha256 AND to_ids:true
category:"Network activity" AND tags.name:tlp\:red
```

!!! tip "Discover fields first"
    Use `get_index_mapping` with `index="misp-events"` or `index="misp-attributes"` to see all available fields, including any GeoIP or ASN enrichment fields added by your ingest pipelines.

### Pagination

All search and list tools accept `page` (1-based) and `size` (default 10, capped at 100) parameters:

```
search_events(query="ransomware", page=2, size=20)
```

### Tag syntax

Tags come from two sources — escape the colon when searching:

| Source | Example tag | Query syntax |
|---|---|---|
| Taxonomy | `tlp:white` | `tags.name:tlp\:white` |
| Galaxy | `misp-galaxy:threat-actor="APT28"` | `tags.name:misp-galaxy\:threat-actor\="APT28"` |

Use `search_taxonomy` to find taxonomy tags by keyword, and `search_galaxy` to look up galaxy cluster entries by name or synonym.

### Enrichment

Before calling `enrich_indicator`, use `list_modules` to see which modules are enabled and what attribute types they accept:

```
list_modules(enabled_only=True)
→ [{"name": "mmdb_lookup", "input_types": ["ip-src", "ip-dst", ...], ...}]

enrich_indicator("8.8.8.8", "ip-dst", "mmdb_lookup")
enrich_indicator("8.8.8.8", "ip-dst", "geolocation")  # alias for mmdb_lookup
```

Module aliases resolved automatically: `geolocation`, `geoip`, `geo`, `ip2geo` → `mmdb_lookup`.


## Resources

Resources provide static reference data that the AI can read at any time.

| URI | Scope | Description |
|---|---|---|
| `misp://attribute-types` | `mcp:list_resources` | All MISP attribute types grouped by category (hashes, network, email, etc.) |
| `misp://attribute-categories` | `mcp:list_resources` | Valid MISP attribute categories |
| `misp://threat-levels` | `mcp:list_resources` | Threat level codes: 1=High, 2=Medium, 3=Low, 4=Undefined |
| `misp://analysis-levels` | `mcp:list_resources` | Analysis state codes: 0=Initial, 1=Ongoing, 2=Completed |
| `misp://distribution-levels` | `mcp:list_resources` | Distribution level codes and their meanings |
| `misp://query-syntax` | `mcp:list_resources` | Lucene query syntax cheat sheet for use with search tools |
| `misp://taxonomies` | `mcp:list_resources` | Index of all installed MISP taxonomy namespaces |
| `misp://galaxies` | `mcp:list_resources` | Index of all installed MISP galaxy types |


## Prompts

Prompts are reusable analysis templates. They guide the AI through a structured investigation workflow using the available tools.

| Prompt | Arguments | Description |
|---|---|---|
| `threat_report` | `keyword` | Summarize events, IOCs, correlations, and tags related to a keyword into a structured report |
| `ioc_lookup` | `value` | Detect type, search attributes, fetch parent events, check correlations, and summarize an IOC |
| `threat_actor_profile` | `name` | Build a full profile of a threat actor: events, IOCs, MITRE ATT&CK TTPs, and aliases |
| `country_exposure` | `country_code` | Analyze threat exposure for a country using GeoIP-enriched IP attributes |
| `daily_summary` | _(none)_ | Generate a daily intelligence briefing: stats, recent events, high-threat items |
| `enrich_indicator_prompt` | `value`, `module` | Enrich an indicator with a specific module and produce a concise enrichment report |


## Scopes reference

When `MCP_AUTH_ENABLED=true`, each request must carry a token with the appropriate scope. The `mcp:config` endpoint generates a token scoped to all `mcp:*` permissions granted to the user.

| Scope | Grants access to |
|---|---|
| `mcp:config` | Generate an MCP client configuration token |
| `mcp:list_tools` | List available tools (`tools/list`) |
| `mcp:list_resources` | List and read resources (`resources/list`, `resources/read`) |
| `mcp:list_prompts` | List and get prompts (`prompts/list`, `prompts/get`) |
| `mcp:search_events` | `search_events` tool |
| `mcp:search_attributes` | `search_attributes` tool |
| `mcp:get_event` | `get_event` tool |
| `mcp:get_correlations` | `get_correlations` tool |
| `mcp:detect_indicator_type` | `detect_indicator_type` tool |
| `mcp:get_statistics` | `get_statistics` tool |
| `mcp:get_tags` | `get_tags` tool |
| `mcp:get_index_mapping` | `get_index_mapping` tool |
| `mcp:search_galaxy` | `search_galaxy` tool |
| `mcp:search_taxonomy` | `search_taxonomy` tool |
| `mcp:get_sightings` | `get_sightings` and `get_sighting_activity` tools |
| `mcp:list_hunts` | `list_hunts` tool |
| `mcp:get_hunt_results` | `get_hunt_results` tool |
| `mcp:get_hunt_history` | `get_hunt_history` tool |
| `mcp:run_hunt` | `run_hunt` tool |
| `mcp:get_event_reports` | `get_event_reports` tool |
| `mcp:search_event_reports` | `search_event_reports` tool |
| `mcp:create_event_report` | `create_event_report` tool |
| `mcp:enrich_indicator` | `enrich_indicator` tool |
| `mcp:list_modules` | `list_modules` tool |
| `mcp:get_notifications` | `get_notifications` tool |

Users with the `perm_admin` role are granted `mcp:*` (all MCP scopes). Users with `perm_full` are granted `*` (unrestricted).
