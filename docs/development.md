# Development Guide

## Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.9+, FastAPI, SQLAlchemy 2.0, Alembic, Celery 5, Poetry |
| Frontend | Vue 3, Vite, Pinia, TypeScript, Bootstrap 5 |
| Database | PostgreSQL 16 |
| Search | OpenSearch 3 |
| Broker / Cache | Redis |
| Storage | Garage (S3) or local filesystem |
| Task monitor | Flower (port 5555) |

## Backend

### Running tests

```bash
# All tests
docker compose exec api poetry run pytest

# Single file or test
docker compose exec api poetry run pytest tests/path/to/test_file.py::TestClass::test_name
```

### Database migrations

```bash
# Apply pending migrations
docker compose exec api poetry run alembic upgrade head

# Create a new migration
docker compose exec api poetry run alembic revision -m "description"
```

### Linting

```bash
cd api && poetry run pre-commit run --all-files
```

Pre-commit hooks run: `black`, `flake8` (ignores E501, W503, E203), `isort` (black profile), `pyupgrade` (Python 3.9+).

### Remote debugging (VS Code)

Attach to the running container using the configurations in `.vscode/launch.json`:

| Target | Port |
|---|---|
| API | 5678 |
| Celery Worker | 5679 |
| Celery Beat | 5680 |
| Test runner | 5677 |

To debug tests:

```bash
docker compose exec api poetry run python -m debugpy --listen 0.0.0.0:5677 --wait-for-client -m pytest
```

## Frontend

### Dev server

```bash
cd frontend
npm install
npm run dev
```

### Tests

```bash
npm run test:unit    # Vitest unit tests
npm run test:e2e     # Cypress interactive
npm run test:e2e:ci  # Cypress headless
```

### Linting

```bash
npm run lint    # ESLint fix
```

## Code conventions

### Backend

- One router file per resource in `app/routers/`
- Business logic in `app/repositories/`, not in routers
- Static routes (e.g. `/feeds/defaults`) must be declared **before** parameterised routes (e.g. `/feeds/{feed_id}`)
- Celery tasks in `app/worker/tasks.py`; import repositories there, not the other way around (avoid circular imports)

### Frontend

- One Pinia store per domain in `stores/`; each store owns its API calls
- Page-level components in `views/`, reusable components in `components/`
- Emit `{ ...props.modelValue, ...changes }` from child components to avoid overwriting parent state

## CI

GitHub Actions runs on every pull request (`.github/workflows/api_test.yml`):

1. Start PostgreSQL, OpenSearch, Redis
2. Run Alembic migrations
3. Run `pytest` with coverage reporting to Codecov
