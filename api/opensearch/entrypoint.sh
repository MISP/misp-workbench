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
MAPPINGS_DIR="/mappings"
PIPELINES_DIR="/pipelines"

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

echo "OpenSearch setup completed successfully."
