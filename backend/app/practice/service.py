"""Queueing and processing practice attempts.

A student's "Get feedback" queues an attempt; dedicated worker threads (separate from the admin
job worker, so a long content run never keeps students waiting) transcribe the voice, measure the
delivery and ask for feedback. The audio is erased when processing ends, whatever the outcome.
Spend is bounded by an admin switch and a per-student daily limit.
"""

import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.agents.common import AgentError, structured_chat
from app.ai import openrouter
from app.ai.openrouter import AiProviderError
from app.core.config import get_settings
from app.core.db import SessionLocal
from app.core.security import utcnow
from app.jobs.runner import Worker
from app.models import (
    PRACTICE_SETTINGS,
    AttemptStatus,
    Component,
    ContentItem,
    ContentVersion,
    Domain,
    PlatformSetting,
    PracticeAttempt,
    Student,
    Topic,
)
from app.practice.audio import wav_duration_ms
from app.practice.delivery import measure
from app.practice.feedback import AnswerFeedback, build_messages, finalize

log = logging.getLogger(__name__)

TRANSCRIPTION_FEATURE = "practice_transcription"
FEEDBACK_FEATURE = "practice_feedback"
DEFAULT_DAILY_LIMIT = 10
MAX_DAILY_LIMIT = 50
# Fewer words than this isn't an answer worth judging (and isn't sent for feedback).
MIN_WORDS = 12
STALE_AFTER = timedelta(minutes=10)
BUSY_STATUSES = {429, 502, 503, 504, 524, 529}


