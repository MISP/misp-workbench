# Features

| Feature | Description |
|---|---|
| [Feed ingestion](feeds/index.md) | Ingest MISP, CSV, JSON, and Freetext feeds on a schedule or on demand |
| [Explore](explore.md) | Lucene queries against OpenSearch for fast indicator lookups |
| [Hunt](hunts.md) | Hunts are saved searches that run periodically and trigger alerts. |
| [Exports](exports.md) | Scheduled file exports in JSON, CSV, MISP, STIX 2.1, NDJSON, plain text or Wazuh CDB, including incremental feeds that SIEMs poll for changes |
| [Sinks](sinks.md) | Push published indicators to SIEMs and other tools: Splunk HEC, Graylog GELF, syslog/CEF or webhooks, with per-sink filters and delivery status |
| [Sightings](sightings.md) | Record where indicators were seen or proved benign, in bulk or through MISP's `/sightings/add`, with optional false-positive feedback |
| [Warninglists](warninglists.md) | MISP warninglists flag benign or overly common values (public resolvers, top domains, private ranges) and keep them out of exports, feeds, sinks and lookups |
| [Correlations](correlations.md) | Batch and incremental correlation scans over indexed attributes |
| [Event Graph](event-graph.md) | Draw an event as a graph: its attributes, objects, tags and the references between them |
| [Notifications](notifications.md) | Event-driven notifications processed by Celery workers. |
| [Enrichments](enrichments.md) | IOC enrichment powered by [misp-modules](https://github.com/MISP/misp-modules) |
| [Analyst Data](analyst-data.md) | MISP analyst notes, opinions and relationships on events, attributes and objects |
| [MCP Server](mcp/index.md) | AI assistant integration via the Model Context Protocol — query threat intel from Claude, Cursor, etc. |
| [Batch Import](batch-import.md) | Easily import a list of indicators and add them as attributes to an event in a single operation. |
| [Retention](retention.md) | Configurable event retention period with automatic purge of expired events |
| [Reactor Scripts](tech-lab/reactor.md) | User-defined Python scripts that react to platform events (event/attribute/object/correlation/sighting) and run in an isolated sandbox |
| [Notebooks](tech-lab/notebooks.md) | Interactive analyst notebooks with a pre-imported SDK (`mwlab`) for ad-hoc exploration of events, attributes, correlations, and enrichments |
| [Transformation Servos](tech-lab/servos.md) | User-authored OpenSearch ingest pipelines that normalise, parse and enrich attributes as they are indexed |
| [OpenSearch](opensearch/index.md) | Full-text search, dashboards, and ingestion pipelines |
| [REST API](api/index.md) | FastAPI backend with automatic OpenAPI documentation |
| [API keys](api/api-keys.md) | Long-lived, scoped, MISP-compatible keys for integrations, with a SIEM integration preset |
| [MISP restSearch](api/rest-search.md) | MISP-compatible `restSearch` for attributes and events, so existing MISP integrations work unmodified |
| [Streaming exports](api/streaming-exports.md) | Streamed, incremental attribute and event exports with conditional requests, for SIEMs pulling indicator sets |
| [Bulk lookup](api/lookup.md) | Check up to 10,000 values per request for known indicators, with a Redis prefilter that keeps misses cheap |
| [Audit logs](api/audit-logs.md) | Append-only record of security-relevant actions, for incident response |
| **Storage** | Garage (S3-compatible) or local filesystem for attachments |
