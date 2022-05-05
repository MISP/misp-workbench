#!/bin/bash
set -e

# run migrations
alembic upgrade head

# start API
uvicorn app.main:app --host 0.0.0.0 --port 80 --reload