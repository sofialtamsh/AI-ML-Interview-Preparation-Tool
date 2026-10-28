import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Any, Literal

from pydantic import Field, StringConstraints

from app.models import (
    ConnectorType,
    Decision,
    Difficulty,
    QuestionType,
    RecommendationKind,
    ReviewStatus,
    Trend,
)
from app.schemas.common import ApiModel
from app.schemas.sources import JobEventOut, JobSummary

Text200 = Annotated[str, StringConstraints(strip_whitespace=True, max_length=200)]
Note = Annotated[str, StringConstraints(strip_whitespace=True, max_length=1000)]

# --- Agents -------------------------------------------------------------------------------------


class AgentStatus(ApiModel):
    ai_configured: bool
    extraction_model: str
    research_model: str
    search_engine: str
    max_records_per_run: int
    max_cost_per_run_usd: Decimal
    role_presets: list[str]


class ExplorationStart(ApiModel):
    source_ids: list[uuid.UUID] = Field(min_length=1, max_length=20)
    fetch_first: bool = True
    max_records: int = Field(default=50, ge=1, le=1000)
    max_cost_usd: Decimal = Field(default=Decimal("1"), gt=0, le=100)


class ResearchStart(ApiModel):
    roles: list[
        Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=80)]
    ] = Field(min_length=1, max_length=6)
    focus: Text200 = ""
    region: Annotated[str, StringConstraints(strip_whitespace=True, max_length=60)] = "Global"
    months: int = Field(default=6, ge=1, le=24)
    sources_per_search: int = Field(default=5, ge=3, le=10)
    max_cost_usd: Decimal = Field(default=Decimal("0.50"), gt=0, le=100)


class AgentJob(JobSummary):
    source_name: str | None
    cost_usd: Decimal
    report_id: uuid.UUID | None


class AgentJobDetail(AgentJob):
    payload: dict[str, Any]
    events: list[JobEventOut]


class StartSkipped(ApiModel):
    source_id: uuid.UUID
    name: str | None
    reason: str


class StartResult(ApiModel):
    started: list[AgentJob]
    skipped: list[StartSkipped]


class ExplorationSource(ApiModel):
    id: uuid.UUID
    name: str
    connector_type: ConnectorType
    enabled: bool
    fetchable: bool
    record_count: int
    unexplored: int
    questions: int
    pending_review: int
    last_explored_at: datetime | None
    active_job: JobSummary | None


# --- Intelligence --------------------------------------------------------------------------------


class TopicRef(ApiModel):
    id: uuid.UUID
    slug: str
    name: str
    domain_name: str


class DomainOut(ApiModel):
    id: uuid.UUID
    slug: str
    name: str
    topics: list[TopicRef]


class ExperienceRef(ApiModel):
    id: uuid.UUID
    company: str | None
    role: str | None
    interview_date: date | None
    period: str | None
    location: str | None


class NamedRef(ApiModel):
    id: uuid.UUID
    name: str


class RecordRef(ApiModel):
    id: int
    title: str | None
    url: str | None


class QuestionItem(ApiModel):
    id: uuid.UUID
    original_text: str
    status: ReviewStatus
    grounded: bool
    question_type: QuestionType
    difficulty: Difficulty | None
    round: str | None
    topic: TopicRef | None
    suggested_topic: str | None
    technologies: list[str]
    duplicate_of_id: uuid.UUID | None
    experience: ExperienceRef
    source: NamedRef
    record: RecordRef
    created_at: datetime
    reviewed_by: str | None
    reviewed_at: datetime | None
    review_note: str | None
    # Distinct approved records in which this question (or a duplicate of it) appears.
    seen_in_records: int


class QuestionDetail(QuestionItem):
    context: str
    duplicates: list["DuplicateRef"]
    duplicate_of_text: str | None


class DuplicateRef(ApiModel):
    id: uuid.UUID
    original_text: str
    status: ReviewStatus
    company: str | None


class QuestionReview(ApiModel):
    status: Literal["approved", "rejected", "pending_review"] | None = None
    topic_id: uuid.UUID | None = None  # explicit null clears the topic
    difficulty: Difficulty | None = None
    round: Text200 | None = None
    duplicate_of_id: uuid.UUID | None = None  # explicit null: not a duplicate
    review_note: Note | None = None


class BulkReview(ApiModel):
    question_ids: list[uuid.UUID] = Field(min_length=1, max_length=200)
    status: Literal["approved", "rejected"]


class BulkReviewResult(ApiModel):
    updated: int


class ExperienceUpdate(ApiModel):
    company: Text200 | None = None
    role: Text200 | None = None
    interview_date: date | None = None
    period: Annotated[str, StringConstraints(strip_whitespace=True, max_length=100)] | None = None
    location: Text200 | None = None


class ResearchSignal(ApiModel):
    latest_trend: Trend | None
    findings: int
    reports: int
    last_seen: datetime | None


class TopicInsight(ApiModel):
    topic: TopicRef
    approved_questions: int
    interview_records: int
    pending_questions: int
    roles: list[str]
    research: ResearchSignal
    signal: Literal["asked_and_rising", "rising_in_market", "asked", "declining", "no_evidence"]


class IntelligenceSummary(ApiModel):
    pending_questions: int
    approved_questions: int
    rejected_questions: int
    interview_records: int
    topics_with_evidence: int
    pending_recommendations: int
    pending_research_questions: int
    reports: int
    last_exploration_at: datetime | None
    last_research_at: datetime | None


# --- Research -----------------------------------------------------------------------------------


class ReportSummary(ApiModel):
    id: uuid.UUID
    job_id: uuid.UUID
    title: str
    scope: dict[str, Any]
    model: str
    created_at: datetime
    triggered_by: str | None
    sources: int
    findings: int
    pending_recommendations: int
    questions: int


class ResearchSourceOut(ApiModel):
    id: int
    url: str
    title: str
    site: str
    excerpt: str
    accessed_at: datetime


class EvidenceOut(ApiModel):
    source_id: int
    quote: str | None
    quote_verified: bool


class FindingOut(ApiModel):
    id: int
    topic: TopicRef | None
    topic_label: str
    roles: list[str]
    skills: list[str]
    observation: str
    trend: Trend
    evidence: list[EvidenceOut]


class RecommendationOut(ApiModel):
    id: uuid.UUID
    report_id: uuid.UUID
    report_title: str
    kind: RecommendationKind
    topic: TopicRef | None
    domain: NamedRef | None
    proposed_name: str | None
    rationale: str
    finding_ids: list[int]
    status: Decision
    decided_by: str | None
    decided_at: datetime | None
    decision_note: str | None
    created_topic_id: uuid.UUID | None
    created_at: datetime


class ResearchQuestionOut(ApiModel):
    id: uuid.UUID
    text: str
    topic: TopicRef | None
    topic_label: str
    role: str | None
    rationale: str
    finding_ids: list[int]
    status: ReviewStatus


class ReportDetail(ReportSummary):
    summary: str
    source_list: list[ResearchSourceOut]
    finding_list: list[FindingOut]
    recommendations: list[RecommendationOut]
    question_list: list[ResearchQuestionOut]


class RecommendationDecision(ApiModel):
    decision: Literal["approved", "rejected", "deferred"]
    note: Note = ""


class ResearchQuestionReview(ApiModel):
    status: Literal["approved", "rejected", "pending_review"]
