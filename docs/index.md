# misp-workbench

![misp-workbench](images/misp-workbench-hori-color.jpg)

A modern MISP-compatible threat intelligence platform. It provides a self-contained solution for ingesting, correlating, and analysing threat intelligence data — without requiring a full MISP instance.

## Features

| Feature | Description |
|---|---|
| [Feed ingestion](features/feeds/index.md) | Ingest MISP, CSV, JSON, and Freetext feeds on a schedule or on demand |
| [Correlations](features/correlations.md) | Batch and incremental correlation scans over indexed attributes |
| [Explore](features/explore.md) | Lucene queries against OpenSearch for fast indicator lookups |
| [Enrichments](features/enrichments.md) | IOC enrichment powered by [misp-modules](https://github.com/MISP/misp-modules) |
| [MCP Server](features/mcp/index.md) | AI assistant integration via the Model Context Protocol — query threat intel from Claude, Cursor, etc. |
| [Hunt](features/hunts.md) | Hunts are saved searches that run periodically and trigger alerts. |
| [Notifications](features/notifications.md) | Event-driven notifications processed by Celery workers |
| [Batch Import](features/batch-import.md) | Easily import a list of indicators and add them as attributes to an event in a single operation. |
| [Retention](features/retention.md) | Configurable event retention period with automatic purge of expired events |
| [Reactor Scripts](features/tech-lab/reactor.md) | User-defined Python scripts that react to platform events and run in an isolated sandbox |
| [OpenSearch](features/opensearch/index.md) | Full-text search, dashboards, and ingestion pipelines |
| [REST API](features/api/index.md) | FastAPI backend with automatic OpenAPI documentation |
| **Storage** | Garage (S3-compatible) or local filesystem for attachments |

## Screenshots

=== "Explore"
    Browse and search MISP events and attributes using Lucene queries.

    ![Explore](screenshots/misp-workbench-explore-view.png)

=== "Hunts"
    Define saved searches to proactively hunt for indicators of interest.

    ![Hunts](screenshots/misp-workbench-hunts-view.png)

=== "Sources"
    Manage feed sources: JSON, CSV, Freetext and MISP.

    ![Sources](screenshots/misp-workbench-json-feeds-view.png)

## Quick links

- [Getting Started](getting-started.md)
- [Features](features/index.md)
- [Configuration reference](configuration.md)
- [Architecture overview](architecture.md)
- [Development guide](development.md)
