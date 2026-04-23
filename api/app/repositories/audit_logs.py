from datetime import datetime
from typing import Optional

from app.models import audit_log as audit_log_models
from app.schemas import audit_log as audit_log_schemas
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlalchemy import paginate
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload


def _to_schema(row: audit_log_models.AuditLog) -> audit_log_schemas.AuditLog:
    return audit_log_schemas.AuditLog(
        id=row.id,
        created_at=row.created_at,
        actor_user_id=row.actor_user_id,
        actor_email=row.actor.email if row.actor else None,
        actor_type=row.actor_type,
        actor_credential_id=row.actor_credential_id,
        resource_type=row.resource_type,
        resource_id=row.resource_id,
        action=row.action,
        ip_address=str(row.ip_address) if row.ip_address is not None else None,
        user_agent=row.user_agent,
        metadata=row.metadata_,
    )


def list_audit_logs(
    db: Session,
    *,
    actor_user_id: Optional[int] = None,
    resource_type: Optional[str] = None,
    resource_id: Optional[int] = None,
    action: Optional[str] = None,
    actor_type: Optional[str] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
) -> Page[audit_log_schemas.AuditLog]:
    query = select(audit_log_models.AuditLog).options(
        joinedload(audit_log_models.AuditLog.actor)
    )

    if actor_user_id is not None:
        query = query.where(audit_log_models.AuditLog.actor_user_id == actor_user_id)
    if resource_type:
        query = query.where(audit_log_models.AuditLog.resource_type == resource_type)
    if resource_id is not None:
        query = query.where(audit_log_models.AuditLog.resource_id == resource_id)
    if action:
        query = query.where(audit_log_models.AuditLog.action.ilike(f"{action}%"))
    if actor_type:
        query = query.where(audit_log_models.AuditLog.actor_type == actor_type)
    if date_from is not None:
        query = query.where(audit_log_models.AuditLog.created_at >= date_from)
    if date_to is not None:
        query = query.where(audit_log_models.AuditLog.created_at <= date_to)

    query = query.order_by(audit_log_models.AuditLog.created_at.desc())

    return paginate(db, query, transformer=lambda rows: [_to_schema(r) for r in rows])
