"""Interview intelligence: review what the Exploration Agent extracted, and see topics in the
light of both approved interview evidence and current market research.

Counts only ever come from approved records; nothing here invents a frequency."""

import uuid
from collections import Counter, defaultdict
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session

from app.auth.deps import AdminContext, require_any_permission, require_permission
from app.auth.permissions import Perm
from app.core.audit import record_audit
from app.core.db import get_db
from app.core.security import utcnow
from app.models import (
    CurriculumRecommendation,
    Decision,
    Domain,
    InterviewExperience,
    InterviewQuestion,
    RecordExtraction,
    ResearchFinding,
    ResearchQuestion,
    ResearchReport,
    ReviewStatus,
    Topic,
    Trend,
)
from app.schemas.common import Page
from app.schemas.intelligence import (
    BulkReview,
    BulkReviewResult,
    DomainOut,
    DuplicateRef,
    ExperienceRef,
    ExperienceUpdate,
    IntelligenceSummary,
    NamedRef,
    QuestionDetail,
    QuestionItem,
    QuestionReview,
    RecordRef,
    ResearchSignal,
    TopicInsight,
    TopicRef,
)

router = APIRouter(prefix="/intelligence", tags=["admin-intelligence"])

can_view = require_permission(Perm.INTELLIGENCE_VIEW)
can_review = require_permission(Perm.INTELLIGENCE_REVIEW)
CONTEXT_CHARS = 500


def topic_ref(topic: Topic | None) -> TopicRef | None:
    if topic is None:
        return None
    return TopicRef(id=topic.id, slug=topic.slug, name=topic.name, domain_name=topic.domain.name)


def _cluster(question: InterviewQuestion) -> uuid.UUID:
    return question.duplicate_of_id or question.id


def _seen_in(db: Session, clusters: set[uuid.UUID]) -> dict[uuid.UUID, int]:
    """Distinct approved records per question cluster (a question plus its duplicates)."""
    if not clusters:
        return {}
    cluster = func.coalesce(InterviewQuestion.duplicate_of_id, InterviewQuestion.id)
    rows = db.execute(
        select(cluster, func.count(func.distinct(InterviewQuestion.record_id)))
        .where(cluster.in_(clusters), InterviewQuestion.status == ReviewStatus.APPROVED)
        .group_by(cluster)
    )
    return dict(rows.all())


def _items(db: Session, questions: list[InterviewQuestion]) -> list[QuestionItem]:
    seen = _seen_in(db, {_cluster(q) for q in questions})
    return [
        QuestionItem(
            id=q.id,
            original_text=q.original_text,
            status=q.status,
            grounded=q.grounded,
            question_type=q.question_type,
            difficulty=q.difficulty,
            round=q.round,
            topic=topic_ref(q.topic),
            suggested_topic=q.suggested_topic,
            technologies=q.technologies,
            duplicate_of_id=q.duplicate_of_id,
            experience=ExperienceRef.model_validate(q.experience),
            source=NamedRef(id=q.experience.source.id, name=q.experience.source.name),
            record=RecordRef(
                id=q.experience.record.id,
                title=q.experience.record.title,
                url=q.experience.record.url,
            ),
            created_at=q.created_at,
            reviewed_by=q.reviewed_by.full_name if q.reviewed_by else None,
            reviewed_at=q.reviewed_at,
            review_note=q.review_note,
            seen_in_records=seen.get(_cluster(q), 0),
        )
        for q in questions
    ]


def _get_question(db: Session, question_id: uuid.UUID) -> InterviewQuestion:
    question = db.get(InterviewQuestion, question_id)
    if question is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Question not found.")
    return question


# --- Taxonomy & summary ---------------------------------------------------------------------------


@router.get(
    "/taxonomy",
    response_model=list[DomainOut],
    dependencies=[
        Depends(
            require_any_permission(Perm.INTELLIGENCE_VIEW, Perm.AGENTS_VIEW, Perm.TAXONOMY_MANAGE)
        )
    ],
)
def taxonomy(db: Session = Depends(get_db)) -> list[DomainOut]:
    domains = db.scalars(
        select(Domain).where(Domain.archived_at.is_(None)).order_by(Domain.position)
    ).all()
    return [
        DomainOut(
            id=d.id,
            slug=d.slug,
            name=d.name,
            topics=[topic_ref(t) for t in d.topics if t.archived_at is None],
        )
        for d in domains
    ]


