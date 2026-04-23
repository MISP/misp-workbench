from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel


class AuditLog(BaseModel):
    id: int
    created_at: datetime
    actor_user_id: Optional[int] = None
    actor_email: Optional[str] = None
    actor_type: str
    actor_credential_id: Optional[int] = None
    resource_type: str
    resource_id: Optional[int] = None
    action: str
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    metadata: Optional[dict[str, Any]] = None
