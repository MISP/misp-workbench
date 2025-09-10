#!/bin/bash
set -e

# run migrations
poetry run alembic upgrade head

# create admin org and user
poetry run python -m app.cli create-organisation ADMIN
poetry run python -m app.cli create-user admin@admin.test admin 1 1

# start API
poetry run uvicorn app.main:app --host 0.0.0.0 --port 80