@router.get("/summary", response_model=IntelligenceSummary, dependencies=[Depends(can_view)])
def summary(db: Session = Depends(get_db)) -> IntelligenceSummary:
    by_status = dict(
        db.execute(
            select(InterviewQuestion.status, func.count()).group_by(InterviewQuestion.status)
        ).all()
    )
    approved = InterviewQuestion.status == ReviewStatus.APPROVED
    return IntelligenceSummary(
        pending_questions=by_status.get(ReviewStatus.PENDING, 0),
        approved_questions=by_status.get(ReviewStatus.APPROVED, 0),
        rejected_questions=by_status.get(ReviewStatus.REJECTED, 0),
        interview_records=db.scalar(
            select(func.count(func.distinct(InterviewQuestion.record_id))).where(approved)
        )
        or 0,
        topics_with_evidence=db.scalar(
            select(func.count(func.distinct(InterviewQuestion.topic_id))).where(
                approved, InterviewQuestion.topic_id.is_not(None)
            )
        )
        or 0,
        pending_recommendations=db.scalar(
            select(func.count()).where(CurriculumRecommendation.status == Decision.PENDING)
        )
        or 0,
        pending_research_questions=db.scalar(
            select(func.count()).where(ResearchQuestion.status == ReviewStatus.PENDING)
        )
        or 0,
        reports=db.scalar(select(func.count()).select_from(ResearchReport)) or 0,
        last_exploration_at=db.scalar(select(func.max(RecordExtraction.created_at))),
        last_research_at=db.scalar(select(func.max(ResearchReport.created_at))),
    )


# --- Questions ------------------------------------------------------------------------------------


def _question_filters(
    query: Select[tuple[InterviewQuestion]],
    *,
    status_filter: ReviewStatus | None,
    topic_id: uuid.UUID | None,
    source_id: uuid.UUID | None,
    q: str | None,
    hide_duplicates: bool,
    not_grounded: bool,
) -> Select[tuple[InterviewQuestion]]:
    if status_filter is not None:
        query = query.where(InterviewQuestion.status == status_filter)
    if topic_id is not None:
        query = query.where(InterviewQuestion.topic_id == topic_id)
    if source_id is not None:
        query = query.where(InterviewQuestion.source_id == source_id)
    if hide_duplicates:
        query = query.where(InterviewQuestion.duplicate_of_id.is_(None))
    if not_grounded:
        query = query.where(InterviewQuestion.grounded.is_(False))
    if q and q.strip():
        pattern = f"%{q.strip()}%"
        query = query.where(
            or_(
                InterviewQuestion.original_text.ilike(pattern),
                InterviewExperience.company.ilike(pattern),
                InterviewExperience.role.ilike(pattern),
            )
        )
    return query


