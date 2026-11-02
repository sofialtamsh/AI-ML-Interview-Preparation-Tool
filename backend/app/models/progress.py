"""Learning progress and quiz attempts, stored against the student so they survive logout and
follow the student across devices.

`learning_events` is the append-only record of what a student did. `topic_progress` is the
current state per student and topic, derived from those events. Quiz attempts are graded on the
server and never overwritten: a retake is a new attempt.
"""

import uuid
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any

from sqlalchemy import BigInteger, ForeignKey, Identity, Index, Numeric, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDPrimaryKey, str_enum
from app.models.content import Component


class LearningEventKind(StrEnum):
    SECTION_OPENED = "section_opened"
    SECTION_DONE = "section_done"
    LESSON_PROGRESS = "lesson_progress"  # {"seen": cards seen, "of": cards}
    PLAYGROUND_TASK = "playground_task"  # {"task": index, "of": tasks}
    VIDEO_PROGRESS = "video_progress"  # {"scene": index, "of": scenes}
    CODE_RUN = "code_run"  # {"ok": no error, "matched": output as expected}
    INTERVIEW_TAKE = "interview_take"  # {"question": text}: a recorded answer
    ACTIVE_TIME = "active_time"  # {"seconds": credited}: time spent actively on the topic page


class LearningEvent(Base):
    """One thing a student did in a topic. Append-only (a DB trigger enforces it)."""

    __tablename__ = "learning_events"
    __table_args__ = (Index("ix_learning_events_student_time", "student_id", "occurred_at"),)

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    student_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("students.id"))
    topic_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("topics.id"), index=True)
    component: Mapped[Component] = mapped_column(str_enum(Component, "content_component"))
    kind: Mapped[LearningEventKind] = mapped_column(str_enum(LearningEventKind, "event_kind"))
    version_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("content_versions.id"))
    data: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    occurred_at: Mapped[datetime] = mapped_column(server_default=func.now())


class TopicProgress(Base):
    """Where a student is in one topic: each section started or done, and when."""

    __tablename__ = "topic_progress"

    student_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("students.id"), primary_key=True)
    topic_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("topics.id"), primary_key=True)
    # {component: {"status": "started" | "done", "updated_at": iso, ...section details}}
    sections: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    last_component: Mapped[str | None] = mapped_column(String(32))
    first_visited_at: Mapped[datetime] = mapped_column(server_default=func.now())
    last_visited_at: Mapped[datetime] = mapped_column(server_default=func.now(), index=True)
    # Set when every published section is done; later content additions don't undo it.
    completed_at: Mapped[datetime | None]
    # Time spent actively on the topic page (visible, with recent input or media playing).
    active_seconds: Mapped[int] = mapped_column(default=0, server_default="0")


class QuizAttempt(UUIDPrimaryKey, Base):
    """A finished quiz, graded on the server against the published version. Append-only."""

    __tablename__ = "quiz_attempts"
    __table_args__ = (
        Index("ix_quiz_attempts_student_topic", "student_id", "topic_id", "submitted_at"),
    )

    student_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("students.id"))
    topic_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("topics.id"), index=True)
    version_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("content_versions.id"))
    attempt_number: Mapped[int]
    total: Mapped[int]
    correct: Mapped[int]
    score_pct: Mapped[Decimal] = mapped_column(Numeric(5, 2))
    duration_seconds: Mapped[int | None]
    submitted_at: Mapped[datetime] = mapped_column(server_default=func.now(), index=True)


class QuizResponse(Base):
    """One answer in an attempt. Append-only."""

    __tablename__ = "quiz_responses"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    attempt_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("quiz_attempts.id"), index=True)
    question_index: Mapped[int]
    chosen: Mapped[int | None]
    correct: Mapped[bool]
    difficulty: Mapped[str] = mapped_column(String(16))
    kind: Mapped[str] = mapped_column(String(16))
