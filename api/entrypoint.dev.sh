#!/bin/bash
set -e

# run migrations
alembic upgrade head

# installd debug tools
pip install debugpy 

# start API
python -m debugpy --listen 0.0.0.0:5678 -m uvicorn app.main:app --reload --host 0.0.0.0 --port 80