@router.get("/questions", response_model=Page[QuestionItem], dependencies=[Depends(can_view)])
def list_questions(
    status_filter: ReviewStatus | None = Query(default=None, alias="status"),
    topic_id: uuid.UUID | None = None,
    source_id: uuid.UUID | None = None,
    q: str | None = Query(default=None, max_length=200),
    hide_duplicates: bool = False,
    not_grounded: bool = False,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> Page[QuestionItem]:
    base = select(InterviewQuestion).join(
        InterviewExperience, InterviewQuestion.experience_id == InterviewExperience.id
    )
    filtered = _question_filters(
        base,
        status_filter=status_filter,
        topic_id=topic_id,
        source_id=source_id,
        q=q,
        hide_duplicates=hide_duplicates,
        not_grounded=not_grounded,
    )
    total = db.scalar(select(func.count()).select_from(filtered.subquery())) or 0
    questions = db.scalars(
        filtered.order_by(
            InterviewQuestion.created_at.desc(),
            InterviewQuestion.experience_id,
            InterviewQuestion.id,
        )
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).unique()
    return Page(items=_items(db, list(questions)), total=total, page=page, page_size=page_size)


def _context(content: str, text: str) -> str:
    """The part of the record around the question, so a reviewer can check it in place."""
    at = content.lower().find(text.lower()[:80])
    if at < 0:
        return content[: CONTEXT_CHARS * 2]
    start = max(0, at - CONTEXT_CHARS)
    end = min(len(content), at + len(text) + CONTEXT_CHARS)
    return ("…" if start else "") + content[start:end] + ("…" if end < len(content) else "")


def _detail(db: Session, question: InterviewQuestion) -> QuestionDetail:
    cluster = _cluster(question)
    related = db.scalars(
        select(InterviewQuestion)
        .where(
            or_(InterviewQuestion.duplicate_of_id == cluster, InterviewQuestion.id == cluster),
            InterviewQuestion.id != question.id,
        )
        .order_by(InterviewQuestion.created_at)
        .limit(50)
    ).unique()
    canonical = (
        db.get(InterviewQuestion, question.duplicate_of_id) if question.duplicate_of_id else None
    )
    return QuestionDetail(
        **_items(db, [question])[0].model_dump(),
        context=_context(question.experience.record.content, question.original_text),
        duplicates=[
            DuplicateRef(
                id=r.id,
                original_text=r.original_text,
                status=r.status,
                company=r.experience.company,
            )
            for r in related
        ],
        duplicate_of_text=canonical.original_text if canonical else None,
    )


@router.get(
    "/questions/{question_id}", response_model=QuestionDetail, dependencies=[Depends(can_view)]
)
def get_question(question_id: uuid.UUID, db: Session = Depends(get_db)) -> QuestionDetail:
    return _detail(db, _get_question(db, question_id))


def _mark_reviewed(question: InterviewQuestion, ctx: AdminContext) -> None:
    question.reviewed_by_admin_id = ctx.admin.id
    question.reviewed_at = utcnow()


@router.patch("/questions/{question_id}", response_model=QuestionDetail)
def review_question(
    question_id: uuid.UUID,
    body: QuestionReview,
    request: Request,
    ctx: AdminContext = Depends(can_review),
    db: Session = Depends(get_db),
) -> QuestionDetail:
    question = _get_question(db, question_id)
    sent = body.model_fields_set
    changes: dict[str, Any] = {}

    def change(field: str, value: Any, shown: Any = None) -> None:
        if getattr(question, field) != value:
            before = getattr(question, field)
            after = shown if shown is not None else value
            changes[field] = {
                "from": str(before) if before is not None else None,
                "to": str(after) if after is not None else None,
            }
            setattr(question, field, value)

    if "status" in sent and body.status:
        change("status", ReviewStatus(body.status), body.status)
    if "topic_id" in sent:
        if body.topic_id and db.get(Topic, body.topic_id) is None:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Topic not found.")
        change("topic_id", body.topic_id)
    if "difficulty" in sent:
        change("difficulty", body.difficulty)
    if "round" in sent:
        change("round", body.round or None)
    if "duplicate_of_id" in sent:
        target = body.duplicate_of_id
        if target is not None:
            if target == question.id:
                raise HTTPException(
                    status.HTTP_422_UNPROCESSABLE_CONTENT, "A question can't duplicate itself."
                )
            canonical = _get_question(db, target)
            target = _cluster(canonical)  # always point at the original of a cluster
            if target == question.id:
                raise HTTPException(
                    status.HTTP_422_UNPROCESSABLE_CONTENT,
                    "That question is already marked as a duplicate of this one.",
                )
        change("duplicate_of_id", target)
    if "review_note" in sent:
        question.review_note = body.review_note or None
    if changes:
        _mark_reviewed(question, ctx)
        record_audit(
            db,
            request,
            ctx,
            "intelligence.question_reviewed",
            "interview_question",
            question.id,
            changes,
        )
    db.commit()
    db.refresh(question)  # load the reviewer just set
    return _detail(db, question)


@router.post("/questions/review", response_model=BulkReviewResult)
def bulk_review(
    body: BulkReview,
    request: Request,
    ctx: AdminContext = Depends(can_review),
    db: Session = Depends(get_db),
) -> BulkReviewResult:
    questions = db.scalars(
        select(InterviewQuestion).where(InterviewQuestion.id.in_(body.question_ids))
    ).unique()
    target = ReviewStatus(body.status)
    updated = 0
    for question in questions:
        if question.status is not target:
            question.status = target
            _mark_reviewed(question, ctx)
            updated += 1
    if updated:
        record_audit(
            db,
            request,
            ctx,
            "intelligence.questions_reviewed",
            "interview_question",
            None,
            {"status": body.status, "count": updated},
        )
    db.commit()
    return BulkReviewResult(updated=updated)


@router.patch("/experiences/{experience_id}", response_model=ExperienceRef)
def correct_experience(
    experience_id: uuid.UUID,
    body: ExperienceUpdate,
    request: Request,
    ctx: AdminContext = Depends(can_review),
    db: Session = Depends(get_db),
) -> ExperienceRef:
    """Reviewers correct who/what/when. The audit log keeps every original value."""
    experience = db.get(InterviewExperience, experience_id)
    if experience is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Interview not found.")
    changes: dict[str, Any] = {}
    for field in body.model_fields_set:
        value = getattr(body, field)
        value = value or None if isinstance(value, str) else value
        if getattr(experience, field) != value:
            before = getattr(experience, field)
            changes[field] = {
                "from": str(before) if before is not None else None,
                "to": str(value) if value is not None else None,
            }
            setattr(experience, field, value)
    if changes:
        record_audit(
            db,
            request,
            ctx,
            "intelligence.interview_corrected",
            "interview_experience",
            experience.id,
            changes,
        )
        db.commit()
    return ExperienceRef.model_validate(experience)


# --- Topics: interview evidence beside market research ------------------------------------------

_RISING = {Trend.RISING, Trend.EMERGING}


def _signal(records: int, trend: Trend | None) -> str:
    """A transparent label, never a score: which kinds of evidence point at the topic."""
    if trend is Trend.DECLINING:
        return "declining"
    if records and trend in _RISING:
        return "asked_and_rising"
    if trend in _RISING:
        return "rising_in_market"
    if records:
        return "asked"
    return "no_evidence"


@router.get("/topics", response_model=list[TopicInsight], dependencies=[Depends(can_view)])
def topic_insights(db: Session = Depends(get_db)) -> list[TopicInsight]:
    topics = db.scalars(
        select(Topic)
        .join(Domain, Topic.domain_id == Domain.id)
        .where(Topic.archived_at.is_(None), Domain.archived_at.is_(None))
        .order_by(Domain.position, Topic.position)
    ).all()
    approved = InterviewQuestion.status == ReviewStatus.APPROVED
    evidence = {
        topic_id: (questions, records)
        for topic_id, questions, records in db.execute(
            select(
                InterviewQuestion.topic_id,
                func.count(),
                func.count(func.distinct(InterviewQuestion.record_id)),
            )
            .where(approved, InterviewQuestion.topic_id.is_not(None))
            .group_by(InterviewQuestion.topic_id)
        )
    }
    pending = dict(
        db.execute(
            select(InterviewQuestion.topic_id, func.count())
            .where(InterviewQuestion.status == ReviewStatus.PENDING)
            .group_by(InterviewQuestion.topic_id)
        ).all()
    )
    roles: dict[uuid.UUID, Counter[str]] = defaultdict(Counter)
    for topic_id, role in db.execute(
        select(InterviewQuestion.topic_id, InterviewExperience.role)
        .join(InterviewExperience, InterviewQuestion.experience_id == InterviewExperience.id)
        .where(
            approved, InterviewQuestion.topic_id.is_not(None), InterviewExperience.role.is_not(None)
        )
    ):
        roles[topic_id][role] += 1

    research: dict[uuid.UUID, dict[str, Any]] = {}
    for topic_id, trend, report_id, created_at in db.execute(
        select(
            ResearchFinding.topic_id,
            ResearchFinding.trend,
            ResearchFinding.report_id,
            ResearchFinding.created_at,
        )
        .where(ResearchFinding.topic_id.is_not(None))
        .order_by(ResearchFinding.created_at)
    ):
        entry = research.setdefault(
            topic_id, {"findings": 0, "reports": set(), "trend": None, "last": None}
        )
        entry["findings"] += 1
        entry["reports"].add(report_id)
        entry["trend"], entry["last"] = trend, created_at  # newest wins (ordered ascending)

    insights = []
    for topic in topics:
        questions, records = evidence.get(topic.id, (0, 0))
        found = research.get(topic.id)
        trend = found["trend"] if found else None
        insights.append(
            TopicInsight(
                topic=topic_ref(topic),
                approved_questions=questions,
                interview_records=records,
                pending_questions=pending.get(topic.id, 0),
                roles=[role for role, _ in roles[topic.id].most_common(4)],
                research=ResearchSignal(
                    latest_trend=trend,
                    findings=found["findings"] if found else 0,
                    reports=len(found["reports"]) if found else 0,
                    last_seen=found["last"] if found else None,
                ),
                signal=_signal(records, trend),
            )
        )
    return insights
