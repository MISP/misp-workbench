"""Match reactor scripts to (resource_type, action) trigger events."""

from typing import Any, Iterable

from app.models import reactor as reactor_models
from sqlalchemy.orm import Session


def list_active_scripts_for(
    db: Session, resource_type: str, action: str
) -> list[reactor_models.ReactorScript]:
    """Return all active scripts subscribed to (resource_type, action).

    JSONB array filter could be done in SQL, but the active-script set is
    small (per-user, hand-curated), so we filter in Python for clarity.
    """
    rows = (
        db.query(reactor_models.ReactorScript)
        .filter(reactor_models.ReactorScript.status == "active")
        .all()
    )
    return [s for s in rows if _has_trigger(s.triggers or [], resource_type, action)]


def _has_trigger(triggers: Iterable[dict], resource_type: str, action: str) -> bool:
    for t in triggers:
        if t.get("resource_type") == resource_type and t.get("action") == action:
            return True
    return False


def matches_filters(
    triggers: Iterable[dict],
    resource_type: str,
    action: str,
    payload: dict[str, Any],
) -> bool:
    """Apply optional filters from the matching trigger entry.

    Filters supported in v1:
      - ``tag``  — one of the resource's tags (case-sensitive name match)
      - ``type`` — attribute type equality
      - ``org``  — orgc.name on an event/attribute
    Missing filter keys are treated as wildcards.
    """
    for t in triggers:
        if t.get("resource_type") != resource_type or t.get("action") != action:
            continue
        filters = t.get("filters") or {}
        if not filters:
            return True
        if _filters_pass(filters, payload):
            return True
    return False


def _filters_pass(filters: dict[str, Any], payload: dict[str, Any]) -> bool:
    tag_filter = filters.get("tag")
    if tag_filter:
        tag_names = [t.get("name") for t in payload.get("tags", []) if isinstance(t, dict)]
        if tag_filter not in tag_names:
            return False

    type_filter = filters.get("type")
    if type_filter and payload.get("type") != type_filter:
        return False

    org_filter = filters.get("org")
    if org_filter:
        orgc = payload.get("orgc") or {}
        if orgc.get("name") != org_filter:
            return False

    return True
