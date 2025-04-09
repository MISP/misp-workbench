#!/bin/bash

set -e

# Variables
OPENSEARCH_PORT="${OPENSEARCH_PORT:-9200}"
OPENSEARCH_HOSTNAME="${OPENSEARCH_HOSTNAME:-opensearch}"
OPENSEARCH_URL="$OPENSEARCH_HOSTNAME:$OPENSEARCH_PORT"
MAPPINGS_DIR="/mappings"
PIPELINES_DIR="/pipelines"

echo "Initializing OpenSearch indices..."
for file in "$MAPPINGS_DIR"/*.json; do
  INDEX_NAME=$(basename "$file" .json)

  # Check if index exists
  if curl -s -o /dev/null -w "%{http_code}" "$OPENSEARCH_URL/$INDEX_NAME" | grep -q "200"; then
    echo "Index '$INDEX_NAME' already exists. Skipping..."
  else
    echo "Creating index '$INDEX_NAME' using mapping file '$file'..."
    curl -s -X PUT "$OPENSEARCH_URL/$INDEX_NAME" \
         -H "Content-Type: application/json" \
         -d @"$file"
    echo "Index '$INDEX_NAME' created."
  fi
done

echo "Creating OpenSearch ingest pipelines..."
for file in "$PIPELINES_DIR"/*.json; do
  PIPELINE_NAME=$(basename "$file" .json)

  # Check if pipeline exists
  if curl -s -o /dev/null -w "%{http_code}" "$OPENSEARCH_URL/_ingest/pipeline/$PIPELINE_NAME" | grep -q "200"; then
    echo "Pipeline '$PIPELINE_NAME' already exists. Skipping..."
  else
    echo "Creating pipeline '$PIPELINE_NAME' using mapping file '$file'..."
    curl -s -X PUT "$OPENSEARCH_URL/_ingest/pipeline/$PIPELINE_NAME" \
         -H "Content-Type: application/json" \
         -d @"$file"
    echo "Pipeline '$PIPELINE_NAME' created."
  fi
done