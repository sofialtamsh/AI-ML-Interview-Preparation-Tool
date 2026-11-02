"""Interview practice for students: upload a spoken answer, get interviewer-style feedback.

Every query is scoped to the signed-in student. Only the voice is uploaded (the video stays in the
browser), and the audio is erased once processing ends."""

import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile, status
from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.auth.deps import StudentContext, get_student_context
from app.core.config import get_settings
from app.core.db import get_db
from app.core.rate_limit import RateLimiter
from app.models import PracticeAttempt, Topic
from app.practice.audio import AudioProblem, max_upload_bytes
from app.practice.service import (
    PracticeError,
    erase_attempt,
    notify_practice_workers,
    practice_config,
    queue_attempt,
    unavailable,
    used_today,
)
from app.schemas.practice import (
    AttemptDetail,
    AttemptSummary,
    PracticeStatus,
    attempt_detail,
    attempt_summary,
)

router = APIRouter(prefix="/practice", tags=["student-practice"])

# Per student (not per IP: a whole classroom can share one address).
upload_limiter = RateLimiter("practice-upload", limit=6, window_seconds=60)


def _http(error: PracticeError) -> HTTPException:
    return HTTPException(error.status_code, str(error))


@router.get("/status", response_model=PracticeStatus)
def practice_status(
    ctx: StudentContext = Depends(get_student_context), db: Session = Depends(get_db)
) -> PracticeStatus:
    problem = unavailable(db, ctx.student.id)
    return PracticeStatus(
        feedback_available=problem is None,
        reason=str(problem) if problem else None,
        daily_limit=practice_config(db).daily_limit,
        used_today=used_today(db, ctx.student.id),
        max_seconds=get_settings().practice_max_answer_seconds,
    )


@router.post("/attempts", response_model=AttemptDetail, status_code=status.HTTP_202_ACCEPTED)
def submit_attempt(
    topic: str = Form(max_length=300),
    version_id: uuid.UUID = Form(),
    question_index: int = Form(ge=0, le=100),
    audio: UploadFile = File(),
    ctx: StudentContext = Depends(get_student_context),
    db: Session = Depends(get_db),
) -> AttemptDetail:
    if not upload_limiter.allow(str(ctx.student.id)):
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS, "Too many answers at once. Wait a minute."
        )
    limit = max_upload_bytes(get_settings().practice_max_answer_seconds)
    data = audio.file.read(limit + 1)
    if len(data) > limit:
        raise HTTPException(status.HTTP_413_CONTENT_TOO_LARGE, "That recording is too large.")
    try:
        attempt = queue_attempt(
            db,
            ctx.student,
            topic_slug=topic,
            version_id=version_id,
            question_index=question_index,
            audio=data,
        )
    except PracticeError as exc:
        raise _http(exc) from exc
    except AudioProblem as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from exc
    notify_practice_workers()
    return attempt_detail(attempt)


def _own_attempts(ctx: StudentContext) -> Select[tuple[PracticeAttempt]]:
    return select(PracticeAttempt).where(
        PracticeAttempt.student_id == ctx.student.id, PracticeAttempt.deleted_at.is_(None)
    )


@router.get("/attempts", response_model=list[AttemptSummary])
def list_attempts(
    topic: str | None = None,
    ctx: StudentContext = Depends(get_student_context),
    db: Session = Depends(get_db),
) -> list[AttemptSummary]:
    query = _own_attempts(ctx).order_by(PracticeAttempt.created_at.desc()).limit(200)
    if topic is not None:
        query = query.join(Topic, PracticeAttempt.topic_id == Topic.id).where(Topic.slug == topic)
    return [AttemptSummary(**attempt_summary(a)) for a in db.scalars(query).unique()]


def _get_own(db: Session, ctx: StudentContext, attempt_id: uuid.UUID) -> PracticeAttempt:
    attempt = db.scalars(_own_attempts(ctx).where(PracticeAttempt.id == attempt_id)).first()
    if attempt is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Attempt not found.")
    return attempt


@router.get("/attempts/{attempt_id}", response_model=AttemptDetail)
def get_attempt(
    attempt_id: uuid.UUID,
    ctx: StudentContext = Depends(get_student_context),
    db: Session = Depends(get_db),
) -> AttemptDetail:
    return attempt_detail(_get_own(db, ctx, attempt_id))


@router.delete("/attempts/{attempt_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_attempt(
    attempt_id: uuid.UUID,
    ctx: StudentContext = Depends(get_student_context),
    db: Session = Depends(get_db),
) -> Response:
    try:
        erase_attempt(db, _get_own(db, ctx, attempt_id))
    except PracticeError as exc:
        raise _http(exc) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)
