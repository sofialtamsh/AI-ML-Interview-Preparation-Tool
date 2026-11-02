"""A student's own learning progress: what they did, quiz attempts and their dashboard.

Everything is stored against the signed-in student and scoped to them; there is no way to name
another student. Quizzes are graded here from the published version, never by the browser."""

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.auth.deps import StudentContext, get_student_context
from app.core.db import get_db
from app.core.rate_limit import RateLimiter
from app.progress.service import (
    ProgressError,
    record_event,
    record_time,
    student_summary,
    submit_quiz,
    topic_progress,
)
from app.schemas.progress import (
    EventIn,
    ProgressSummary,
    QuizResult,
    QuizSubmitIn,
    TimeIn,
    TopicProgressOut,
)

router = APIRouter(prefix="/progress", tags=["student-progress"])

# Per student: generous for normal use, a stop for runaway clients.
event_limiter = RateLimiter("progress-events", limit=120, window_seconds=60)
quiz_limiter = RateLimiter("progress-quiz", limit=20, window_seconds=60)
time_limiter = RateLimiter("progress-time", limit=12, window_seconds=60)


def _limit(limiter: RateLimiter, ctx: StudentContext) -> None:
    if not limiter.allow(str(ctx.student.id)):
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Too many requests. Slow down.")


@router.get("", response_model=ProgressSummary, response_model_by_alias=True)
def my_progress(
    ctx: StudentContext = Depends(get_student_context), db: Session = Depends(get_db)
) -> ProgressSummary:
    return ProgressSummary.model_validate(student_summary(db, ctx.student.id))


@router.get("/topics/{slug:path}", response_model=TopicProgressOut)
def my_topic_progress(
    slug: str, ctx: StudentContext = Depends(get_student_context), db: Session = Depends(get_db)
) -> TopicProgressOut:
    try:
        return TopicProgressOut.model_validate(topic_progress(db, ctx.student.id, slug))
    except ProgressError as exc:
        raise HTTPException(exc.status_code, str(exc)) from exc


@router.post("/events", response_model=TopicProgressOut)
def add_event(
    body: EventIn,
    ctx: StudentContext = Depends(get_student_context),
    db: Session = Depends(get_db),
) -> TopicProgressOut:
    _limit(event_limiter, ctx)
    try:
        record_event(
            db,
            ctx.student.id,
            slug=body.topic,
            component=body.component,
            kind=body.kind,
            data=body.data,
        )
        return TopicProgressOut.model_validate(topic_progress(db, ctx.student.id, body.topic))
    except ProgressError as exc:
        raise HTTPException(exc.status_code, str(exc)) from exc


@router.post("/time", status_code=status.HTTP_204_NO_CONTENT)
def add_time(
    body: TimeIn,
    ctx: StudentContext = Depends(get_student_context),
    db: Session = Depends(get_db),
) -> Response:
    """Active time on a topic page, sent by the browser about once a minute."""
    _limit(time_limiter, ctx)
    try:
        record_time(
            db, ctx.student.id, slug=body.topic, component=body.component, seconds=body.seconds
        )
    except ProgressError as exc:
        raise HTTPException(exc.status_code, str(exc)) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/quiz-attempts", response_model=QuizResult, status_code=status.HTTP_201_CREATED)
def add_quiz_attempt(
    body: QuizSubmitIn,
    ctx: StudentContext = Depends(get_student_context),
    db: Session = Depends(get_db),
) -> QuizResult:
    _limit(quiz_limiter, ctx)
    try:
        attempt = submit_quiz(
            db,
            ctx.student.id,
            slug=body.topic,
            version_id=body.version_id,
            answers=body.answers,
            duration_seconds=body.duration_seconds,
        )
        best = topic_progress(db, ctx.student.id, body.topic)["quiz"]["best_pct"]
    except ProgressError as exc:
        raise HTTPException(exc.status_code, str(exc)) from exc
    return QuizResult(
        attempt_number=attempt.attempt_number,
        correct=attempt.correct,
        total=attempt.total,
        score_pct=float(attempt.score_pct),
        best_pct=float(best or 0),
    )
