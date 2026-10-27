from datetime import timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import Date, cast, func, select
from sqlalchemy.orm import Session

from app.auth.deps import AdminContext, get_ready_admin
from app.auth.permissions import Perm
from app.core.db import get_db
from app.core.security import utcnow
from app.models import AdminStatus, AdminUser, Audience, AuthSession, Student
from app.schemas.admin import DailyCount, Overview, StudentListItem, StudentStats

router = APIRouter(tags=["admin-overview"])


def _student_stats(db: Session) -> StudentStats:
    now = utcnow()
    week_ago, month_ago = now - timedelta(days=7), now - timedelta(days=30)

    by_status = {
        status.value: count
        for status, count in db.execute(
            select(Student.status, func.count()).group_by(Student.status)
        )
    }
    # "Active" means the student actually used the platform, not merely that a session exists.
    active_7d = db.scalar(
        select(func.count(func.distinct(AuthSession.student_id))).where(
            AuthSession.audience == Audience.STUDENT, AuthSession.last_seen_at >= week_ago
        )
    )
    new_7d = db.scalar(select(func.count()).where(Student.created_at >= week_ago))

    day = cast(func.timezone("UTC", Student.created_at), Date)
    daily = dict(
        db.execute(
            select(day, func.count()).where(Student.created_at >= month_ago).group_by(day)
        ).all()
    )
    start = (now - timedelta(days=29)).date()
    series = [
        DailyCount(day=start + timedelta(days=i), count=daily.get(start + timedelta(days=i), 0))
        for i in range(30)
    ]

    recent = db.scalars(select(Student).order_by(Student.created_at.desc()).limit(5)).all()
    return StudentStats(
        total=sum(by_status.values()),
        by_status=by_status,
        active_last_7_days=active_7d or 0,
        new_last_7_days=new_7d or 0,
        new_last_30_days=sum(c.count for c in series),
        registrations_last_30_days=series,
        recent=[StudentListItem.of(s) for s in recent],
    )


@router.get("/overview", response_model=Overview)
def overview(
    ctx: AdminContext = Depends(get_ready_admin), db: Session = Depends(get_db)
) -> Overview:
    """Each section is included only if the admin holds the permission that guards its data."""
    perms = ctx.permissions
    return Overview(
        students=_student_stats(db) if Perm.STUDENTS_VIEW in perms else None,
        active_admins=(
            db.scalar(select(func.count()).where(AdminUser.status == AdminStatus.ACTIVE))
            if Perm.ADMINS_MANAGE in perms
            else None
        ),
    )
