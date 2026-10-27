from typing import Any

from fastapi import Request
from sqlalchemy.orm import Session

from app.auth.deps import AdminContext
from app.auth.sessions import client_ip
from app.models import AuditLog


def record_audit(
    db: Session,
    request: Request,
    ctx: AdminContext,
    action: str,
    entity_type: str,
    entity_id: object | None = None,
    details: dict[str, Any] | None = None,
) -> None:
    """Append an audit entry in the caller's transaction. Never pass secrets in `details`."""
    db.add(
        AuditLog(
            actor_admin_id=ctx.admin.id,
            action=action,
            entity_type=entity_type,
            entity_id=str(entity_id) if entity_id is not None else None,
            details=details or {},
            ip_address=client_ip(request),
        )
    )
