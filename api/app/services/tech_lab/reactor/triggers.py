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

    Filters supported:
      - ``tag``  / ``tags``  — match if any of the resource's tags is in the set
      - ``type`` / ``types`` — attribute type equality (only meaningful for
        attribute triggers)
      - ``org``  / ``orgs``  — orgc.name on an event/attribute
      - ``template`` / ``templates`` — object template name (only meaningful
        for object triggers; matched against ``payload['name']``)
    Singular forms accept a single value, plural forms accept a list of
    values (OR-match). Missing filter keys are treated as wildcards.
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
    tag_set = _as_set(filters.get("tag"), filters.get("tags"))
    if tag_set:
        tag_names = {
            t.get("name") for t in payload.get("tags", []) if isinstance(t, dict)
        }
        if tag_set.isdisjoint(tag_names):
            return False

    type_set = _as_set(filters.get("type"), filters.get("types"))
    if type_set and payload.get("type") not in type_set:
        return False

    org_set = _as_set(filters.get("org"), filters.get("orgs"))
    if org_set:
        orgc = payload.get("orgc") or {}
        if orgc.get("name") not in org_set:
            return False

    template_set = _as_set(filters.get("template"), filters.get("templates"))
    if template_set and payload.get("name") not in template_set:
        return False

    return True


def _as_set(singular: Any, plural: Any) -> set:
    """Combine optional singular + plural filter values into a set."""
    out: set = set()
    if singular:
        out.add(singular)
    if isinstance(plural, (list, tuple, set)):
        out.update(v for v in plural if v)
    return out