class PracticeError(Exception):
    def __init__(self, status_code: int, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code


@dataclass(frozen=True)
class PracticeConfig:
    enabled: bool
    daily_limit: int


def practice_config(db: Session) -> PracticeConfig:
    setting = db.get(PlatformSetting, PRACTICE_SETTINGS)
    value = setting.value if setting and isinstance(setting.value, dict) else {}
    return PracticeConfig(
        enabled=bool(value.get("enabled", True)),
        daily_limit=int(value.get("daily_limit", DEFAULT_DAILY_LIMIT)),
    )


def _today_start() -> datetime:
    tz = ZoneInfo(get_settings().usage_timezone)
    return datetime.combine(utcnow().astimezone(tz).date(), time.min, tz)


def used_today(db: Session, student_id: uuid.UUID) -> int:
    """Feedback requests today (local time). Ones that failed on our side don't count."""
    return (
        db.scalar(
            select(func.count()).where(
                PracticeAttempt.student_id == student_id,
                PracticeAttempt.created_at >= _today_start(),
                PracticeAttempt.status != AttemptStatus.FAILED,
            )
        )
        or 0
    )


def unavailable(db: Session, student_id: uuid.UUID) -> PracticeError | None:
    """Why this student can't get feedback right now (recording works regardless)."""
    config = practice_config(db)
    if not config.enabled:
        return PracticeError(503, "AI feedback is switched off right now.")
    if not openrouter.ai_configured():
        return PracticeError(503, "AI feedback isn't set up yet.")
    if used_today(db, student_id) >= config.daily_limit:
        return PracticeError(
            429, f"You've used today's {config.daily_limit} feedback requests. More tomorrow!"
        )
    return None


def published_interview(db: Session, slug: str) -> tuple[Topic, ContentVersion]:
    found = db.execute(
        select(Topic, ContentVersion)
        .join(Domain, Topic.domain_id == Domain.id)
        .join(ContentItem, ContentItem.topic_id == Topic.id)
        .join(ContentVersion, ContentItem.published_version_id == ContentVersion.id)
        .where(
            Topic.slug == slug,
            Topic.archived_at.is_(None),
            Domain.archived_at.is_(None),
            ContentItem.component == Component.INTERVIEW,
        )
    ).first()
    if found is None:
        raise PracticeError(404, "Topic not found.")
    return found[0], found[1]


def queue_attempt(
    db: Session,
    student: Student,
    *,
    topic_slug: str,
    version_id: uuid.UUID,
    question_index: int,
    audio: bytes,
) -> PracticeAttempt:
    topic, version = published_interview(db, topic_slug)
    if version.id != version_id:
        raise PracticeError(
            409, "These questions were just updated. Reload the page and try again."
        )
    questions = version.body["questions"]
    if not 0 <= question_index < len(questions):
        raise PracticeError(404, "Question not found.")
    if problem := unavailable(db, student.id):
        raise problem
    duration_ms = wav_duration_ms(audio, get_settings().practice_max_answer_seconds)

    attempt = PracticeAttempt(
        student_id=student.id,
        topic_id=topic.id,
        version_id=version.id,
        question_index=question_index,
        question=questions[question_index]["question"],
        duration_ms=duration_ms,
        audio=audio,
    )
    db.add(attempt)
    db.commit()
    return attempt


# --- Processing --------------------------------------------------------------------------------


class _Failure(Exception):
    pass


def _provider_message(error: AiProviderError) -> str:
    if error.status_code in BUSY_STATUSES:
        return "The AI is busy right now. Try again in a minute."
    return "AI feedback is temporarily unavailable. Try again later."


def claim_next_attempt(db: Session) -> PracticeAttempt | None:
    attempt = db.scalars(
        select(PracticeAttempt)
        .where(PracticeAttempt.status == AttemptStatus.QUEUED)
        .order_by(PracticeAttempt.created_at)
        .limit(1)
        .with_for_update(skip_locked=True, of=PracticeAttempt)
    ).first()
    if attempt is None:
        return None
    attempt.status = AttemptStatus.PROCESSING
    attempt.started_at = attempt.heartbeat_at = utcnow()
    db.commit()
    return attempt


def process_attempt(attempt_id: uuid.UUID) -> AttemptStatus:
    settings = get_settings()
    with SessionLocal() as db:
        attempt = db.get(PracticeAttempt, attempt_id)
        if attempt is None:
            raise LookupError(f"Practice attempt {attempt_id} not found")
        error: str | None = None
        try:
            audio = attempt.audio
            if not audio:
                raise _Failure("The recording was lost. Record your answer again.")
            version = db.get(ContentVersion, attempt.version_id)
            assert version is not None  # noqa: S101 (versions are never deleted)
            item = version.body["questions"][attempt.question_index]
            client = openrouter.make_ai_client()
            if client is None:
                raise _Failure("AI feedback isn't set up yet.")
            try:
                heard = client.transcribe(
                    feature=TRANSCRIPTION_FEATURE,
                    model=settings.model_transcription,
                    audio=audio,
                    audio_format="wav",
                    student_id=attempt.student_id,
                    practice_attempt_id=attempt.id,
                )
                delivery = measure(heard.text, attempt.duration_ms, heard.segments)
                attempt.transcript = heard.text
                attempt.delivery = delivery
                attempt.transcription_model = heard.model
                attempt.heartbeat_at = utcnow()
                db.commit()

                if delivery["words"] < MIN_WORDS:
                    status = AttemptStatus.NO_ANSWER
                else:
                    feedback = structured_chat(
                        client,
                        AnswerFeedback,
                        feature=FEEDBACK_FEATURE,
                        model=settings.model_feedback,
                        messages=build_messages(item, heard.text, delivery),
                        job_id=None,
                        admin_id=None,
                        student_id=attempt.student_id,
                        practice_attempt_id=attempt.id,
                    )
                    result = finalize(feedback, heard.text, item)
                    attempt.feedback = result
                    attempt.score = result["score"]
                    attempt.feedback_model = settings.model_feedback
                    status = AttemptStatus.COMPLETED
            finally:
                client.close()
        except _Failure as exc:
            status, error = AttemptStatus.FAILED, str(exc)
        except AiProviderError as exc:
            log.warning("Practice attempt %s: AI provider error: %s", attempt_id, exc)
            status, error = AttemptStatus.FAILED, _provider_message(exc)
        except AgentError:
            status = AttemptStatus.FAILED
            error = "The feedback came back in the wrong shape. Try again."
        except Exception:
            log.exception("Practice attempt %s crashed", attempt_id)
            status, error = AttemptStatus.FAILED, "Something went wrong on our side. Try again."

        if status is AttemptStatus.FAILED:
            db.rollback()
            attempt = db.get(PracticeAttempt, attempt_id)
            assert attempt is not None  # noqa: S101
            attempt.transcript = attempt.delivery = attempt.feedback = None
        attempt.audio = None
        attempt.status = status
        attempt.error = error
        attempt.finished_at = utcnow()
        db.commit()
        return status


def run_pending_attempts(limit: int | None = None) -> int:
    ran = 0
    while limit is None or ran < limit:
        with SessionLocal() as db:
            attempt = claim_next_attempt(db)
            attempt_id = attempt.id if attempt else None
        if attempt_id is None:
            return ran
        process_attempt(attempt_id)
        ran += 1
    return ran


def recover_stale_attempts() -> int:
    """Attempts whose worker died mid-way (e.g. a restart) fail and free the student's quota."""
    cutoff = utcnow() - STALE_AFTER
    with SessionLocal() as db:
        stale = db.scalars(
            select(PracticeAttempt)
            .where(
                PracticeAttempt.status == AttemptStatus.PROCESSING,
                or_(PracticeAttempt.heartbeat_at < cutoff, PracticeAttempt.heartbeat_at.is_(None)),
            )
            .with_for_update(skip_locked=True, of=PracticeAttempt)
        ).all()
        for attempt in stale:
            attempt.status = AttemptStatus.FAILED
            attempt.error = "This took too long and was stopped. Try again."
            attempt.audio = attempt.transcript = attempt.delivery = attempt.feedback = None
            attempt.finished_at = utcnow()
        db.commit()
        return len(stale)


def erase_attempt(db: Session, attempt: PracticeAttempt) -> None:
    if attempt.status in (AttemptStatus.QUEUED, AttemptStatus.PROCESSING):
        raise PracticeError(409, "Wait for the feedback to finish, then delete it.")
    attempt.transcript = attempt.delivery = attempt.feedback = attempt.score = None
    attempt.audio = None
    attempt.deleted_at = utcnow()
    db.commit()


# --- Workers -----------------------------------------------------------------------------------

_workers: list[Worker] = []


def start_practice_workers(count: int) -> None:
    for number in range(count):
        worker = Worker(
            name=f"ipp-practice-worker-{number + 1}",
            run_one=lambda: run_pending_attempts(limit=1),
            recover=recover_stale_attempts,
        )
        worker.start()
        _workers.append(worker)


def stop_practice_workers() -> None:
    while _workers:
        _workers.pop().stop()


def notify_practice_workers() -> None:
    """Call after committing a new attempt so an idle in-process worker starts it right away."""
    if _workers:
        _workers[0].notify()
