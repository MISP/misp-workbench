# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**misp-workbench** is a MISP-compatible threat intelligence platform. It provides event/attribute management, correlation, feed sync, and search without requiring a full MISP instance. It is a monorepo with a Python FastAPI backend and a Vue.js 3 frontend.

## Development Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.9+, FastAPI, SQLAlchemy 2.0, Alembic, Celery 5, Poetry |
| Frontend | Vue 3, Vite, Pinia, TypeScript, Bootstrap 5 |
| Database | PostgreSQL 16 |
| Search | OpenSearch 3 |
| Broker/Cache | Redis |
| Storage | MinIO (S3) or local filesystem |
| Task Monitor | Flower (port 5555) |

## Commands

### Start dev environment

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml --env-file=".env.dev" up --build
```

Copy `.env.dev.dist` to `.env.dev` and set required secrets before first run.

### Backend (run inside the `api` container)

```bash
# Run all tests
docker compose exec api poetry run pytest

# Run a single test file or test
docker compose exec api poetry run pytest tests/path/to/test_file.py::test_name

# Apply migrations
docker compose exec api poetry run alembic upgrade head

# Create a new migration
docker compose exec api poetry run alembic revision -m "description"

# CLI admin tools
docker compose exec api poetry run python -m app.cli --help
docker compose exec api poetry run python -m app.cli create-organisation <name>
docker compose exec api poetry run python -m app.cli create-user <email> <password> <org_id> <role_id>

# Pre-commit linting (black, flake8, isort, autoflake)
cd api && poetry run pre-commit run --all-files
```

### Frontend

```bash
cd frontend
npm install
npm run dev          # Dev server
npm run build        # Production build
npm run lint         # ESLint fix
npm run test:unit    # Vitest unit tests
npm run test:e2e     # Cypress interactive
npm run test:e2e:ci  # Cypress headless
```

## Architecture

### Backend (`api/`)

Layered architecture: **Router → Repository → SQLAlchemy Model → PostgreSQL**

- `app/routers/` — FastAPI route definitions, one file per resource (events, attributes, feeds, servers, correlations, tasks, etc.)
- `app/models/` — SQLAlchemy ORM models
- `app/repositories/` — Database access logic
- `app/schemas/` — Pydantic request/response models
- `app/auth/` — JWT OAuth2 authentication
- `app/dependencies.py` — FastAPI dependency injection (current user, permissions)
- `app/worker/tasks.py` — Celery async task definitions (server sync, feed ingestion, correlations, notifications)
- `app/cli.py` — Admin CLI commands

Background jobs are enqueued to Redis via Celery and scheduled by Celery Beat (redbeat scheduler).

### Frontend (`frontend/src/`)

Store-based component architecture:

- `views/` — Page-level components, organized by domain (`events/`, `attributes/`, `feeds/`, `servers/`, etc.)
- `stores/` — Pinia stores per domain; each store owns API communication and state
- `components/` — Shared reusable components
- `router/` — Vue Router SPA configuration
- `schemas/` — Yup validation schemas for forms
- `helpers/` — Utility functions

### Supporting Services (dev extras)

- **pgAdmin** — PostgreSQL GUI
- **MailHog** — Email capture for testing
- **Redis Commander** — Redis GUI
- **OpenSearch Dashboards** (port 5601)

## Remote Debugging (VS Code)

Debug configurations are in `.vscode/launch.json`:

| Target | Port |
|---|---|
| API | 5678 |
| Celery Worker | 5679 |
| Celery Beat | 5680 |
| Test runner | 5677 |

To debug tests: `docker compose exec api poetry run python -m debugpy --listen 0.0.0.0:5677 --wait-for-client -m pytest`

## Code Style

**Python** (enforced by pre-commit):
- `black` formatter
- `flake8` (ignores E501, W503, E203)
- `isort` (black profile)
- `pyupgrade` targeting Python 3.9+

**Frontend**: ESLint with Vue/TypeScript plugins + Prettier via Husky pre-commit hooks.

## Key Env Variables

See `.env.dev.dist` for the full list. Required secrets to set:
- `OAUTH2_SECRET_KEY` / `OAUTH2_REFRESH_SECRET_KEY`
- Database credentials
- MinIO credentials (if `STORAGE_ENGINE=minio`)

## CI

GitHub Actions (`.github/workflows/api_test.yml`) runs on PRs: migrations → pytest with full service stack (PostgreSQL, OpenSearch, Redis).
