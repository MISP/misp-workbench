# OpenSearch

misp-workbench uses [OpenSearch](https://opensearch.org/) as its search and analytics engine. All events, attributes, objects, correlations, sightings, and event reports are indexed so they can be queried through the [Explore](../explore.md) view and used by [Correlations](../correlations.md) and [Hunts](../hunts.md).

## Indices

The following indices are created automatically on first startup:

| Index | Description |
|---|---|
| `misp-attributes` | Threat indicators with type, category, value, and GeoIP-enriched fields |
| `misp-events` | Event metadata including tags, threat level, analysis state |
| `misp-objects` | MISP objects with references and template information |
| `misp-attribute-correlations` | Correlation results linking attributes across events |
| `misp-sightings` | Sighting records with observer and metadata |
| `misp-event-reports` | Event report content and distribution |

### Attribute index enrichments

The `misp-attributes` index has an `expanded` field populated by [ingest pipelines](ingest-pipelines.md):

| Field | Type | Description |
|---|---|---|
| `expanded.ip` | `ip` | Parsed IP address for `ip-src` and `ip-dst` attributes |
| `expanded.ip_range` | `ip_range` | CIDR range for attributes containing `/` notation |
| `expanded.ip2geo.country_name` | `text` | GeoIP country |
| `expanded.ip2geo.city_name` | `text` | GeoIP city |
| `expanded.ip2geo.location` | `geo_point` | Latitude/longitude for map visualizations |
| `expanded.ip2geo.continent_name` | `text` | GeoIP continent |
| `expanded.ip2geo.region_name` | `text` | GeoIP region |
| `expanded.ip2geo.country_iso_code` | `text` | ISO country code |

## How data gets indexed

Data flows into OpenSearch through Celery background tasks:

```
Event/attribute created or updated
        │
        ▼
  Celery task indexes document
        │
        ▼
  Ingest pipelines enrich the document (attributes only)
        │
        ▼
  Document stored in the appropriate index
```

Correlation generation also runs as a Celery task and writes results to the `misp-attribute-correlations` index.

## Bootstrap

On first startup, an init container (`opensearch/entrypoint.sh`) sets up the cluster:

1. **Ingest pipelines** — creates the attribute enrichment pipeline chain
2. **Index templates** — applies default and final pipeline settings to `misp-attributes`
3. **Indices** — creates all indices with their field mappings
4. **Saved objects** — imports index patterns, visualizations, and [dashboards](dashboards.md) into OpenSearch Dashboards

Existing resources are skipped so the bootstrap is idempotent.

## Configuration

| Variable | Default | Description |
|---|---|---|
| `OPENSEARCH_HOSTNAME` | `opensearch` | OpenSearch host |
| `OPENSEARCH_PORT` | `9200` | OpenSearch HTTP port |
| `OPENSEARCH_INITIAL_ADMIN_PASSWORD` | — | Admin password for the cluster |
| `OPENSEARCH_DASHBOARDS_PASSWORD` | — | Service user password for Dashboards (prod only) |
| `OPENSEARCH_DASHBOARDS_PORT` | `5601` | Dashboards UI port |

## Diagnostics

The **Diagnostics** page in the UI shows an OpenSearch health card with:

- **Cluster** — status (green/yellow/red), node count, active and unassigned shards
- **Nodes** — per-node CPU, JVM heap, OS memory, and disk usage
- **Indices** — document counts, deleted docs, and store size per index
- **Shards** — shard allocation, type (primary/replica), state, and unassigned reasons
