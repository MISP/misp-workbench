"""SDK exposed to reactor scripts as ``ctx``.

Every write goes through the audit log under the script's identity so that
admins can trace any side-effect back to a specific reactor run.
"""

import logging
from typing import Any, Optional
from uuid import UUID

from app.models import reactor as reactor_models
from app.repositories import attributes as attributes_repository
from app.repositories import events as events_repository
from app.repositories import modules as modules_repository
from app.repositories import objects as objects_repository
from app.repositories import tags as tags_repository
from app.schemas import attribute as attribute_schemas
from app.schemas import module as module_schemas
from app.services import audit
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class ReactorWriteQuotaExceeded(Exception):
    pass


class ReactorContext:
    """Minimal SDK passed to user scripts as the first positional argument.

    Read methods return plain dicts to keep the surface JSON-friendly. Write
    methods are quota-counted and audited.
    """

    def __init__(
        self,
        db: Session,
        script: reactor_models.ReactorScript,
        run: reactor_models.ReactorRun,
    ):
        self._db = db
        self._script = script
        self._run = run
        self._writes_count = 0

    # ---- introspection ----

    @property
    def run_id(self) -> int:
        return self._run.id

    @property
    def script_id(self) -> int:
        return self._script.id

    # ---- reads ----

    def get_event(self, event_uuid: str) -> Optional[dict]:
        result = events_repository.get_event_from_opensearch(UUID(event_uuid))
        if result is None:
            return None
        return result.model_dump(mode="json") if hasattr(result, "model_dump") else dict(result)

    def get_attribute(self, attribute_uuid: str) -> Optional[dict]:
        result = attributes_repository.get_attribute_from_opensearch(UUID(attribute_uuid))
        if result is None:
            return None
        return result.model_dump(mode="json") if hasattr(result, "model_dump") else dict(result)

    def get_object(self, object_uuid: str) -> Optional[dict]:
        result = objects_repository.get_object_from_opensearch(UUID(object_uuid))
        if result is None:
            return None
        return result.model_dump(mode="json") if hasattr(result, "model_dump") else dict(result)

    # ---- writes ----

    def add_attribute(
        self,
        event_uuid: str,
        type: str,
        value: str,
        category: str = "External analysis",
        comment: Optional[str] = None,
        to_ids: Optional[bool] = None,
    ) -> dict:
        self._account_write()
        attr_create = attribute_schemas.AttributeCreate(
            event_uuid=event_uuid,
            type=type,
            value=value,
            category=category,
        )
        if comment is not None:
            attr_create.comment = comment
        if to_ids is not None:
            attr_create.to_ids = to_ids
        result = attributes_repository.create_attribute(self._db, attr_create)
        attr_uuid = getattr(result, "uuid", None)
        self._audit(
            "attribute.create",
            resource_type="attribute",
            metadata={"event_uuid": event_uuid, "attribute_uuid": str(attr_uuid) if attr_uuid else None},
        )
        return result.model_dump(mode="json") if hasattr(result, "model_dump") else dict(result)

    def tag_event(self, event_uuid: str, tag_name: str) -> None:
        self._account_write()
        event = events_repository.get_event_from_opensearch(UUID(event_uuid))
        if event is None:
            raise ValueError(f"event {event_uuid} not found")
        tag = tags_repository.get_tag_by_name(self._db, tag_name)
        if tag is None:
            raise ValueError(f"tag {tag_name!r} not found")
        tags_repository.tag_event(self._db, event, tag)
        self._audit(
            "event.tag",
            resource_type="event",
            metadata={"event_uuid": event_uuid, "tag": tag_name},
        )

    def tag_attribute(self, attribute_uuid: str, tag_name: str) -> None:
        self._account_write()
        attr = attributes_repository.get_attribute_from_opensearch(UUID(attribute_uuid))
        if attr is None:
            raise ValueError(f"attribute {attribute_uuid} not found")
        tag = tags_repository.get_tag_by_name(self._db, tag_name)
        if tag is None:
            raise ValueError(f"tag {tag_name!r} not found")
        tags_repository.tag_attribute(self._db, attr, tag)
        self._audit(
            "attribute.tag",
            resource_type="attribute",
            metadata={"attribute_uuid": attribute_uuid, "tag": tag_name},
        )

    # ---- enrichment ----

    def enrich(
        self,
        value: str,
        type: str,
        module: str,
        config: Optional[dict] = None,
    ) -> dict:
        """Run a MISP expansion module on a single indicator and return its result.

        Counts against ``max_writes`` because enrichments hit external services
        with their own quotas. The module must be enabled in admin settings.
        """
        self._account_write()
        query = module_schemas.ModuleQuery(
            module=module,
            attribute={"type": type, "value": value, "uuid": ""},
            config=config,
        )
        try:
            result = modules_repository.query_module(self._db, query)
        except Exception as e:
            self._audit(
                "module.enrich.error",
                resource_type="module",
                metadata={"module": module, "type": type, "value": value, "error": str(e)},
            )
            raise
        self._audit(
            "module.enrich",
            resource_type="module",
            metadata={"module": module, "type": type, "value": value},
        )
        return result

    def list_modules(self, enabled_only: bool = True) -> list[dict]:
        """List available MISP enrichment modules.

        Read-only; does not count against ``max_writes``.
        """
        modules = modules_repository.get_modules(
            self._db, enabled=True if enabled_only else None
        )
        out: list[dict] = []
        for m in modules:
            data = m.model_dump(mode="json") if hasattr(m, "model_dump") else dict(m)
            out.append(
                {
                    "name": data.get("name"),
                    "type": data.get("type"),
                    "enabled": data.get("enabled"),
                    "input": (data.get("misp_attributes") or {}).get("input", []),
                    "output": (data.get("misp_attributes") or {}).get("output", []),
                    "description": (data.get("meta") or {}).get("description"),
                }
            )
        return out

    def log(self, *args: Any) -> None:
        """Convenience: like print, but also goes to the worker log."""
        msg = " ".join(str(a) for a in args)
        print(msg)
        logger.info("reactor[%s/run=%s] %s", self._script.id, self._run.id, msg)

    # ---- internals ----

    def _account_write(self) -> None:
        if self._writes_count >= self._script.max_writes:
            raise ReactorWriteQuotaExceeded(
                f"reactor script {self._script.id} exceeded max_writes={self._script.max_writes}"
            )
        self._writes_count += 1

    def _audit(self, verb: str, *, resource_type: str, metadata: dict) -> None:
        audit.record(
            self._db,
            action=f"reactor.write.{verb}",
            resource_type=resource_type,
            actor_user_id=self._script.user_id,
            actor_type="reactor_script",
            actor_credential_id=self._script.id,
            metadata={
                "run_id": self._run.id,
                "script_id": self._script.id,
                "script_name": self._script.name,
                **metadata,
            },
        )
