# Features

| Feature | Description |
|---|---|
| [Feed ingestion](feeds/index.md) | Ingest MISP, CSV, JSON, and Freetext feeds on a schedule or on demand |
| [Correlations](correlations.md) | Batch and incremental correlation scans over indexed attributes |
| [Explore](explore.md) | Lucene queries against OpenSearch for fast indicator lookups |
| [Enrichments](enrichments.md) | IOC enrichment powered by [misp-modules](https://github.com/MISP/misp-modules) |
| [Hunt](hunts.md) | Hunts are saved searches that run periodically and trigger alerts. |
| [Notifications](notifications.md) | Event-driven notifications processed by Celery workers |
| [Batch Import](batch-import.md) | Easily import a list of indicators and add them as attributes to an event in a single operation. |
| [OpenSearch](opensearch/index.md) | Full-text search, dashboards, and ingestion pipelines |
| **REST API** | FastAPI backend with automatic OpenAPI documentation |
| **Storage** | Garage (S3-compatible) or local filesystem for attachments |
