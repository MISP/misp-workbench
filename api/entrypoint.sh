#!/bin/bash
set -e

# Check mandatory variables are defined
: "${OPENSEARCH_INITIAL_ADMIN_PASSWORD:?Variable is mandatory}"
: "${OAUTH2_SECRET_KEY:?Variable is mandatory}"
: "${OAUTH2_REFRESH_SECRET_KEY:?Variable is mandatory}"
: "${GARAGE_ADMIN_TOKEN:?Variable is mandatory}"
: "${S3_ACCESS_KEY:?Variable is mandatory}"
: "${S3_SECRET_KEY:?Variable is mandatory}"

# run migrations
poetry run alembic upgrade head

# bootstrap Garage S3 (layout, key, bucket)
if [ "$STORAGE_ENGINE" = "s3" ]; then
  poetry run python -m app.s3setup
fi

# create admin org and user (skipped if they already exist)
ADMIN_PASSWORD=$(openssl rand -hex 16)
poetry run python -m app.cli create-organisation ADMIN
CREATE_USER_OUTPUT=$(poetry run python -m app.cli create-user admin@admin.local "$ADMIN_PASSWORD" --org-name ADMIN --role-id 1)
echo "$CREATE_USER_OUTPUT"

cat <<'EOF'

  ███╗   ███╗██╗███████╗██████╗     ██╗    ██╗ ██████╗ ██████╗ ██╗  ██╗██████╗ ███████╗███╗   ██╗ ██████╗██╗  ██╗
  ████╗ ████║██║██╔════╝██╔══██╗    ██║    ██║██╔═══██╗██╔══██╗██║ ██╔╝██╔══██╗██╔════╝████╗  ██║██╔════╝██║  ██║
  ██╔████╔██║██║███████╗██████╔╝    ██║ █╗ ██║██║   ██║██████╔╝█████╔╝ ██████╔╝█████╗  ██╔██╗ ██║██║     ███████║
  ██║╚██╔╝██║██║╚════██║██╔═══╝     ██║███╗██║██║   ██║██╔══██╗██╔═██╗ ██╔══██╗██╔══╝  ██║╚██╗██║██║     ██╔══██║
  ██║ ╚═╝ ██║██║███████║██║         ╚███╔███╔╝╚██████╔╝██║  ██║██║  ██╗██████╔╝███████╗██║ ╚████║╚██████╗██║  ██║
  ╚═╝     ╚═╝╚═╝╚══════╝╚═╝          ╚══╝╚══╝  ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝╚═════╝ ╚══════╝╚═╝  ╚═══╝ ╚═════╝╚═╝  ╚═╝

  Server is ready!
EOF
if echo "$CREATE_USER_OUTPUT" | grep -q "Created user"; then
  echo "  Admin credentials:  admin@admin.local / $ADMIN_PASSWORD"
  echo "  Save this password — it will not be shown again."
  echo
fi

# OpenSearch credentials (prod security plugin is enabled)
export OPENSEARCH_USERNAME="${OPENSEARCH_USERNAME:-admin}"
export OPENSEARCH_PASSWORD="${OPENSEARCH_PASSWORD:-${OPENSEARCH_INITIAL_ADMIN_PASSWORD}}"

# provision dedicated OpenSearch user if one is configured
poetry run python -m app.opensearch_setup

# start API
poetry run uvicorn app.main:app --host ${API_LISTEN_HOST:-0.0.0.0} --port ${API_LISTEN_PORT:-80} --forwarded-allow-ips ${API_PROXY_IP:-127.0.0.1}
