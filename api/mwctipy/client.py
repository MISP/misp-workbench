"""The ``MwLab`` instance that user notebooks call into.

Every method opens its own short-lived ``Session(engine)``. The kernel is
long-lived across cells, so holding a single session would accumulate
transaction state, hit Postgres idle timeouts, and miss runtime config
changes. This is the key behavioural difference from ``ReactorContext``,
which takes a Session in its constructor for a single short-lived run.
"""

from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import Any, Iterator, Optional
from uuid import UUID

from sqlalchemy.orm import Session


logger = logging.getLogger(__name__)


@contextmanager
def _session() -> Iterator[Session]:
    # Local imports keep this module importable in environments that don't
    # have the full ``app`` stack on sys.path (rare, but useful for unit tests).
    from app.database import SQLALCHEMY_DATABASE_URL
    from sqlalchemy import create_engine

    engine = create_engine(SQLALCHEMY_DATABASE_URL)
    session = Session(engine)
    try:
        yield session
    finally:
        session.close()


class MwLab:
    """Read-only analyst SDK bound to a single ``(user_id, notebook_id)``."""

    def __init__(self, *, user_id: int, notebook_id: int):
        self.user_id = int(user_id)
        self.notebook_id = int(notebook_id)

    def __repr__(self) -> str:  # pragma: no cover - cosmetic
        return f"<MwLab user_id={self.user_id} notebook_id={self.notebook_id}>"

    # ── single-record reads ────────────────────────────────────────────────

    def get_event(self, event_uuid: str) -> Optional[dict]:
        from app.repositories import events as events_repository

        result = events_repository.get_event_from_opensearch(UUID(event_uuid))
        if result is None:
            return None
        return _to_dict(result)

    def get_attribute(self, attribute_uuid: str) -> Optional[dict]:
        from app.repositories import attributes as attributes_repository

        result = attributes_repository.get_attribute_from_opensearch(
            UUID(attribute_uuid)
        )
        if result is None:
            return None
        return _to_dict(result)

    def get_object(self, object_uuid: str) -> Optional[dict]:
        from app.repositories import objects as objects_repository

        result = objects_repository.get_object_from_opensearch(UUID(object_uuid))
        if result is None:
            return None
        return _to_dict(result)

    # ── search ─────────────────────────────────────────────────────────────

    def search_events(
        self,
        query: Optional[str] = None,
        tags: Optional[list[str]] = None,
        size: int = 50,
    ) -> list[dict]:
        """Search events via OpenSearch.

        ``query`` is a free-text fragment matched against event ``info``;
        ``tags`` is an AND-list of tag names. Returns a list of dicts
        (not pydantic models) so analysts can stuff them into pandas.
        """
        from app.services.opensearch import get_opensearch_client

        must: list[dict] = []
        if query:
            must.append({"match": {"info": query}})
        if tags:
            for t in tags:
                must.append({"term": {"tags.name": t}})
        body = {
            "size": size,
            "query": {"bool": {"must": must}} if must else {"match_all": {}},
        }
        client = get_opensearch_client()
        resp = client.search(index="misp-events", body=body)
        return [hit.get("_source", {}) for hit in resp.get("hits", {}).get("hits", [])]

    def search_attributes(
        self,
        value: Optional[str] = None,
        type: Optional[str] = None,
        size: int = 50,
    ) -> list[dict]:
        from app.services.opensearch import get_opensearch_client

        must: list[dict] = []
        if value:
            must.append({"match": {"value": value}})
        if type:
            must.append({"term": {"type": type}})
        body = {
            "size": size,
            "query": {"bool": {"must": must}} if must else {"match_all": {}},
        }
        client = get_opensearch_client()
        resp = client.search(index="misp-attributes", body=body)
        return [hit.get("_source", {}) for hit in resp.get("hits", {}).get("hits", [])]

    # ── modules / enrichment ───────────────────────────────────────────────

    def modules(self, enabled_only: bool = True) -> list[dict]:
        from app.repositories import modules as modules_repository

        with _session() as db:
            modules = modules_repository.get_modules(
                db, enabled=True if enabled_only else None
            )
            return [_to_dict(m) for m in modules]

    def enrich(
        self,
        value: str,
        type: str,
        module: str,
        config: Optional[dict] = None,
    ) -> dict:
        """Run a MISP expansion module against one indicator.

        Audited under ``actor_type=lab_notebook``,
        ``actor_credential_id=notebook_id`` so admins can trace any
        third-party API call back to the notebook that triggered it.
        """
        from app.repositories import modules as modules_repository
        from app.schemas import module as module_schemas
        from app.services import audit

        query = module_schemas.ModuleQuery(
            module=module,
            attribute={"type": type, "value": value, "uuid": ""},
            config=config,
        )
        with _session() as db:
            try:
                result = modules_repository.query_module(db, query)
            except Exception as e:
                audit.record(
                    db,
                    action="lab.enrich.error",
                    resource_type="module",
                    actor_user_id=self.user_id,
                    actor_type="lab_notebook",
                    actor_credential_id=self.notebook_id,
                    metadata={
                        "module": module, "type": type, "value": value,
                        "error": str(e),
                    },
                )
                db.commit()
                raise
            audit.record(
                db,
                action="lab.enrich",
                resource_type="module",
                actor_user_id=self.user_id,
                actor_type="lab_notebook",
                actor_credential_id=self.notebook_id,
                metadata={"module": module, "type": type, "value": value},
            )
            db.commit()
            return result

    # ── convenience ────────────────────────────────────────────────────────

    def dataframe(self, rows: list[dict]):
        """Return a ``pandas.DataFrame`` from a list of dicts.

        Pandas is available in the lab-worker image; the import lives inside
        the call so importing ``mwctipy`` outside that container doesn't
        require it.
        """
        import pandas as pd

        return pd.DataFrame(rows)


def _to_dict(obj: Any) -> dict:
    if hasattr(obj, "model_dump"):
        return obj.model_dump(mode="json")
    if isinstance(obj, dict):
        return obj
    return dict(obj)
