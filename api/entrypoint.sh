#!/bin/bash
set -e

# run migrations
poetry run alembic upgrade head

# bootstrap Garage S3 (layout, key, bucket)
if [ "$STORAGE_ENGINE" = "s3" ]; then
  poetry run python -m app.s3setup
fi

# create admin org and user (skipped if they already exist)
ADMIN_PASSWORD=$(openssl rand -base64 18 | tr -dc 'a-zA-Z0-9' | head -c 24)
poetry run python -m app.cli create-organisation ADMIN
poetry run python -m app.cli create-user admin@admin.local "$ADMIN_PASSWORD" 1 1

cat <<'EOF'

  ███╗   ███╗██╗███████╗██████╗     ██╗    ██╗ ██████╗ ██████╗ ██╗  ██╗██████╗ ███████╗███╗   ██╗ ██████╗██╗  ██╗
  ████╗ ████║██║██╔════╝██╔══██╗    ██║    ██║██╔═══██╗██╔══██╗██║ ██╔╝██╔══██╗██╔════╝████╗  ██║██╔════╝██║  ██║
  ██╔████╔██║██║███████╗██████╔╝    ██║ █╗ ██║██║   ██║██████╔╝█████╔╝ ██████╔╝█████╗  ██╔██╗ ██║██║     ███████║
  ██║╚██╔╝██║██║╚════██║██╔═══╝     ██║███╗██║██║   ██║██╔══██╗██╔═██╗ ██╔══██╗██╔══╝  ██║╚██╗██║██║     ██╔══██║
  ██║ ╚═╝ ██║██║███████║██║         ╚███╔███╔╝╚██████╔╝██║  ██║██║  ██╗██████╔╝███████╗██║ ╚████║╚██████╗██║  ██║
  ╚═╝     ╚═╝╚═╝╚══════╝╚═╝          ╚══╝╚══╝  ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝╚═════╝ ╚══════╝╚═╝  ╚═══╝ ╚═════╝╚═╝  ╚═╝

  Server is ready!
EOF
echo "  Admin credentials:  admin@admin.local / $ADMIN_PASSWORD"
echo

# OpenSearch credentials (prod security plugin is enabled)
export OPENSEARCH_USERNAME="${OPENSEARCH_USERNAME:-admin}"
export OPENSEARCH_PASSWORD="${OPENSEARCH_PASSWORD:-${OPENSEARCH_INITIAL_ADMIN_PASSWORD}}"

# provision dedicated OpenSearch user if one is configured
poetry run python -m app.opensearch_setup

# start API
poetry run uvicorn app.main:app --host 0.0.0.0 --port 80
