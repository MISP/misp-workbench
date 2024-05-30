#!/bin/bash
set -e

# run migrations
poetry run alembic upgrade head

# pull submodules
git submodule update --init --recursive

# start API
poetry run uvicorn app.main:app --host 0.0.0.0 --port 80
