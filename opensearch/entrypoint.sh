#!/bin/bash

set -e


# Set SCHEME based on environment (prod uses https)
if [ "${ENVIRONMENT:-prod}" = "prod" ]; then
  SCHEME="https"
else
  SCHEME="http"
fi

# Variables
OPENSEARCH_PORT="${OPENSEARCH_PORT:-9200}"
OPENSEARCH_HOSTNAME="${OPENSEARCH_HOSTNAME:-opensearch}"
OPENSEARCH_URL="${SCHEME}://${OPENSEARCH_HOSTNAME}:${OPENSEARCH_PORT}"
DASHBOARDS_URL="${SCHEME}://dashboards:${OPENSEARCH_DASHBOARDS_PORT:-5601}"
MAPPINGS_DIR="/mappings"
PIPELINES_DIR="/pipelines"
INDEX_TEMPLATES_DIR="/index-templates"
# locations for saved objects (mounted into the container)
INDEX_PATTERNS_DIR="/index-patterns"
VISUALIZATIONS_DIR="/visualizations"
DASHBOARDS_DIR="/dashboards"

echo "Waiting for OpenSearch to be ready at ${OPENSEARCH_URL}..."

# Wait for OpenSearch to become available
MAX_RETRIES=20
RETRY_COUNT=0

if [ "${SCHEME}" = "https" ]; then
  until curl --user admin:${OPENSEARCH_INITIAL_ADMIN_PASSWORD} -k "${OPENSEARCH_URL}" >/dev/null 2>&1; do
    RETRY_COUNT=$((RETRY_COUNT+1))
    if [ "$RETRY_COUNT" -ge "$MAX_RETRIES" ]; then
      echo "ERROR: OpenSearch (https) is not ready after $MAX_RETRIES attempts."
      echo "Last curl output:"
      curl --user admin:${OPENSEARCH_INITIAL_ADMIN_PASSWORD} -k "${OPENSEARCH_URL}" || true
      exit 1
    fi
    echo "OpenSearch (https) is not ready yet. Retrying in 3 seconds... ($RETRY_COUNT/$MAX_RETRIES)"
    sleep 3
  done
else
  until curl -s --user admin:${OPENSEARCH_INITIAL_ADMIN_PASSWORD} "${OPENSEARCH_URL}" >/dev/null 2>&1; do
    RETRY_COUNT=$((RETRY_COUNT+1))
    if [ "$RETRY_COUNT" -ge "$MAX_RETRIES" ]; then
      echo "ERROR: OpenSearch is not ready after $MAX_RETRIES attempts."
      echo "Last curl output:"
      curl --user admin:${OPENSEARCH_INITIAL_ADMIN_PASSWORD} -k "${OPENSEARCH_URL}" || true
      exit 1
    fi
    echo "OpenSearch is not ready yet. Retrying in 3 seconds... ($RETRY_COUNT/$MAX_RETRIES)"
    sleep 3
  done
fi

echo "OpenSearch is up! Proceeding with setup."

