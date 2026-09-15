"""Compile Tech Lab servos into OpenSearch ingest pipelines and keep them in sync.

Wiring (see docs/features/opensearch/ingest-pipelines.md)::

    misp-attributes_final            (repo file)
     |- pipeline: misp-attributes_ip_geoip
     `- pipeline: misp-attributes_servos      <- content owned by this module
          |- pipeline: servo_<slug>  + on_failure
          `- pipeline: servo_<slug>  + on_failure

Two constraints shape this module:

- OpenSearch 3.x's ``pipeline`` processor has no ``ignore_missing_pipeline``, so
  ``misp-attributes_servos`` must always exist. It ships as a repo file with an
  empty processor list, which ``opensearch/entrypoint.sh`` PUTs on every stack
  start -- wiping the chain. ``sync()`` therefore runs at API startup too, not
  just after a mutation.
- A failing servo must never stop an attribute from being indexed, so every
  chain entry carries an ``on_failure`` that records the message on the document
  instead of letting the failure propagate.
"""

import json
import logging
import pathlib
from datetime import datetime, timezone
from typing import Optional

from opensearchpy.exceptions import NotFoundError, RequestError, TransportError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import servo as servo_models
from app.opensearch import OpenSearchClient
from app.schemas.servo import SERVO_PREFIX, SYSTEM_PREFIX

logger = logging.getLogger(__name__)

TARGET_INDEX = "misp-attributes"
CHAIN_PIPELINE = f"{TARGET_INDEX}_servos"
SERVO_ERRORS_FIELD = "expanded.servo_errors"

TEMPLATES_DIR = pathlib.Path(__file__).parent / "templates"


def pipeline_name(slug: str) -> str:
    return f"{SERVO_PREFIX}{slug}"


def classify(name: str) -> str:
    """Bucket a cluster pipeline as system / servo / external by its name."""
    if name.startswith(SYSTEM_PREFIX):
        return "system"
    if name.startswith(SERVO_PREFIX):
        return "servo"
    return "external"


def compile_pipeline(db_servo: servo_models.Servo) -> dict:
    """The servo's own ``_ingest/pipeline`` body."""
    return {
        "description": db_servo.description
        or f"Transformation servo '{db_servo.name}' (misp-workbench Tech Lab)",
        "processors": list(db_servo.processors or []),
    }


def _chain_entry(db_servo: servo_models.Servo) -> dict:
    name = pipeline_name(db_servo.slug)
    return {
        "pipeline": {
            "name": name,
            "on_failure": [
                {
                    "append": {
                        "field": SERVO_ERRORS_FIELD,
                        "value": f"{name}: {{{{{{_ingest.on_failure_message}}}}}}",
                    }
                }
            ],
        }
    }


def get_enabled_servos(db: Session) -> list[servo_models.Servo]:
    return list(
        db.scalars(
            select(servo_models.Servo)
            .where(servo_models.Servo.enabled.is_(True))
            .order_by(servo_models.Servo.position, servo_models.Servo.id)
        ).all()
    )


def build_chain(db: Session) -> dict:
    """The body of ``misp-attributes_servos``: every enabled servo, in order."""
    return {
        "description": (
            "Tech Lab transformation servos. Managed by the misp-workbench API "
            "-- edit servos in the UI, not here."
        ),
        "processors": [_chain_entry(s) for s in get_enabled_servos(db)],
    }


def _all_servos(db: Session) -> list[servo_models.Servo]:
    return list(
        db.scalars(
            select(servo_models.Servo).order_by(
                servo_models.Servo.position, servo_models.Servo.id
            )
        ).all()
    )


