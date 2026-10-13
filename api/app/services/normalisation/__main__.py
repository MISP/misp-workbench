"""Regenerate opensearch/pipelines/misp-attributes_normalise.json."""

from app.services.normalisation import write_repo_pipeline

print(write_repo_pipeline())