echo "Creating OpenSearch ingest pipelines..."
for file in "${PIPELINES_DIR}"/*.json; do
  PIPELINE_NAME=$(basename "$file" .json)

  STATUS=$(curl -s -o /dev/null -w "%{http_code}" "${OPENSEARCH_URL}/_ingest/pipeline/${PIPELINE_NAME}" || true)
  if [ "$STATUS" -eq 200 ]; then
    echo "Pipeline '$PIPELINE_NAME' already exists. Skipping..."
  else
    echo "Creating pipeline '$PIPELINE_NAME' using mapping file '$file'..."
    curl -s -X PUT "${OPENSEARCH_URL}/_ingest/pipeline/${PIPELINE_NAME}" \
         -H "Content-Type: application/json" \
         --user admin:${OPENSEARCH_INITIAL_ADMIN_PASSWORD} \
         -k \
         -d @"$file"
    echo "Pipeline '$PIPELINE_NAME' created."
  fi
done

echo "Creating OpenSearch index templates..."
for file in "${INDEX_TEMPLATES_DIR}"/*.json; do
  INDEX_TEMPLATE_NAME=$(basename "$file" .json)

  STATUS=$(curl -s -o /dev/null -w "%{http_code}" "${OPENSEARCH_URL}/_index_template/${INDEX_TEMPLATE_NAME}" || true)
  if [ "$STATUS" -eq 200 ]; then
    echo "Index template '$INDEX_TEMPLATE_NAME' already exists. Skipping..."
  else
    echo "Creating index template '$INDEX_TEMPLATE_NAME' using mapping file '$file'..."
    curl -s -X PUT "${OPENSEARCH_URL}/_index_template/${INDEX_TEMPLATE_NAME}" \
         -H "Content-Type: application/json" \
         --user admin:${OPENSEARCH_INITIAL_ADMIN_PASSWORD} \
         -k \
         -d @"$file"
    echo "Index template '$INDEX_TEMPLATE_NAME' created."
  fi
done

echo "Initializing OpenSearch indices..."
for file in "${MAPPINGS_DIR}"/*.json; do
  INDEX_NAME=$(basename "$file" .json)

  STATUS=$(curl -s -o /dev/null  --user admin:${OPENSEARCH_INITIAL_ADMIN_PASSWORD} -k -w "%{http_code}" "${OPENSEARCH_URL}/${INDEX_NAME}" || true)
  if [ "$STATUS" -eq 200 ]; then
    echo "Index '$INDEX_NAME' already exists. Skipping..."
  else
    echo "Creating index '$INDEX_NAME' using mapping file '$file'..."
    curl -s -X PUT "${OPENSEARCH_URL}/${INDEX_NAME}" \
         -H "Content-Type: application/json" \
         --user admin:${OPENSEARCH_INITIAL_ADMIN_PASSWORD} \
         -k \
         -d @"$file"
    echo "Index '$INDEX_NAME' created."
  fi
done

if [ "${ENVIRONMENT:-prod}" = "prod" ]; then
  curl --fail -k -u admin:${OPENSEARCH_INITIAL_ADMIN_PASSWORD} \
    -X PUT "${OPENSEARCH_URL}/_plugins/_security/api/internalusers/dashboards_system" \
    -H "Content-Type: application/json" \
    -d "{
      \"password\": \"${OPENSEARCH_DASHBOARDS_PASSWORD}\",
      \"reserved\": true,
      \"backend_roles\": [\"dashboards_system\"],
      \"description\": \"OpenSearch Dashboards service user\"
    }"
  echo "dashboards_system user configured"
fi

echo "OpenSearch setup completed successfully."

# Import OpenSearch Dashboards saved objects (index-patterns, visualizations, dashboards)
echo "Importing OpenSearch Dashboards saved objects (if available)..."

# choose credentials: in prod we created dashboards_system user; use it if available
if [ "${ENVIRONMENT:-prod}" = "prod" ] && [ -n "${OPENSEARCH_DASHBOARDS_PASSWORD}" ]; then
  IMPORT_USER="dashboards_system"
  IMPORT_PASS="${OPENSEARCH_DASHBOARDS_PASSWORD}"
  CURL_AUTH_OPT="--user ${IMPORT_USER}:${IMPORT_PASS}"
else
  # in non-prod mode we don't pass authentication for saved object imports
  CURL_AUTH_OPT=""
fi

IMPORT_URL="${DASHBOARDS_URL}/api/saved_objects/_import?overwrite=true"

import_ndjson() {
  local file="$1"
  if [ ! -f "$file" ]; then
    echo "File $file not found, skipping."
    return 0
  fi

  echo "Importing $file -> ${IMPORT_URL}"
  # OpenSearch Dashboards requires an XSRF header (kbn-xsrf for Kibana-compatible API)
  HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" \
    ${CURL_AUTH_OPT} -k \
    -X POST "${IMPORT_URL}" \
    -H "osd-xsrf: true" \
    -F "file=@${file}") || HTTP_STATUS=000

  if [ "$HTTP_STATUS" -ge 200 ] && [ "$HTTP_STATUS" -lt 300 ]; then
    echo "Imported $file successfully (http $HTTP_STATUS)."
  else
    echo "Warning: failed to import $file (http $HTTP_STATUS)."
    # print server response for debugging
  curl ${CURL_AUTH_OPT} -k -X POST "${IMPORT_URL}" -H "osd-xsrf: true" -F "file=@${file}" || true
  fi
}

# Import index-patterns first
for file in "${INDEX_PATTERNS_DIR}"/*.ndjson; do
  [ -e "$file" ] || continue
  import_ndjson "$file"
done

# Import visualizations
for file in "${VISUALIZATIONS_DIR}"/*.ndjson; do
  [ -e "$file" ] || continue
  import_ndjson "$file"
done

# Import dashboards
for file in "${DASHBOARDS_DIR}"/*.ndjson; do
  [ -e "$file" ] || continue
  import_ndjson "$file"
done

echo "Saved objects import complete."
