# Configuration

All configuration is supplied through environment variables. Copy `.env.dev.dist` (development) or `.env.dist` (production) and fill in your values.

## Auto-generated secrets

The following secrets are **automatically generated** on first boot if left unset. They are persisted to a shared Docker volume so they survive container restarts.

| Variable | Default | Description |
|---|---|---|
| `OAUTH2_SECRET_KEY` | _(auto)_ | Secret key for signing access tokens — leave unset to auto-generate |
| `OAUTH2_REFRESH_SECRET_KEY` | _(auto)_ | Secret key for signing refresh tokens — leave unset to auto-generate |
| `OAUTH2_CREDS_FILE` | `/var/lib/misp-workbench/oauth-creds/oauth2.json` | Path where auto-generated OAuth2 secrets are persisted |

When `OAUTH2_SECRET_KEY` / `OAUTH2_REFRESH_SECRET_KEY` are not set, the entrypoint generates random 256-bit hex keys and writes them to `OAUTH2_CREDS_FILE`:

```json
{
  "secret_key": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
  "refresh_secret_key": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
}
```

The file is written with mode `0600`. It is read at startup by the API, worker, beat, and flower containers via the shared `oauth-creds` Docker volume.

Set both variables explicitly if you need fixed credentials (e.g. existing tokens must remain valid across redeployments).

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

When `S3_ACCESS_KEY` / `S3_SECRET_KEY` are not set, `s3setup.py` calls the Garage `CreateKey` API to generate credentials and writes them to `S3_CREDS_FILE`:

```json
{
  "access_key_id": "GKxxxxxxxxxxxxxxxxxxxx",
  "secret_key": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
}
```

The file is written with mode `0600`. It is read at startup by the API, worker, and beat containers via the shared `garage-creds` Docker volume mounted at the same path.

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
| `MAIL_FROM` | `info@misp-workbench.local` | From address used for platform emails |

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
