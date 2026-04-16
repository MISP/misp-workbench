#!/bin/bash
set -e

# Auto-generate OAuth2 secrets if not provided, persisting them across restarts
OAUTH2_CREDS_FILE="${OAUTH2_CREDS_FILE:-/var/lib/misp-workbench/oauth-creds/oauth2.json}"
if [ -z "$OAUTH2_SECRET_KEY" ] || [ -z "$OAUTH2_REFRESH_SECRET_KEY" ]; then
  if [ -f "$OAUTH2_CREDS_FILE" ]; then
    echo "Loading OAuth2 secrets from $OAUTH2_CREDS_FILE"
    export OAUTH2_SECRET_KEY=$(python3 -c "import json; print(json.load(open('$OAUTH2_CREDS_FILE'))['secret_key'])")
    export OAUTH2_REFRESH_SECRET_KEY=$(python3 -c "import json; print(json.load(open('$OAUTH2_CREDS_FILE'))['refresh_secret_key'])")
  else
    echo "Generating new OAuth2 secrets..."
    export OAUTH2_SECRET_KEY=$(openssl rand -hex 32)
    export OAUTH2_REFRESH_SECRET_KEY=$(openssl rand -hex 32)
    mkdir -p "$(dirname "$OAUTH2_CREDS_FILE")"
    python3 -c "
import json, os
with open('$OAUTH2_CREDS_FILE', 'w') as f:
    json.dump({'secret_key': os.environ['OAUTH2_SECRET_KEY'], 'refresh_secret_key': os.environ['OAUTH2_REFRESH_SECRET_KEY']}, f)
os.chmod('$OAUTH2_CREDS_FILE', 0o600)
"
    echo "OAuth2 secrets generated and saved to $OAUTH2_CREDS_FILE"
  fi
fi

# run migrations
poetry run alembic upgrade head

# bootstrap Garage S3 (layout, key, bucket)
if [ "$STORAGE_ENGINE" = "s3" ]; then
  poetry run python -m app.s3setup
fi

# create admin org and user
poetry run python -m app.cli create-organisation ADMIN
poetry run python -m app.cli create-user admin@admin.test admin --org-name ADMIN --role-id 1

cat <<'EOF'

  ███╗   ███╗██╗███████╗██████╗     ██╗    ██╗ ██████╗ ██████╗ ██╗  ██╗██████╗ ███████╗███╗   ██╗ ██████╗██╗  ██╗
  ████╗ ████║██║██╔════╝██╔══██╗    ██║    ██║██╔═══██╗██╔══██╗██║ ██╔╝██╔══██╗██╔════╝████╗  ██║██╔════╝██║  ██║
  ██╔████╔██║██║███████╗██████╔╝    ██║ █╗ ██║██║   ██║██████╔╝█████╔╝ ██████╔╝█████╗  ██╔██╗ ██║██║     ███████║
  ██║╚██╔╝██║██║╚════██║██╔═══╝     ██║███╗██║██║   ██║██╔══██╗██╔═██╗ ██╔══██╗██╔══╝  ██║╚██╗██║██║     ██╔══██║
  ██║ ╚═╝ ██║██║███████║██║         ╚███╔███╔╝╚██████╔╝██║  ██║██║  ██╗██████╔╝███████╗██║ ╚████║╚██████╗██║  ██║
  ╚═╝     ╚═╝╚═╝╚══════╝╚═╝          ╚══╝╚══╝  ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝╚═════╝ ╚══════╝╚═╝  ╚═══╝ ╚═════╝╚═╝  ╚═╝

  Server is ready!
  Admin credentials:  admin@admin.test / admin

EOF

# load galaxies and taxonomies
poetry run python -m app.cli load-galaxies --user-id 1
poetry run python -m app.cli load-taxonomies --user-id 1

# start API
poetry run python -m debugpy --listen 0.0.0.0:5678 -m uvicorn app.main:app --reload --host 0.0.0.0 --port 80
