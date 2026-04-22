"""Audit logging service.

Generic, append-only record of security-relevant events. Other features
record events via `audit.record(...)`. Entries are written in the caller's
DB session so they commit or roll back with the business operation.

Designing new integrations:
- `resource_type` is a short tag like "api_key", "event", "user".
- `action` is a dotted verb namespaced by resource: "api_key.created",
  "api_key.authenticated", "user.login".
- `metadata` is a JSON-serializable dict with action-specific details.
  Never include raw credentials.

`request_context(request)` extracts IP + user agent from a FastAPI Request
so callers don't need to pull them out by hand.
"""

import ipaddress
from typing import Optional

from app.models import audit_log as audit_log_models
from fastapi import Request
from sqlalchemy.orm import Session


ACTOR_USER = "user"
ACTOR_API_KEY = "api_key"
ACTOR_SYSTEM = "system"


def _valid_ip(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    try:
        ipaddress.ip_address(value)
    except ValueError:
        return None
    return value


def request_context(request: Optional[Request]) -> dict:
    if request is None:
        return {}
    ip = request.client.host if request.client else None
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        # Left-most entry is the original client.
        ip = forwarded.split(",")[0].strip() or ip
    user_agent = request.headers.get("user-agent")
    return {"ip_address": _valid_ip(ip), "user_agent": user_agent}


def record(
    db: Session,
    *,
    action: str,
    resource_type: str,
    resource_id: Optional[int] = None,
    actor_user_id: Optional[int] = None,
    actor_type: str = ACTOR_USER,
    actor_credential_id: Optional[int] = None,
    request: Optional[Request] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    metadata: Optional[dict] = None,
) -> audit_log_models.AuditLog:
    ctx = request_context(request)
    entry = audit_log_models.AuditLog(
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        actor_user_id=actor_user_id,
        actor_type=actor_type,
        actor_credential_id=actor_credential_id,
        ip_address=_valid_ip(ip_address) or ctx.get("ip_address"),
        user_agent=user_agent or ctx.get("user_agent"),
        metadata_=metadata,
    )
    db.add(entry)
    db.flush()
    return entry
