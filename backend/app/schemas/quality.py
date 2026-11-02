"""Content quality, as the admin console sees it: automated checks, AI reviews, reviewer ratings,
revisions, retries, interview coverage and the pilot evaluation."""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Annotated, Any, Literal

from pydantic import Field, StringConstraints

from app.models import Component, VersionStatus
from app.schemas.common import ApiModel
from app.schemas.content import TopicRefOut


class CheckFinding(ApiModel):
    severity: Literal["warning", "error"]
    message: str
    where: str | None


class AutomatedCheck(ApiModel):
    key: str
    label: str
    status: Literal["passed", "warning", "error"]
    findings: list[CheckFinding]
    note: str | None


class AutomatedReport(ApiModel):
    checks: list[AutomatedCheck]
    errors: int
    warnings: int


class AiReviewOut(ApiModel):
    id: uuid.UUID
    created_at: datetime
    model: str
    summary: str
    scores: dict[str, int | None]
    average: float | None
    issues: list[dict[str, Any]]
    quiz_check: list[dict[str, Any]] | None
    dropped_issues: int
    requested_by: str | None


class Criterion(ApiModel):
    key: str
    label: str


class RatingOut(ApiModel):
    admin: str
    mine: bool
    scores: dict[str, int]
    average: float
    note: str | None
    created_at: datetime


class RatingSummary(ApiModel):
    criteria: list[Criterion]
    ratings: list[RatingOut]  # each admin's latest
    average: float | None


class QualityOut(ApiModel):
    automated: AutomatedReport
    ai_reviews: list[AiReviewOut]
    ratings: RatingSummary
    review_model: str
    ai_configured: bool


class AiReviewIn(ApiModel):
    max_cost_usd: Decimal = Field(default=Decimal("0.5"), gt=0, le=10)


class RatingIn(ApiModel):
    scores: dict[str, Annotated[int, Field(ge=1, le=5)]]
    note: Annotated[str, StringConstraints(strip_whitespace=True, max_length=1000)] | None = None


class ReviseIn(ApiModel):
    instructions: Annotated[str, StringConstraints(strip_whitespace=True, max_length=2000)] = ""
    use_review: bool = False
    max_cost_usd: Decimal = Field(default=Decimal("1"), gt=0, le=10)


class CoverageQuestion(ApiModel):
    id: uuid.UUID
    question: str
    role: str | None
    used: bool


class TopicInsights(ApiModel):
    spend_usd: Decimal
    runs: int
    interview_version: int | None
    interview_published: bool
    actual_questions: list[CoverageQuestion]
    research_questions: list[CoverageQuestion]


class PilotComponent(ApiModel):
    component: Component
    latest_number: int | None
    latest_status: VersionStatus | None
    published_number: int | None
    errors: int
    warnings: int
    ai_score: float | None
    rating: float | None
    ratings: int


class PilotTopic(ApiModel):
    topic: TopicRefOut
    components: list[PilotComponent]


class PilotTotals(ApiModel):
    components: int
    published: int
    with_errors: int
    ai_reviewed: int
    rated: int
    average_rating: float | None
    average_ai_score: float | None


class PilotEvaluation(ApiModel):
    expansion_approved: bool
    topics: list[PilotTopic]
    totals: PilotTotals
