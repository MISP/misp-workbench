# Architecture

## Overview

misp-workbench is a monorepo composed of a Python FastAPI backend and a Vue.js 3 frontend, wired together via Docker Compose.

```
┌─────────────────────────────────────────────────────────────┐
│                        Browser                              │
│                    Vue.js 3 frontend                        │
│               (Vite, Pinia, Bootstrap 5)                    │
└──────────────────────┬──────────────────────────────────────┘
                       │ REST / JSON
┌──────────────────────▼──────────────────────────────────────┐
│                   FastAPI backend                           │
│            Routers → Repositories → Models                  │
└────┬────────────────┬───────────────┬───────────────┬───────┘
     │                │               │               │
┌────▼─────┐   ┌──────▼──────┐  ┌─────▼─────┐  ┌──────▼──────┐
│PostgreSQL│   │ OpenSearch  │  │   Redis   │  │  Garage/S3  │
│ (ORM)    │   │ (indexing)  │  │ (broker / │  │(attachments)│
│          │   │             │  │  cache)   │  │             │
└──────────┘   └─────────────┘  └─────┬─────┘  └─────────────┘
                                      │
                               ┌──────▼──────┐
                               │   Celery    │
                               │   workers   │
                               └─────────────┘
```

## Backend (`api/`)

Layered architecture: **Router → Repository → SQLAlchemy Model → PostgreSQL**

| Layer | Path | Responsibility |
|---|---|---|
| Routers | `app/routers/` | FastAPI route definitions, one file per resource |
| Repositories | `app/repositories/` | Business logic and database access |
| Models | `app/models/` | SQLAlchemy ORM models |
| Schemas | `app/schemas/` | Pydantic request/response validation |
| Auth | `app/auth/` | JWT OAuth2 authentication |
| Worker | `app/worker/tasks.py` | Celery async task definitions |
| CLI | `app/cli.py` | Admin CLI commands |

### Background tasks

Celery is used for all long-running operations:

- Feed fetching (MISP, CSV, JSON, Freetext)
- Correlation generation
- OpenSearch indexing
- Notifications

Tasks are scheduled via **RedBeat** (Redis-backed Celery Beat scheduler) and monitored via **Flower** on port 5555.

Tasks are spread over queues, each consumed by its own worker, so that one kind of work can't hold up the others:

| Queue | Worker | Work |
|---|---|---|
| `celery` (default), `maintenance` | `worker` | User-triggered work; periodic jobs and rebuilds |
| `ingest` | `ingest-worker` | Feed fetches, server pulls and pushes, bulk-ingest correlation and notification follow-ups |
| `sinks` | `sinks-worker` | Deliveries to outbound sinks |
| `reactor_sandbox` | `reactor-worker` | Reactor scripts |
| `lab_kernel` | `lab-worker` | Tech Lab notebook kernels |

Feed fetches and server pulls are bounded [ingestion runs](features/feeds/index.md#ingestion-runs).

### Authentication

JWT-based OAuth2 with scoped tokens. Each endpoint declares required scopes (e.g. `feeds:read`, `feeds:fetch`). Tokens are issued by `POST /auth/token`.

## Frontend (`frontend/src/`)

Store-based component architecture built on Pinia.

| Layer | Path | Responsibility |
|---|---|---|
| Views | `views/` | Page-level components, one per domain |
| Stores | `stores/` | Pinia stores; own API calls and state |
| Components | `components/` | Shared reusable UI components |
| Router | `router/` | Vue Router SPA configuration |
| Schemas | `schemas/` | Yup validation schemas for forms |
| Helpers | `helpers/` | Utility functions (fetchWrapper, etc.) |

## Data flow: feed ingestion

```
User clicks "Fetch"
      │
      ▼
POST /feeds/{id}/fetch  (API)
      │
      ▼
Celery task enqueued  (Redis broker)
      │
      ▼
Worker: fetch_csv_feed / fetch_json_feed / fetch_freetext_feed / fetch_feed
      │
      ├── Fetch remote content (HTTP)
      ├── Parse rows / items
      ├── Create Attribute records  (PostgreSQL)
      └── index_event.delay()  →  OpenSearch
```

## Service ports (development)

| Service | Port |
|---|---|
| Frontend (Vite) | 3000 |
| API (Uvicorn) | 8000 |
| PostgreSQL | 5432 |
| Redis | 6379 |
| OpenSearch | 9200 |
| OpenSearch Dashboards | 5601 |
| Flower | 5555 |
| pgAdmin | 5050 |
| Redis Commander | 8081 |
| MailHog SMTP | 1025 |
| MailHog UI | 8025 |
