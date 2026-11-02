"""Interview practice, as students and admins see it. Students get their own attempts only, and
never the model names or anything about other students."""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import Field

from app.models import AttemptStatus, PracticeAttempt
from app.schemas.common import ApiModel


class PracticeStatus(ApiModel):
    feedback_available: bool
    reason: str | None
    daily_limit: int
    used_today: int
    max_seconds: int


class AttemptSummary(ApiModel):
    id: uuid.UUID
    topic_slug: str
    question_index: int
    question: str
    status: AttemptStatus
    score: float | None
    verdict: str | None
    duration_ms: int
    created_at: datetime


class AttemptDetail(AttemptSummary):
    transcript: str | None
    delivery: dict[str, Any] | None
    feedback: dict[str, Any] | None
    error: str | None


def attempt_summary(attempt: PracticeAttempt) -> dict[str, Any]:
    feedback = attempt.feedback or {}
    return {
        "id": attempt.id,
        "topic_slug": attempt.topic.slug,
        "question_index": attempt.question_index,
        "question": attempt.question,
        "status": attempt.status,
        "score": float(attempt.score) if attempt.score is not None else None,
        "verdict": (feedback.get("verdict") or {}).get("label"),
        "duration_ms": attempt.duration_ms,
        "created_at": attempt.created_at,
    }


def attempt_detail(attempt: PracticeAttempt) -> AttemptDetail:
    feedback = dict(attempt.feedback) if attempt.feedback else None
    if feedback:
        feedback.pop("dropped_quotes", None)  # quality monitoring, not for students
    return AttemptDetail(
        **attempt_summary(attempt),
        transcript=attempt.transcript,
        delivery=attempt.delivery,
        feedback=feedback,
        error=attempt.error,
    )


# --- Admin ---------------------------------------------------------------------------------------


class PracticeSettingsUpdate(ApiModel):
    enabled: bool
    daily_limit: int = Field(ge=1, le=50)


class PracticeWeek(ApiModel):
    attempts: int
    students: int
    feedback_given: int
    average_score: float | None
    cost_usd: Decimal


class PracticeAdminView(ApiModel):
    enabled: bool
    daily_limit: int
    ai_configured: bool
    max_seconds: int
    transcription_model: str
    feedback_model: str
    last_7_days: PracticeWeek
