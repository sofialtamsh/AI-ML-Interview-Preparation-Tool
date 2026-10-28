import uuid
from datetime import datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import BigInteger, ForeignKey, Identity, Index, String, Text, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.admin import AdminUser
from app.models.base import Base, UUIDPrimaryKey, str_enum


class JobKind(StrEnum):
    SOURCE_FETCH = "source_fetch"
    SOURCE_IMPORT = "source_import"
    EXPLORATION = "exploration"
    MARKET_RESEARCH = "market_research"
    CONTENT_GENERATION = "content_generation"
    CONTENT_NARRATION = "content_narration"


class JobStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    COMPLETED_WITH_ERRORS = "completed_with_errors"
    FAILED = "failed"
    CANCELLED = "cancelled"


ACTIVE_JOB_STATUSES = (JobStatus.QUEUED, JobStatus.RUNNING)


class Job(UUIDPrimaryKey, Base):
    """A unit of background work. Rows are never deleted: they are the execution history."""

    __tablename__ = "jobs"
    __table_args__ = (
        # One fetch or exploration at a time per source, enforced by the database rather than
        # by a race-prone check in application code.
        Index(
            "uq_jobs_one_active_run_per_source",
            "source_id",
            unique=True,
            postgresql_where=text(
                "kind IN ('source_fetch', 'exploration') AND status IN ('queued', 'running')"
            ),
        ),
    )

    kind: Mapped[JobKind] = mapped_column(str_enum(JobKind, "job_kind"), index=True)
    status: Mapped[JobStatus] = mapped_column(
        str_enum(JobStatus, "job_status"), default=JobStatus.QUEUED, index=True
    )
    source_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("interview_sources.id"), index=True
    )
    # Content jobs: the topic they work on, and the bulk batch they belong to.
    topic_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("topics.id"), index=True)
    batch_id: Mapped[uuid.UUID | None] = mapped_column(index=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    # Counters the handler reports (records seen / new / updated / unchanged, errors).
    result: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    progress_done: Mapped[int] = mapped_column(default=0)
    progress_total: Mapped[int | None]
    error: Mapped[str | None] = mapped_column(Text)
    attempts: Mapped[int] = mapped_column(default=0)
    cancel_requested: Mapped[bool] = mapped_column(default=False)
    triggered_by_admin_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("admin_users.id"), index=True
    )
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), index=True)
    started_at: Mapped[datetime | None]
    finished_at: Mapped[datetime | None]
    heartbeat_at: Mapped[datetime | None]

    triggered_by: Mapped[AdminUser | None] = relationship(lazy="joined")


class JobEventLevel(StrEnum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class JobEvent(Base):
    """A job's execution log. Append-only (enforced by a DB trigger); never holds secrets."""

    __tablename__ = "job_events"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    job_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("jobs.id"), index=True)
    level: Mapped[JobEventLevel] = mapped_column(str_enum(JobEventLevel, "job_event_level"))
    message: Mapped[str] = mapped_column(String(1000))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
