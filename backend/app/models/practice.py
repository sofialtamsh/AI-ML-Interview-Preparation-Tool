"""Interview practice: a student answers an interview question out loud and gets interviewer-style
feedback. The video never leaves the student's device; only the voice is uploaded, and it is
deleted as soon as processing ends. The transcript and feedback stay so students can see progress.
"""

import uuid
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any

from sqlalchemy import ForeignKey, Index, LargeBinary, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, deferred, mapped_column, relationship

from app.models.base import Base, UUIDPrimaryKey, str_enum
from app.models.taxonomy import Topic


class AttemptStatus(StrEnum):
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    # Transcribed, but too little was said to judge (nothing is sent for feedback).
    NO_ANSWER = "no_answer"
    FAILED = "failed"


class PracticeAttempt(UUIDPrimaryKey, Base):
    __tablename__ = "practice_attempts"
    __table_args__ = (Index("ix_practice_attempts_student_created", "student_id", "created_at"),)

    student_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("students.id"))
    topic_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("topics.id"), index=True)
    # The published interview version and the question's position in it (versions are immutable).
    version_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("content_versions.id"))
    question_index: Mapped[int]
    question: Mapped[str] = mapped_column(Text)
    status: Mapped[AttemptStatus] = mapped_column(
        str_enum(AttemptStatus, "attempt_status"), default=AttemptStatus.QUEUED, index=True
    )
    duration_ms: Mapped[int]
    # The uploaded voice recording (16-bit PCM WAV). Cleared when processing ends.
    audio: Mapped[bytes | None] = deferred(mapped_column(LargeBinary))
    transcript: Mapped[str | None] = mapped_column(Text)
    # Pace, filler words and pauses, measured in code from the transcript.
    delivery: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    # The validated evaluation plus the score and verdict computed from it.
    feedback: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    score: Mapped[Decimal | None] = mapped_column(Numeric(3, 1))
    error: Mapped[str | None] = mapped_column(Text)
    transcription_model: Mapped[str | None] = mapped_column(String(200))
    feedback_model: Mapped[str | None] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    started_at: Mapped[datetime | None]
    heartbeat_at: Mapped[datetime | None]
    finished_at: Mapped[datetime | None]
    # A student can delete an attempt: its transcript and feedback are erased, the row (and the
    # AI spend that points at it) stays.
    deleted_at: Mapped[datetime | None]

    topic: Mapped[Topic] = relationship(lazy="joined")


# Admin decisions about practice feedback, stored in platform_settings under this key.
PRACTICE_SETTINGS = "practice_feedback"
