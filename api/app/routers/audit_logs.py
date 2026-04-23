from datetime import datetime
from typing import Optional

from app.auth.security import get_current_active_user
from app.db.session import get_db
from app.repositories import audit_logs as audit_logs_repository
from app.schemas import audit_log as audit_log_schemas
from app.schemas import user as user_schemas
from fastapi import APIRouter, Depends, Security
from fastapi_pagination import Page
from sqlalchemy.orm import Session

router = APIRouter()


@router.get(
    "/admin/audit-logs/",
    response_model=Page[audit_log_schemas.AuditLog],
)
def admin_list_audit_logs(
    actor_user_id: Optional[int] = None,
    resource_type: Optional[str] = None,
    resource_id: Optional[int] = None,
    action: Optional[str] = None,
    actor_type: Optional[str] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    db: Session = Depends(get_db),
    _admin: user_schemas.User = Security(
        get_current_active_user, scopes=["audit_logs:admin"]
    ),
) -> Page[audit_log_schemas.AuditLog]:
    return audit_logs_repository.list_audit_logs(
        db,
        actor_user_id=actor_user_id,
        resource_type=resource_type,
        resource_id=resource_id,
        action=action,
        actor_type=actor_type,
        date_from=date_from,
        date_to=date_to,
    )
