#!/bin/bash
set -e

# run migrations
poetry run alembic upgrade head

# bootstrap Garage S3 (layout, key, bucket)
if [ "$STORAGE_ENGINE" = "s3" ]; then
  poetry run python -m app.s3setup
fi

# create admin org and user
poetry run python -m app.cli create-organisation ADMIN
poetry run python -m app.cli create-user admin@admin.test admin 1 1

# load galaxies and taxonomies
poetry run python -m app.cli load-galaxies --user-id 1
poetry run python -m app.cli load-taxonomies --user-id 1

# start API
poetry run python -m debugpy --listen 0.0.0.0:5678 -m uvicorn app.main:app --reload --host 0.0.0.0 --port 80
