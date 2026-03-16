# Ingest Pipelines

Ingest pipelines process documents as they are indexed into OpenSearch. misp-workbench uses a chain of pipelines to extract and enrich IP address data in the `misp-attributes` index.

## Pipeline chain

The `misp-attributes` index template attaches two pipelines:

- **Default pipeline** (`misp-attributes_default`) — runs before the document is stored
- **Final pipeline** (`misp-attributes_final`) — runs after the default pipeline completes

Each pipeline delegates to the next step in the chain:

```
Document indexed into misp-attributes
        │
        ▼
misp-attributes_default (default pipeline)
        │  calls ▼
misp-attributes_ip_extraction
   Extracts IP from ip-src / ip-dst attributes
   → expanded.ip (single IP)
   → expanded.ip_range (CIDR notation)
        │
        ▼
misp-attributes_final (final pipeline)
        │  calls ▼
misp-attributes_ip_geoip
   Enriches expanded.ip with GeoIP data
   → expanded.ip2geo (city, country, coordinates, …)
```

## Pipeline details

### misp-attributes_default

Entry point. Delegates to the IP extraction pipeline.

```json
{
  "description": "Normalization pipeline wrapper",
  "processors": [
    { "pipeline": { "name": "misp-attributes_ip_extraction" } }
  ]
}
```

### misp-attributes_ip_extraction

A Painless script that runs for `ip-src` and `ip-dst` attribute types:

- If the value contains `/` (CIDR notation), it is stored in `expanded.ip_range` as an `ip_range` field
- Otherwise, the value is stored in `expanded.ip` as an `ip` field

This enables native IP range queries and aggregations in OpenSearch.

```json
{
  "description": "Extract IP addresses from specific types and store in expanded.ip",
  "processors": [
    {
      "script": {
        "lang": "painless",
        "source": "if (ctx.type == 'ip-src' || ctx.type == 'ip-dst') { if (ctx.expanded == null) { ctx.expanded = new HashMap(); } if (ctx.value.contains('/')) { ctx.expanded.ip_range = ctx.value; } else { ctx.expanded.ip = ctx.value; } }",
        "ignore_failure": true
      }
    }
  ]
}
```

### misp-attributes_ip_geoip

Uses OpenSearch's built-in [GeoIP processor](https://opensearch.org/docs/latest/ingest-pipelines/processors/ip2geo/) to enrich `expanded.ip` with geographic data. The result is stored in `expanded.ip2geo` with fields like `country_name`, `city_name`, `location` (geo_point), and `region_name`.

```json
{
  "description": "Enrich IP with GeoIP",
  "processors": [
    {
      "geoip": {
        "field": "expanded.ip",
        "target_field": "expanded.ip2geo",
        "ignore_missing": true,
        "ignore_failure": true
      }
    }
  ]
}
```

### misp-attributes_final

Exit point. Delegates to the GeoIP enrichment pipeline.

```json
{
  "description": "Enrichments pipeline wrapper",
  "processors": [
    { "pipeline": { "name": "misp-attributes_ip_geoip" } }
  ]
}
```

## Index template

The pipeline chain is wired via an index template that matches the `misp-attributes` index:

```json
{
  "index_patterns": ["misp-attributes"],
  "template": {
    "settings": {
      "index.default_pipeline": "misp-attributes_default",
      "index.final_pipeline": "misp-attributes_final"
    }
  },
  "priority": 100
}
```

This ensures every document written to `misp-attributes` passes through both pipelines automatically.

## Pipeline files

All pipeline definitions are stored in the repository and applied on startup:

| File | Pipeline |
|---|---|
| `opensearch/pipelines/misp-attributes_default.json` | Default entry point |
| `opensearch/pipelines/misp-attributes_ip_extraction.json` | IP extraction script |
| `opensearch/pipelines/misp-attributes_ip_geoip.json` | GeoIP enrichment |
| `opensearch/pipelines/misp-attributes_final.json` | Final exit point |
| `opensearch/index-templates/misp-attributes-template.json` | Index template wiring |
