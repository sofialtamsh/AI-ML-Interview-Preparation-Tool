"""Learning progress as the student app and the admin console receive it."""

import uuid
from datetime import date, datetime
from typing import Annotated, Any, Literal

from pydantic import Field, StringConstraints

from app.models import Component, LearningEventKind
from app.progress.service import MAX_TIME_REPORT
from app.schemas.common import ApiModel

SectionStatus = Literal["done", "started", "not_started"]
Band = Literal["strong", "developing", "needs_work", "not_enough_evidence"]


class EventIn(ApiModel):
    topic: Annotated[str, StringConstraints(max_length=300)]
    component: Component
    kind: LearningEventKind
    data: dict[str, Any] = Field(default_factory=dict, max_length=4)


class TimeIn(ApiModel):
    topic: Annotated[str, StringConstraints(max_length=300)]
    component: Component
    seconds: int = Field(ge=1, le=MAX_TIME_REPORT)


class QuizSubmitIn(ApiModel):
    topic: Annotated[str, StringConstraints(max_length=300)]
    version_id: uuid.UUID
    answers: list[int | None] = Field(max_length=30)
    duration_seconds: int | None = Field(default=None, ge=0, le=24 * 3600)


class QuizResult(ApiModel):
    attempt_number: int
    correct: int
    total: int
    score_pct: float
    best_pct: float


class TopicProgressOut(ApiModel):
    sections: dict[str, SectionStatus]
    last_section: str | None
    completed: bool
    quiz: dict[str, float | int | None]
    answered_questions: list[str]


class Mastery(ApiModel):
    score: float | None
    band: Band
    quiz_average: float | None
    practice_average: float | None


class TopicSummary(ApiModel):
    slug: str
    name: str
    domain: str
    sections: dict[str, SectionStatus]
    done: int
    total: int
    completion: int
    completed: bool
    started: bool
    last_visited_at: datetime | None
    last_section: str | None
    quiz_attempts: int
    quiz_best: float | None
    quiz_last: float | None
    interview_takes: int
    active_seconds: int
    mastery: Mastery


class ContinueTopic(TopicSummary):
    next_section: str | None


class RecommendedTopic(TopicSummary):
    reason: str


class DomainProgress(ApiModel):
    name: str
    done: int
    total: int
    completion: int


class RecentQuiz(ApiModel):
    topic: str
    slug: str | None
    score_pct: float
    correct: int
    total: int
    attempt_number: int
    submitted_at: datetime


class InterviewProgress(ApiModel):
    answers_recorded: int
    feedback_count: int
    average_score: float | None
    recent_scores: list[dict[str, Any]]


class Activity(ApiModel):
    streak_days: int
    active_days_this_week: int
    active_days_last_30: int
    last_active_at: datetime | None
    learning_seconds: int
    learning_seconds_last_7: int


class AttemptResponse(ApiModel):
    question_index: int
    prompt: str
    chosen: int | None
    correct: bool
    difficulty: str


class QuizAttemptOut(ApiModel):
    id: uuid.UUID
    topic: str
    topic_slug: str | None
    attempt_number: int
    correct: int
    total: int
    score_pct: float
    duration_seconds: int | None
    submitted_at: datetime
    responses: list[AttemptResponse]


class PracticeScore(ApiModel):
    topic: str
    question: str
    score: float | None
    verdict: str | None
    deleted: bool
    created_at: datetime


class TimelineEntry(ApiModel):
    at: datetime
    topic: str
    section: str
    action: str


class ProgressSummary(ApiModel):
    overall_completion: int
    sections_done: int
    sections_total: int
    topics_completed: int
    topics_started: int
    topics: list[TopicSummary]
    domains: list[DomainProgress]
    continue_: ContinueTopic | None = Field(alias="continue", serialization_alias="continue")
    recommended: list[RecommendedTopic]
    recent_quizzes: list[RecentQuiz]
    quiz_average: float | None
    strengths: list[str]
    weaknesses: list[str]
    interview: InterviewProgress
    activity: Activity


class StudentLearning(ApiModel):
    """A student's learning, for admins with students.view."""

    summary: ProgressSummary
    quiz_attempts: list[QuizAttemptOut]
    practice: list[PracticeScore]
    timeline: list[TimelineEntry]


# --- Analytics (admin) ------------------------------------------------------------------------


class AnalyticsReport(ApiModel):
    range: dict[str, date]
    kpis: dict[str, int | float | None]
    registrations: list[dict[str, Any]]
    weekly_active: list[dict[str, Any]]
    score_distribution: list[dict[str, int]]
    topics: list[dict[str, Any]]
    domains: list[dict[str, Any]]
    weak_topics: list[dict[str, Any]]
    cohorts: list[dict[str, Any]]
    student: dict[str, str] | None
    filters: dict[str, list[dict[str, str]]]
