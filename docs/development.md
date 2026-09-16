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
docker compose exec -e ENVIRONMENT=test api poetry run pytest

# Single file or test
docker compose exec -e ENVIRONMENT=test api poetry run pytest tests/path/to/test_file.py::TestClass::test_name
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

## Seeding a demo instance

`seed-demo` fills an empty instance with a coherent dataset you can walk
through live, without hand-building events mid-presentation:

```bash
docker compose exec api poetry run python -m app.cli seed-demo
```

It layers on top of `seed-docs-fixtures` (the events, attributes, objects,
hunts and audit rows behind the documentation screenshots) and adds the parts
the screenshot suite fakes with Playwright route stubs, which therefore never
reach the database:

| Seeded | What you get |
|---|---|
| Events + attributes | Two extra events whose indicators deliberately overlap the docs fixtures |
| Correlations | Generated from that overlap, so the correlation views and notifications populate themselves |
| Servos | The four shipped templates, two of them enabled |
| Reactor scripts | One active, one paused |
| Analyst data | Notes, opinions and a relationship across the fixture events and attributes |
| Event report | A Markdown incident write-up on the Emotet event |
| Feeds | Three well-known OSINT feed definitions, **all disabled** |
| Notebooks | The Tech Lab library notebooks from `api/lab_library/` |
| Hunt run history | ~90 days of daily runs per hunt, so the heatmap and sparkline are populated |
| Hunt results | Each hunt is executed once, so the results table is populated too |
| Notifications | One of every kind the notification list knows how to render |

### Hunt history and the 90-row limit

`hunts_repository.get_hunt_history` returns the **oldest** 90 rows
(`order_by(run_at.asc()).limit(90)`) and caches them in Redis. So a hunt with
more than 90 stored runs draws a heatmap of the wrong end of the window — the
recent months come out blank.

The fixtures therefore seed at most one run per day. `seed-demo` warns if a
fixture would exceed the limit, and clears each hunt's `hunt:history:*` and
`hunt:results:*` Redis keys as it reseeds, so a refreshed demo is not served
the previous seed from cache.

!!! warning "Do not seed the demo before capturing docs screenshots"
    `seed-demo` is additive, and `seed-docs-fixtures` does not remove events it
    did not create — so demo events stay in the index and turn up in the
    documentation captures. Regenerate screenshots on an instance that has only
    ever had `seed-docs-fixtures` run against it.

    A related side effect worth knowing: seeding attributes fires the seeded
    reactor script, so demo events pick up a `workflow:state="triage"` tag on
    their own. That is the reactor genuinely working, not stray fixture data.

### Results come from a real run

Synthetic history gives the chart its shape, but the results table reads
`hunt:results:<id>` in Redis, which only an actual run writes. So `seed-demo`
executes each hunt once after seeding the history — the newest point on the
chart is a real run with real hits behind it, rather than a populated chart
sitting above an empty table.

Two consequences worth knowing:

- Running a hunt `rpush`es onto the history key the seeder just cleared, which
  would leave a cache holding that single run. The seeder rebuilds the list
  from the newest rows afterwards.
- The `cpe` and `rulezet` hunts reach external services. Those are allowed to
  fail and are reported as *unavailable*, so the demo still comes up on a
  machine with no outbound network.

Run counts come out lower than `days` where `quiet_weekends` is set — a hunt
that matches nothing at the weekend reads as a real schedule rather than a
flat block of colour. The shape (cadence, baseline, jitter, spikes) is
described in `hunt_history.json` and expanded by the seeder from a fixed RNG
seed, so the heatmap is identical on every machine and every run — a demo that
looks different each time is a demo you cannot rehearse.

The overlapping indicators are the point: a demo of correlations, of the event
graph, or of a servo transforming a value needs data that actually relates to
other data, which is exactly what a screenshot stub cannot give you.

### It is additive

Everything is keyed by a pinned UUID or by an exact name, so re-running
refreshes the demo in place and leaves the rest of the instance alone. Nothing
is deleted that the seeder did not create.

`--reset` removes the demo's own rows before re-creating them — matched by
pinned UUID or exact fixture name, so a servo, feed or reactor script you made
by hand survives even if it covers the same subject.

| Flag | Effect |
|---|---|
| `--reset` | Delete and re-create the demo's own rows |
| `--skip-docs` | Do not run `seed-docs-fixtures` first |
| `--skip-correlations` | Do not run the correlation engine afterwards |
| `--fixtures-dir` | Read demo fixtures from elsewhere |
| `--notebooks-dir` | Read library notebooks from elsewhere |

Correlation generation here calls `run_correlations` directly, which writes
with `op_type=create` and never deletes — unlike the scheduled
`generate_correlations` task, which wipes the correlation index first.

Feeds are seeded **disabled**. A demo should choose when to pull, and a fetch
reaches the network and brings back whatever is live that day, which is the
opposite of what fixture data is for.

Log in with `admin@admin.test` / `admin`.

Fixtures live in `api/app/fixtures/demo/`. Servos reference the shipped
templates by slug rather than copying their processors, so editing a template
reaches the demo automatically instead of leaving two copies to drift apart.
