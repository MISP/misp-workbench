# misp-workbench

<img src="./images/misp-workbench-verti-color.svg#only-light">
<img src="./images/misp-workbench-verti-white.svg#only-dark">

A modern MISP-compatible threat intelligence platform. It provides a self-contained solution for ingesting, correlating, and analysing threat intelligence data — without requiring a full MISP instance.

## Features

| Feature | Description |
|---|---|
| [Feed ingestion](features/feeds/index.md) | Ingest MISP, CSV, JSON, and Freetext feeds on a schedule or on demand |
| [Correlations](features/correlations.md) | Batch and incremental correlation scans over indexed attributes |
| [Explore](features/explore.md) | Lucene queries against OpenSearch for fast indicator lookups |
| [Exports](features/exports.md) | File based exports in JSON, CSV or STIX 2.1 format |
| [Enrichments](features/enrichments.md) | IOC enrichment powered by [misp-modules](https://github.com/MISP/misp-modules) |
| [MCP Server](features/mcp/index.md) | AI assistant integration via the Model Context Protocol — query threat intel from Claude, Cursor, etc. |
| [Hunt](features/hunts.md) | Hunts are saved searches that run periodically and trigger alerts. |
| [Notifications](features/notifications.md) | Event-driven notifications processed by Celery workers |
| [Batch Import](features/batch-import.md) | Easily import a list of indicators and add them as attributes to an event in a single operation. |
| [Retention](features/retention.md) | Configurable event retention period with automatic purge of expired events |
| [Reactor Scripts](features/tech-lab/reactor.md) | User-defined Python scripts that react to platform events and run in an isolated sandbox |
| [Notebooks](features/tech-lab/notebooks.md) | Interactive analyst notebooks with a pre-imported SDK (`mwlab`) for ad-hoc exploration of events, attributes, correlations, and enrichments |
| [OpenSearch](features/opensearch/index.md) | Full-text search, dashboards, and ingestion pipelines |
| [REST API](features/api/index.md) | FastAPI backend with automatic OpenAPI documentation |
| **Storage** | Garage (S3-compatible) or local filesystem for attachments |

## Quick links

- [Getting Started](getting-started.md)
- [Features](features/index.md)
- [Configuration reference](configuration.md)
- [Architecture overview](architecture.md)
- [Development guide](development.md)
