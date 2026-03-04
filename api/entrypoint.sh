#!/bin/bash
set -e

# run migrations
poetry run alembic upgrade head

# bootstrap Garage S3 (layout, key, bucket)
if [ "$STORAGE_ENGINE" = "s3" ]; then
  poetry run python -m app.s3setup
fi

# start API
poetry run uvicorn app.main:app --host 0.0.0.0 --port 80
