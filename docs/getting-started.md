# Getting Started

## Prerequisites

- Docker and Docker Compose
- Git

## Development setup

### 1. Clone and configure

```bash
git clone https://github.com/MISP/misp-workbench.git
cd misp-workbench
git submodule update --init --remote --recursive

cp .env.dev.dist .env.dev
cp frontend/.env.dist frontend/.env
```

Edit `.env.dev` and set at minimum:

- `OAUTH2_SECRET_KEY` — any random 64-character hex string
- `OAUTH2_REFRESH_SECRET_KEY` — another random 64-character hex string
- `OPENSEARCH_INITIAL_ADMIN_PASSWORD` — a strong password for OpenSearch

### 2. Start the stack

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml --env-file=".env.dev" up --build
```

Services started by the dev compose file:

| Service | URL |
|---|---|
| Frontend | http://localhost:3000 |
| API | http://localhost:8000 |
| API docs (Swagger) | http://localhost:8000/docs |
| Flower (task monitor) | http://localhost:5555 |
| pgAdmin | http://localhost:5050 |
| Redis Commander | http://localhost:8081 |
| OpenSearch Dashboards | http://localhost:5601 |
| MailHog | http://localhost:8025 |

### 3. Create an organisation and admin user

```bash
docker compose exec api poetry run python -m app.cli create-organisation "My Org"
# note the organisation ID printed
docker compose exec api poetry run python -m app.cli create-user admin@example.com password <org_id> 1
```

Alternatively, use the default credentials `admin@admin.test` / `admin` if they were seeded.

### 4. Login

Open http://localhost:3000/login and log in with your credentials.

---

## Production setup

### 1. Configure environment

```bash
cp .env.dist .env
# Edit .env and set all required secrets (see Configuration reference)

cp frontend/.env.dist frontend/.env
# Edit frontend/.env and set VITE_API_URL to the API public URL
# e.g. VITE_API_URL=https://api.your-domain.com
```

### 2. Configure storage (Garage/S3)

```bash
cp garage.toml.dist garage.toml
# Set rpc_secret (64 hex chars) and admin_token in garage.toml
```

Or set `STORAGE_ENGINE=local` in `.env` to use local filesystem storage instead.

### 3. Start the stack

```bash
docker compose --env-file=".env" up --build
```

---

## Running migrations

```bash
docker compose exec api poetry run alembic upgrade head
```

## CLI reference

```bash
docker compose exec api poetry run python -m app.cli --help
```

Available commands:

| Command | Description |
|---|---|
| `create-organisation <name>` | Create a new organisation |
| `create-user <email> <pass> <org_id> <role_id>` | Create a new user |
