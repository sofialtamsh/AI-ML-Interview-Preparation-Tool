"""What the Market Research Agent produces. Reports and their evidence are append-only;
recommendations and suggested questions only change status when an admin decides."""

import uuid
from datetime import datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import BigInteger, ForeignKey, Identity, String, Text, func
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.admin import AdminUser
from app.models.base import Base, UUIDPrimaryKey, str_enum
from app.models.intelligence import ReviewStatus
from app.models.taxonomy import Domain, Topic


class Trend(StrEnum):
    EMERGING = "emerging"
    RISING = "rising"
    STABLE = "stable"
    DECLINING = "declining"
    UNCLEAR = "unclear"


class RecommendationKind(StrEnum):
    ADD_TOPIC = "add_topic"
    PRIORITIZE = "prioritize"
    DEPRIORITIZE = "deprioritize"
    UPDATE_CONTENT = "update_content"


class Decision(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    DEFERRED = "deferred"


class ResearchReport(UUIDPrimaryKey, Base):
    __tablename__ = "research_reports"

    job_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("jobs.id"), unique=True)
    title: Mapped[str] = mapped_column(String(300))
    # What was asked: roles, focus, region, time window.
    scope: Mapped[dict[str, Any]] = mapped_column(JSONB)
    summary: Mapped[str] = mapped_column(Text)
    model: Mapped[str] = mapped_column(String(200))
    triggered_by_admin_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("admin_users.id"))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), index=True)

    triggered_by: Mapped[AdminUser | None] = relationship(lazy="joined")


class ResearchSource(Base):
    """A web page the research was based on, with the excerpt the search returned."""

    __tablename__ = "research_sources"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    report_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("research_reports.id"), index=True)
    url: Mapped[str] = mapped_column(String(2048))
    title: Mapped[str] = mapped_column(String(500))
    site: Mapped[str] = mapped_column(String(255))
    excerpt: Mapped[str] = mapped_column(Text)
    accessed_at: Mapped[datetime] = mapped_column(server_default=func.now())


class ResearchFinding(Base):
    """One observation about a topic or skill. Every finding cites at least one source."""

    __tablename__ = "research_findings"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    report_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("research_reports.id"), index=True)
    topic_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("topics.id"), index=True)
    topic_label: Mapped[str] = mapped_column(String(200))
    roles: Mapped[list[str]] = mapped_column(ARRAY(String(120)), default=list)
    skills: Mapped[list[str]] = mapped_column(ARRAY(String(120)), default=list)
    observation: Mapped[str] = mapped_column(Text)
    trend: Mapped[Trend] = mapped_column(str_enum(Trend, "trend"))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    topic: Mapped[Topic | None] = relationship(lazy="joined")


class FindingEvidence(Base):
    __tablename__ = "finding_evidence"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    finding_id: Mapped[int] = mapped_column(ForeignKey("research_findings.id"), index=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("research_sources.id"), index=True)
    quote: Mapped[str | None] = mapped_column(Text)
    # True when the quote was found in the excerpt the search engine returned.
    quote_verified: Mapped[bool] = mapped_column(default=False)


class CurriculumRecommendation(UUIDPrimaryKey, Base):
    """A suggestion only. Approving it may add a topic to the taxonomy; it never generates
    or publishes content."""

    __tablename__ = "curriculum_recommendations"

    report_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("research_reports.id"), index=True)
    kind: Mapped[RecommendationKind] = mapped_column(
        str_enum(RecommendationKind, "recommendation_kind")
    )
    topic_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("topics.id"))
    domain_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("domains.id"))
    proposed_name: Mapped[str | None] = mapped_column(String(200))
    rationale: Mapped[str] = mapped_column(Text)
    finding_ids: Mapped[list[int]] = mapped_column(ARRAY(BigInteger), default=list)
    status: Mapped[Decision] = mapped_column(
        str_enum(Decision, "decision"), default=Decision.PENDING, index=True
    )
    decided_by_admin_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("admin_users.id"))
    decided_at: Mapped[datetime | None]
    decision_note: Mapped[str | None] = mapped_column(String(1000))
    created_topic_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("topics.id"))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    topic: Mapped[Topic | None] = relationship(foreign_keys=[topic_id], lazy="joined")
    domain: Mapped[Domain | None] = relationship(lazy="joined")
    decided_by: Mapped[AdminUser | None] = relationship(lazy="joined")


class ResearchQuestion(UUIDPrimaryKey, Base):
    """A research-derived interview question: based on what the market asks for, *not* an
    actual interview question. Kept separate so the two can never be confused."""

    __tablename__ = "research_questions"

    report_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("research_reports.id"), index=True)
    text: Mapped[str] = mapped_column(Text)
    topic_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("topics.id"), index=True)
    topic_label: Mapped[str] = mapped_column(String(200))
    role: Mapped[str | None] = mapped_column(String(120))
    rationale: Mapped[str] = mapped_column(Text)
    finding_ids: Mapped[list[int]] = mapped_column(ARRAY(BigInteger), default=list)
    status: Mapped[ReviewStatus] = mapped_column(
        str_enum(ReviewStatus, "review_status"), default=ReviewStatus.PENDING, index=True
    )
    reviewed_by_admin_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("admin_users.id"))
    reviewed_at: Mapped[datetime | None]
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    topic: Mapped[Topic | None] = relationship(lazy="joined")
