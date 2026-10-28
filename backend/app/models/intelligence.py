"""What the Interview Exploration Agent extracts from raw source records. Rows are never
deleted; review changes their status, and the audit log keeps who changed what."""

import uuid
from datetime import date, datetime
from enum import StrEnum

from sqlalchemy import BigInteger, ForeignKey, Identity, String, Text, func
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.admin import AdminUser
from app.models.base import Base, UUIDPrimaryKey, str_enum
from app.models.sources import InterviewSource, RawSourceRecord
from app.models.taxonomy import Topic


class ReviewStatus(StrEnum):
    PENDING = "pending_review"
    APPROVED = "approved"
    REJECTED = "rejected"


class ExtractionStatus(StrEnum):
    EXTRACTED = "extracted"
    NOT_INTERVIEW = "not_interview"  # the record isn't an interview experience
    FAILED = "failed"


class QuestionType(StrEnum):
    CONCEPTUAL = "conceptual"
    CODING = "coding"
    MATH = "math"
    ML_SYSTEM_DESIGN = "ml_system_design"
    CASE_STUDY = "case_study"
    PROJECT = "project"
    BEHAVIORAL = "behavioral"
    OTHER = "other"


class Difficulty(StrEnum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class RecordExtraction(Base):
    """One attempt to read one record. Append-only. A record with an `extracted` or
    `not_interview` attempt is never sent to the model again (no repeated spend)."""

    __tablename__ = "record_extractions"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    record_id: Mapped[int] = mapped_column(ForeignKey("raw_source_records.id"), index=True)
    source_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("interview_sources.id"), index=True)
    job_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("jobs.id"), index=True)
    status: Mapped[ExtractionStatus] = mapped_column(
        str_enum(ExtractionStatus, "extraction_status")
    )
    model: Mapped[str | None] = mapped_column(String(200))
    questions_found: Mapped[int] = mapped_column(default=0)
    error: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class InterviewExperience(UUIDPrimaryKey, Base):
    """One interview described in a record: who, for what role, when."""

    __tablename__ = "interview_experiences"

    source_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("interview_sources.id"), index=True)
    record_id: Mapped[int] = mapped_column(ForeignKey("raw_source_records.id"), index=True)
    job_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("jobs.id"), index=True)
    # Only kept when the name appears in the source text: never inferred.
    company: Mapped[str | None] = mapped_column(String(200), index=True)
    role: Mapped[str | None] = mapped_column(String(200), index=True)
    interview_date: Mapped[date | None]
    period: Mapped[str | None] = mapped_column(String(100))
    location: Mapped[str | None] = mapped_column(String(200))
    technologies: Mapped[list[str]] = mapped_column(ARRAY(String(100)), default=list)
    confidence: Mapped[float | None]
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())

    source: Mapped[InterviewSource] = relationship(lazy="joined")
    record: Mapped[RawSourceRecord] = relationship(lazy="joined")


class InterviewQuestion(UUIDPrimaryKey, Base):
    """An actual interview question, as written in the source. `original_text` is never edited."""

    __tablename__ = "interview_questions"

    experience_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("interview_experiences.id"), index=True
    )
    source_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("interview_sources.id"), index=True)
    record_id: Mapped[int] = mapped_column(ForeignKey("raw_source_records.id"), index=True)
    job_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("jobs.id"), index=True)
    original_text: Mapped[str] = mapped_column(Text)
    normalized_hash: Mapped[str] = mapped_column(String(64), index=True)
    round: Mapped[str | None] = mapped_column(String(120))
    question_type: Mapped[QuestionType] = mapped_column(str_enum(QuestionType, "question_type"))
    difficulty: Mapped[Difficulty | None] = mapped_column(str_enum(Difficulty, "difficulty"))
    topic_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("topics.id"), index=True)
    # The model's suggestion when no existing topic fits; a hint for taxonomy updates.
    suggested_topic: Mapped[str | None] = mapped_column(String(200))
    technologies: Mapped[list[str]] = mapped_column(ARRAY(String(100)), default=list)
    # True when the text appears (near) word-for-word in the source record.
    grounded: Mapped[bool]
    status: Mapped[ReviewStatus] = mapped_column(
        str_enum(ReviewStatus, "review_status"), default=ReviewStatus.PENDING, index=True
    )
    duplicate_of_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("interview_questions.id"), index=True
    )
    reviewed_by_admin_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("admin_users.id"))
    reviewed_at: Mapped[datetime | None]
    review_note: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), index=True)
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())

    experience: Mapped[InterviewExperience] = relationship(lazy="joined")
    topic: Mapped[Topic | None] = relationship(lazy="joined")
    reviewed_by: Mapped[AdminUser | None] = relationship(lazy="joined")
