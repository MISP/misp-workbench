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

### Documentation screenshots

Screenshots referenced from `docs/features/*.md` are captured by a Playwright
script in `frontend/scripts/docs-screenshots/`. The script logs in as a
fixture user, navigates each documented view, and writes PNGs directly into
`docs/screenshots/<feature>/`.

First-time setup:

```bash
cd frontend
npm install
npx playwright install chromium
```

Run against a running dev stack (`docker compose ... up`):

```bash
cd frontend
npm run docs:seed              # idempotent — creates fixture org/user/events/hunts
npm run docs:screenshots       # captures both light and dark themes
```

Each spec runs twice — once per Playwright project (`screenshots-light`,
`screenshots-dark`). Dark captures land alongside the light ones with a
`-dark` suffix, e.g. `misp-workbench-1_explore.png` +
`misp-workbench-1_explore-dark.png`.

Reference both variants from a docs page using the mkdocs-material
`#only-light` / `#only-dark` URL fragments — only the variant matching the
reader's selected palette renders:

```html
<img src="../../screenshots/explore/misp-workbench-1_explore.png#only-light">
<img src="../../screenshots/explore/misp-workbench-1_explore-dark.png#only-dark">
```

Other useful scripts:

| Script | Purpose |
|---|---|
| `npm run docs:screenshots:explore` | Capture only the Explore feature shots |
| `npm run docs:screenshots:hunts` | Capture only the Hunts feature shots |
| `npm run docs:screenshots:light` | Capture only the light variants |
| `npm run docs:screenshots:dark` | Capture only the dark variants |
| `npm run docs:screenshots:headed` | Watch the captures run in a visible browser |
| `npm run docs:seed:reset` | Wipe and re-create the fixture user's hunts (events/attributes are always re-timed) |

Filters compose — pass extra flags after `--`. For example, only the dark
Explore shots: `npm run docs:screenshots:explore -- --project=screenshots-dark`.

Events and attributes are re-timed on every seed run so they always sit
within the Explore view's default 30-day window.

Override the frontend URL with `DOCS_FRONTEND_URL=...` if the dev server is
on a non-default port.

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
