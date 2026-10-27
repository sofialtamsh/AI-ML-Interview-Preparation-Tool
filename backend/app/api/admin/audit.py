from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth.deps import require_permission
from app.auth.permissions import Perm
from app.core.db import get_db
from app.models import AuditLog
from app.schemas.admin import AuditLogOut
from app.schemas.common import Page

router = APIRouter(tags=["admin-audit"])


@router.get(
    "/audit-logs",
    response_model=Page[AuditLogOut],
    dependencies=[Depends(require_permission(Perm.AUDIT_VIEW))],
)
def list_audit_logs(
    action: str | None = Query(default=None, max_length=100),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
) -> Page[AuditLogOut]:
    conditions = [AuditLog.action.startswith(action)] if action else []
    total = db.scalar(select(func.count()).select_from(AuditLog).where(*conditions)) or 0
    logs = db.scalars(
        select(AuditLog)
        .where(*conditions)
        .order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return Page(
        items=[
            AuditLogOut(
                id=log.id,
                action=log.action,
                entity_type=log.entity_type,
                entity_id=log.entity_id,
                details=log.details,
                actor_name=log.actor.full_name if log.actor else None,
                actor_email=log.actor.email if log.actor else None,
                ip_address=log.ip_address,
                created_at=log.created_at,
            )
            for log in logs
        ],
        total=total,
        page=page,
        page_size=page_size,
    )
