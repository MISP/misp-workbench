#!/bin/bash

set -e

# Variables
OPENSEARCH_PORT="${OPENSEARCH_PORT:-9200}"
OPENSEARCH_HOSTNAME="${OPENSEARCH_HOSTNAME:-opensearch}"
OPENSEARCH_URL="http://${OPENSEARCH_HOSTNAME}:${OPENSEARCH_PORT}"
MAPPINGS_DIR="/mappings"
PIPELINES_DIR="/pipelines"

echo "Waiting for OpenSearch to be ready at ${OPENSEARCH_URL}..."

# Wait for OpenSearch to become available
until curl -s "${OPENSEARCH_URL}" >/dev/null 2>&1; do
  echo "OpenSearch is not ready yet. Retrying in 3 seconds..."
  sleep 3
done

echo "OpenSearch is up! Proceeding with setup."

echo "Initializing OpenSearch indices..."
for file in "${MAPPINGS_DIR}"/*.json; do
  INDEX_NAME=$(basename "$file" .json)

  STATUS=$(curl -s -o /dev/null -w "%{http_code}" "${OPENSEARCH_URL}/${INDEX_NAME}" || true)
  if [ "$STATUS" -eq 200 ]; then
    echo "Index '$INDEX_NAME' already exists. Skipping..."
  else
    echo "Creating index '$INDEX_NAME' using mapping file '$file'..."
    curl -s -X PUT "${OPENSEARCH_URL}/${INDEX_NAME}" \
         -H "Content-Type: application/json" \
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
         -d @"$file"
    echo "Pipeline '$PIPELINE_NAME' created."
  fi
done

echo "OpenSearch setup completed successfully."