def sync(db: Session) -> dict:
    """Make OpenSearch match the DB. Idempotent.

    PUTs a pipeline per enabled servo, deletes ``servo_*`` pipelines with no
    enabled row behind them, then rewrites the chain. Returns a small summary
    for logging and tests.
    """
    enabled = get_enabled_servos(db)
    known = {pipeline_name(s.slug) for s in _all_servos(db)}
    wanted = {pipeline_name(s.slug) for s in enabled}

    for db_servo in enabled:
        OpenSearchClient.ingest.put_pipeline(
            id=pipeline_name(db_servo.slug), body=compile_pipeline(db_servo)
        )

    # The chain is rewritten before orphans are dropped so nothing in the live
    # chain ever points at a pipeline that has just been deleted.
    OpenSearchClient.ingest.put_pipeline(id=CHAIN_PIPELINE, body=build_chain(db))

    removed = []
    for name in _cluster_pipeline_names():
        if classify(name) != "servo":
            continue
        # Only ever touch pipelines this feature owns: a servo_* pipeline with
        # no row at all is left alone rather than assumed to be ours.
        if name in wanted or name not in known:
            continue
        try:
            OpenSearchClient.ingest.delete_pipeline(id=name)
            removed.append(name)
        except NotFoundError:
            pass

    now = datetime.now(timezone.utc)
    for db_servo in enabled:
        db_servo.last_synced_at = now
    db.commit()

    return {"applied": sorted(wanted), "removed": sorted(removed)}


def sync_quietly(db: Session) -> None:
    """``sync`` that logs instead of raising. Used where OpenSearch being down
    must not take the caller with it (API startup)."""
    try:
        sync(db)
    except Exception:  # noqa: BLE001
        logger.exception("servo chain sync failed; servos are not applied")


def delete_pipeline(slug: str) -> None:
    try:
        OpenSearchClient.ingest.delete_pipeline(id=pipeline_name(slug))
    except NotFoundError:
        pass


def _cluster_pipeline_names() -> list[str]:
    return list(get_cluster_pipelines().keys())


def get_cluster_pipelines() -> dict:
    """Every ingest pipeline in the cluster, keyed by name."""
    try:
        return dict(OpenSearchClient.ingest.get_pipeline())
    except NotFoundError:
        # A cluster with no pipelines at all answers 404 rather than {}.
        return {}


def get_cluster_pipeline(name: str) -> Optional[dict]:
    try:
        response = OpenSearchClient.ingest.get_pipeline(id=name)
    except NotFoundError:
        return None
    return response.get(name)


def processor_types(definition: dict) -> list[str]:
    """The processor type of each step, in order, deduplicated but ordered."""
    types: list[str] = []
    for processor in definition.get("processors") or []:
        if not isinstance(processor, dict) or not processor:
            continue
        kind = next(iter(processor))
        if kind == "pipeline":
            # Chain steps read better as the pipeline they delegate to.
            target = (processor.get("pipeline") or {}).get("name")
            kind = f"pipeline:{target}" if target else "pipeline"
        if kind not in types:
            types.append(kind)
    return types


def simulate(
    processors: list[dict], docs: list[dict]
) -> tuple[bool, list[dict], Optional[str]]:
    """Run ``_ingest/pipeline/_simulate`` with an inline pipeline body.

    Nothing is persisted. Returns ``(ok, docs, error)`` -- a 400 from OpenSearch
    is a user error (bad processor config) and comes back as ``error``, while a
    transport failure is raised.
    """
    body = {
        "pipeline": {"description": "servo dry run", "processors": processors},
        "docs": [{"_index": TARGET_INDEX, "_source": doc} for doc in docs],
    }
    try:
        response = OpenSearchClient.ingest.simulate(body=body)
    except RequestError as error:
        return False, [], _reason(error)

    results = []
    for entry in response.get("docs", []):
        if "error" in entry:
            return False, [], json.dumps(entry["error"])
        results.append((entry.get("doc") or {}).get("_source", {}))
    return True, results, None


def _reason(error: TransportError) -> str:
    info = getattr(error, "info", None)
    if isinstance(info, dict):
        nested = info.get("error")
        if isinstance(nested, dict):
            return nested.get("reason") or json.dumps(nested)
        if nested:
            return str(nested)
    return str(error)


def fetch_sample_docs(attribute_uuids: list[str]) -> list[dict]:
    """Pull real attribute documents so a dry run uses live data."""
    if not attribute_uuids:
        return []
    response = OpenSearchClient.mget(
        index=TARGET_INDEX, body={"ids": [str(u) for u in attribute_uuids]}
    )
    return [
        doc["_source"]
        for doc in response.get("docs", [])
        if doc.get("found") and doc.get("_source")
    ]


def load_templates() -> list[dict]:
    """Starter processor sets shipped alongside this module."""
    templates = []
    for path in sorted(TEMPLATES_DIR.glob("*.json")):
        templates.append(json.loads(path.read_text()))
    return templates
