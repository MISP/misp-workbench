# Configuration

All configuration is supplied through environment variables. Copy `.env.dev.dist` (development) or `.env.dist` (production) and fill in your values.

## Required secrets

These must be set before first run.

| Variable | Description |
|---|---|
| `OAUTH2_SECRET_KEY` | Secret key for signing access tokens (64-char hex recommended) |
| `OAUTH2_REFRESH_SECRET_KEY` | Secret key for signing refresh tokens |

## Database

| Variable | Default | Description |
|---|---|---|
| `POSTGRES_HOSTNAME` | `postgres` | PostgreSQL host |
| `POSTGRES_PORT` | `5432` | PostgreSQL port |
| `POSTGRES_USER` | `postgres` | Database user |
| `POSTGRES_PASSWORD` | — | Database password |
| `POSTGRES_DB` | `misp` | Database name |

## Redis

| Variable | Default | Description |
|---|---|---|
| `REDIS_HOSTNAME` | `redis` | Redis host |
| `REDIS_PORT` | `6379` | Redis port |
| `REDIS_CELERY_DB` | `0` | Redis DB index for Celery broker |
| `REDIS_CACHE_DB` | `5` | Redis DB index for cache/notifications |

## OpenSearch

| Variable | Default | Description |
|---|---|---|
| `OPENSEARCH_HOSTNAME` | `opensearch` | OpenSearch host |
| `OPENSEARCH_PORT` | `9200` | OpenSearch port |
| `OPENSEARCH_INITIAL_ADMIN_PASSWORD` | — | Admin password (required on first start) |

## Authentication (JWT)

| Variable | Default | Description |
|---|---|---|
| `OAUTH2_ALGORITHM` | `HS256` | JWT signing algorithm |
| `OAUTH2_ACCESS_TOKEN_EXPIRE_MINUTES` | `300` | Access token lifetime in minutes |
| `OAUTH2_REFRESH_TOKEN_EXPIRE_DAYS` | `7` | Refresh token lifetime in days |

## Storage

| Variable | Default | Description |
|---|---|---|
| `STORAGE_ENGINE` | `local` | `local` or `s3` |
| `S3_ENDPOINT` | `garage:3900` | S3 / Garage endpoint |
| `S3_ACCESS_KEY` | _(auto)_ | S3 access key — leave unset to let Garage generate one automatically |
| `S3_SECRET_KEY` | _(auto)_ | S3 secret key — leave unset to let Garage generate one automatically |
| `S3_CREDS_FILE` | `/var/lib/misp-workbench/secrets/s3.json` | Path where auto-generated credentials are persisted |
| `S3_BUCKET` | `attachments` | S3 bucket name |
| `S3_SECURE` | `false` | Use TLS for S3 connection |

## Garage (S3-compatible storage)

| Variable | Default | Description |
|---|---|---|
| `GARAGE_ADMIN_URL` | `http://garage:3903` | Garage admin API URL |
| `GARAGE_ADMIN_TOKEN` | — | Garage admin token |
| `GARAGE_METRICS_TOKEN` | — | Garage metrics token |

## Mail

| Variable | Default | Description |
|---|---|---|
| `MAIL_SERVER` | `mailhog` | SMTP server host |
| `MAIL_PORT` | `1025` | SMTP port |
| `MAIL_USERNAME` | — | SMTP username |
| `MAIL_PASSWORD` | — | SMTP password |

## Task monitoring (Flower)

| Variable | Default | Description |
|---|---|---|
| `FLOWER_BASIC_AUTH` | `flower:flower` | `user:password` for Flower UI |
| `FLOWER_URL` | `http://flower:5555/` | Internal Flower API URL used by the backend |

## MISP Modules

| Variable | Default | Description |
|---|---|---|
| `MODULES_HOST` | `modules` | MISP modules service host |
| `MODULES_PORT` | `6666` | MISP modules service port |
