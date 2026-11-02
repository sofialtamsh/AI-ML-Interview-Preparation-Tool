"""Admin controls for interview-practice feedback: the on/off switch, the per-student daily limit,
and last week's usage. Admins see counts and cost here, never students' transcripts."""

from datetime import timedelta
from decimal import Decimal

from fastapi import APIRouter, Depends, Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.ai import openrouter
from app.auth.deps import AdminContext, require_any_permission, require_permission
from app.auth.permissions import Perm
from app.core.audit import record_audit
from app.core.config import get_settings
from app.core.db import get_db
from app.core.security import utcnow
from app.models import (
    PRACTICE_SETTINGS,
    AiUsageEvent,
    AttemptStatus,
    PlatformSetting,
    PracticeAttempt,
)
from app.practice.service import practice_config
from app.schemas.practice import PracticeAdminView, PracticeSettingsUpdate, PracticeWeek

router = APIRouter(prefix="/practice", tags=["admin-practice"])


def _view(db: Session) -> PracticeAdminView:
    settings = get_settings()
    config = practice_config(db)
    since = utcnow() - timedelta(days=7)
    attempts, students = db.execute(
        select(func.count(), func.count(func.distinct(PracticeAttempt.student_id))).where(
            PracticeAttempt.created_at >= since
        )
    ).one()
    given, average = db.execute(
        select(func.count(), func.avg(PracticeAttempt.score)).where(
            PracticeAttempt.created_at >= since,
            PracticeAttempt.status == AttemptStatus.COMPLETED,
        )
    ).one()
    cost = db.scalar(
        select(func.coalesce(func.sum(AiUsageEvent.cost_usd), 0)).where(
            AiUsageEvent.occurred_at >= since, AiUsageEvent.practice_attempt_id.is_not(None)
        )
    )
    return PracticeAdminView(
        enabled=config.enabled,
        daily_limit=config.daily_limit,
        ai_configured=openrouter.ai_configured(),
        max_seconds=settings.practice_max_answer_seconds,
        transcription_model=settings.model_transcription,
        feedback_model=settings.model_feedback,
        last_7_days=PracticeWeek(
            attempts=attempts,
            students=students,
            feedback_given=given,
            average_score=round(float(average), 1) if average is not None else None,
            cost_usd=Decimal(cost or 0),
        ),
    )


@router.get(
    "/settings",
    response_model=PracticeAdminView,
    dependencies=[Depends(require_any_permission(Perm.AI_USAGE_VIEW, Perm.SETTINGS_MANAGE))],
)
def get_practice_settings(db: Session = Depends(get_db)) -> PracticeAdminView:
    return _view(db)


@router.put("/settings", response_model=PracticeAdminView)
def update_practice_settings(
    body: PracticeSettingsUpdate,
    request: Request,
    ctx: AdminContext = Depends(require_permission(Perm.SETTINGS_MANAGE)),
    db: Session = Depends(get_db),
) -> PracticeAdminView:
    before = practice_config(db)
    setting = db.get(PlatformSetting, PRACTICE_SETTINGS)
    if setting is None:
        setting = PlatformSetting(key=PRACTICE_SETTINGS, value={})
        db.add(setting)
    setting.value = {"enabled": body.enabled, "daily_limit": body.daily_limit}
    setting.updated_by_admin_id = ctx.admin.id
    changes = {
        field: {"from": old, "to": new}
        for field, old, new in (
            ("enabled", before.enabled, body.enabled),
            ("daily_limit", before.daily_limit, body.daily_limit),
        )
        if old != new
    }
    if changes:
        record_audit(
            db,
            request,
            ctx,
            "practice.settings_changed",
            "platform_setting",
            PRACTICE_SETTINGS,
            changes,
        )
    db.commit()
    return _view(db)
