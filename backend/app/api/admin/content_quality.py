"""Content quality in the studio (Phase 5): automated checks, AI reviews, reviewer ratings,
revising a version with AI, retrying what failed, interview coverage, and the pilot evaluation
an admin looks at before approving expansion.

AI reviews and revisions are background jobs started only by an admin, with a spending limit.
Nothing here publishes; AI reviews are advice, never verification."""

import uuid
from collections import defaultdict
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.ai import openrouter
from app.api.admin.agents import may_control, queue_job
from app.api.admin.content import (
    _get_content_job,
    _get_topic,
    _get_version,
    _require_ai,
    can_check,
    can_generate,
    can_read,
    content_jobs,
    topic_ref,
)
from app.auth.deps import AdminContext
from app.content.generation import TOPIC_WIDGETS
from app.content.quality import CheckContext, check_report
from app.content.review import mean, rating_criteria, review_average
from app.content.schemas import COMPONENT_ORDER
from app.content.service import expansion_approved, may_generate
from app.core.audit import record_audit
from app.core.config import get_settings
from app.core.db import get_db
from app.jobs.runner import notify_worker
from app.models import (
    ACTIVE_JOB_STATUSES,
    AdminUser,
    AiUsageEvent,
    Component,
    ContentItem,
    ContentRating,
    ContentVersion,
    Domain,
    InterviewExperience,
    InterviewQuestion,
    Job,
    JobEvent,
    JobEventLevel,
    JobKind,
    JobStatus,
    QualityReview,
    ResearchQuestion,
    ReviewStatus,
    Topic,
)
from app.schemas.content import ContentJob
from app.schemas.quality import (
    AiReviewIn,
    AiReviewOut,
    AutomatedReport,
    CoverageQuestion,
    Criterion,
    PilotComponent,
    PilotEvaluation,
    PilotTopic,
    PilotTotals,
    QualityOut,
    RatingIn,
    RatingOut,
    RatingSummary,
    ReviseIn,
    TopicInsights,
)

router = APIRouter(prefix="/content", tags=["admin-content-quality"])


# --- Quality of one version ----------------------------------------------------------------------


def _ratings(db: Session, version: ContentVersion, ctx: AdminContext) -> RatingSummary:
    criteria = rating_criteria(version.item.component)
    latest: dict[uuid.UUID, ContentRating] = {}
    for rating in db.scalars(
        select(ContentRating)
        .where(ContentRating.version_id == version.id)
        .order_by(ContentRating.id)
    ).unique():
        latest[rating.admin_id] = rating  # the last row per admin wins
    rows = [
        RatingOut(
            admin=r.admin.full_name,
            mine=r.admin_id == ctx.admin.id,
            scores=r.scores,
            average=mean([float(v) for v in r.scores.values()]) or 0.0,
            note=r.note,
            created_at=r.created_at,
        )
        for r in latest.values()
    ]
    return RatingSummary(
        criteria=[Criterion(key=k, label=v) for k, v in criteria.items()],
        ratings=sorted(rows, key=lambda r: r.created_at, reverse=True),
        average=mean([r.average for r in rows]),
    )


def _reviews(db: Session, version_id: uuid.UUID) -> list[AiReviewOut]:
    reviews = db.scalars(
        select(QualityReview)
        .where(QualityReview.version_id == version_id)
        .order_by(QualityReview.created_at.desc())
    ).all()
    ids = {r.requested_by_admin_id for r in reviews if r.requested_by_admin_id}
    names = dict(
        db.execute(select(AdminUser.id, AdminUser.full_name).where(AdminUser.id.in_(ids))).all()
    )
    return [
        AiReviewOut(
            id=r.id,
            created_at=r.created_at,
            model=r.model,
            summary=r.summary,
            scores=r.scores,
            average=review_average(r.scores),
            issues=r.issues,
            quiz_check=r.quiz_check,
            dropped_issues=r.dropped_issues,
            requested_by=names.get(r.requested_by_admin_id),
        )
        for r in reviews
    ]


@router.get("/versions/{version_id}/quality", response_model=QualityOut)
def version_quality(
    version_id: uuid.UUID,
    ctx: AdminContext = Depends(can_read),
    db: Session = Depends(get_db),
) -> QualityOut:
    version = _get_version(db, version_id)
    return QualityOut(
        automated=AutomatedReport.model_validate(check_report(db, version)),
        ai_reviews=_reviews(db, version.id),
        ratings=_ratings(db, version, ctx),
        review_model=get_settings().model_review,
        ai_configured=openrouter.ai_configured(),
    )


@router.post(
    "/versions/{version_id}/ai-review",
    response_model=ContentJob,
    status_code=status.HTTP_202_ACCEPTED,
)
def start_ai_review(
    version_id: uuid.UUID,
    body: AiReviewIn,
    request: Request,
    ctx: AdminContext = Depends(can_check),
    db: Session = Depends(get_db),
) -> ContentJob:
    _require_ai()
    version = _get_version(db, version_id)
    job = Job(
        kind=JobKind.CONTENT_REVIEW,
        topic_id=version.item.topic_id,
        payload={"version_id": str(version.id), "max_cost_usd": str(body.max_cost_usd)},
        triggered_by_admin_id=ctx.admin.id,
    )
    queue_job(db, job)
    record_audit(
        db,
        request,
        ctx,
        "content.ai_review_started",
        "content_version",
        version.id,
        {"max_cost_usd": str(body.max_cost_usd)},
    )
    db.commit()
    notify_worker()
    return content_jobs(db, [job])[0]


@router.post("/versions/{version_id}/ratings", response_model=RatingSummary, status_code=201)
def rate_version(
    version_id: uuid.UUID,
    body: RatingIn,
    request: Request,
    ctx: AdminContext = Depends(can_check),
    db: Session = Depends(get_db),
) -> RatingSummary:
    version = _get_version(db, version_id)
    expected = set(rating_criteria(version.item.component))
    if set(body.scores) != expected:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            f"Score each of: {', '.join(sorted(expected))}.",
        )
    db.add(
        ContentRating(
            version_id=version.id, admin_id=ctx.admin.id, scores=body.scores, note=body.note
        )
    )
    record_audit(
        db, request, ctx, "content.rated", "content_version", version.id, {"scores": body.scores}
    )
    db.commit()
    return _ratings(db, version, ctx)


@router.post(
    "/versions/{version_id}/revise",
    response_model=ContentJob,
    status_code=status.HTTP_202_ACCEPTED,
)
def revise_version(
    version_id: uuid.UUID,
    body: ReviseIn,
    request: Request,
    ctx: AdminContext = Depends(can_generate),
    db: Session = Depends(get_db),
) -> ContentJob:
    """A new draft rewritten from this version, following the admin's instructions and, if asked,
    the latest AI review. The version itself never changes."""
    _require_ai()
    version = _get_version(db, version_id)
    topic = version.item.topic
    if not may_generate(db, topic):
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Not a pilot topic, and content expansion hasn't been approved.",
        )
    if not body.instructions and not body.use_review:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "Say what to change, or use the AI review's findings.",
        )
    if body.use_review and not db.scalar(
        select(func.count()).where(QualityReview.version_id == version.id)
    ):
        raise HTTPException(
            status.HTTP_409_CONFLICT, "This version has no AI review yet. Run one first."
        )
    job = Job(
        kind=JobKind.CONTENT_GENERATION,
        topic_id=topic.id,
        payload={
            "components": [version.item.component.value],
            "use_intelligence": False,
            "max_cost_usd": str(body.max_cost_usd),
            "mode": "revise",
            "base_version_id": str(version.id),
            "instructions": body.instructions or None,
            "use_review": body.use_review,
        },
        triggered_by_admin_id=ctx.admin.id,
    )
    queue_job(db, job)
    record_audit(
        db,
        request,
        ctx,
        "content.revision_started",
        "content_version",
        version.id,
        {"use_review": body.use_review, "has_instructions": bool(body.instructions)},
    )
    db.commit()
    notify_worker()
    return content_jobs(db, [job])[0]


# --- Retrying a run ---------------------------------------------------------------------------


@router.post(
    "/jobs/{job_id}/retry", response_model=ContentJob, status_code=status.HTTP_202_ACCEPTED
)
def retry_content_job(
    job_id: uuid.UUID,
    request: Request,
    ctx: AdminContext = Depends(can_read),
    db: Session = Depends(get_db),
) -> ContentJob:
    """Run again only what didn't finish: the components a generation run didn't produce, the
    scenes a narration run didn't voice, or a review that didn't complete."""
    original = _get_content_job(db, job_id)
    if not may_control(ctx, original):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "You do not have permission to perform this action."
        )
    if original.status in ACTIVE_JOB_STATUSES:
        raise HTTPException(status.HTTP_409_CONFLICT, "This run is still in progress.")
    _require_ai()
    payload = dict(original.payload)
    if original.kind is JobKind.CONTENT_GENERATION:
        topic = db.get(Topic, original.topic_id) if original.topic_id else None
        if topic is None or not may_generate(db, topic):
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                "Not a pilot topic, and content expansion hasn't been approved.",
            )
        done = set(original.result.get("generated_components", []))
        if payload.get("mode") == "revise":
            remaining = [] if done else payload["components"]
        else:
            remaining = [c for c in payload["components"] if c not in done]
            if (
                original.status is JobStatus.SUCCEEDED
                and "generated_components" not in original.result
            ):
                remaining = []
        if not remaining:
            raise HTTPException(status.HTTP_409_CONFLICT, "Nothing is left to retry in this run.")
        payload["components"] = remaining
    elif original.status is JobStatus.SUCCEEDED:
        raise HTTPException(status.HTTP_409_CONFLICT, "This run finished; nothing to retry.")

    job = Job(
        kind=original.kind,
        topic_id=original.topic_id,
        batch_id=original.batch_id,
        payload=payload,
        triggered_by_admin_id=ctx.admin.id,
    )
    queue_job(db, job)
    db.add(
        JobEvent(job_id=job.id, level=JobEventLevel.INFO, message=f"Retry of run {original.id}.")
    )
    record_audit(
        db, request, ctx, "content.run_retried", "job", job.id, {"retry_of": str(original.id)}
    )
    db.commit()
    notify_worker()
    return content_jobs(db, [job])[0]


# --- Topic insights: spend and interview coverage ----------------------------------------------


@router.get(
    "/topics/{topic_id}/insights", response_model=TopicInsights, dependencies=[Depends(can_read)]
)
def topic_insights(topic_id: uuid.UUID, db: Session = Depends(get_db)) -> TopicInsights:
    topic = _get_topic(db, topic_id)
    spend = db.scalar(
        select(func.coalesce(func.sum(AiUsageEvent.cost_usd), 0))
        .join(Job, AiUsageEvent.job_id == Job.id)
        .where(Job.topic_id == topic.id)
    )
    runs = db.scalar(select(func.count()).where(Job.topic_id == topic.id)) or 0

    item = db.scalar(
        select(ContentItem).where(
            ContentItem.topic_id == topic.id, ContentItem.component == Component.INTERVIEW
        )
    )
    version = None
    if item is not None:
        version = (
            db.get(ContentVersion, item.published_version_id)
            if item.published_version_id
            else db.scalars(
                select(ContentVersion)
                .where(ContentVersion.item_id == item.id)
                .order_by(ContentVersion.number.desc())
                .limit(1)
            ).first()
        )
    refs = {q.get("source_ref") for q in version.body["questions"]} if version else set()

    actual = db.execute(
        select(InterviewQuestion.id, InterviewQuestion.original_text, InterviewExperience.role)
        .join(InterviewExperience, InterviewQuestion.experience_id == InterviewExperience.id)
        .where(
            InterviewQuestion.topic_id == topic.id,
            InterviewQuestion.status == ReviewStatus.APPROVED,
            InterviewQuestion.duplicate_of_id.is_(None),
        )
        .order_by(InterviewQuestion.created_at)
    ).all()
    research = db.execute(
        select(ResearchQuestion.id, ResearchQuestion.text).where(
            ResearchQuestion.topic_id == topic.id, ResearchQuestion.status == ReviewStatus.APPROVED
        )
    ).all()
    return TopicInsights(
        spend_usd=Decimal(spend or 0),
        runs=runs,
        interview_version=version.number if version else None,
        interview_published=bool(item and version and item.published_version_id == version.id),
        actual_questions=[
            CoverageQuestion(id=qid, question=text, role=role, used=str(qid) in refs)
            for qid, text, role in actual
        ],
        research_questions=[
            CoverageQuestion(id=qid, question=text, role=None, used=str(qid) in refs)
            for qid, text in research
        ],
    )


# --- Pilot evaluation --------------------------------------------------------------------------


@router.get("/pilot-evaluation", response_model=PilotEvaluation, dependencies=[Depends(can_read)])
def pilot_evaluation(db: Session = Depends(get_db)) -> PilotEvaluation:
    """Everything an admin needs to judge the pilot before giving the green signal to expand."""
    topics = db.scalars(
        select(Topic)
        .join(Domain, Topic.domain_id == Domain.id)
        .where(Topic.is_pilot, Topic.archived_at.is_(None))
        .order_by(Domain.position, Topic.position)
    ).unique()
    topics = list(topics)
    # Everything in a few batched queries: items, versions, reviews and ratings for all topics.
    items = list(
        db.scalars(select(ContentItem).where(ContentItem.topic_id.in_([t.id for t in topics])))
    )
    versions = (
        db.scalars(
            select(ContentVersion).where(ContentVersion.item_id.in_([i.id for i in items]))
        ).unique()
        if items
        else []
    )
    by_id = {v.id: v for v in versions}
    latest: dict[uuid.UUID, ContentVersion] = {}
    for version in by_id.values():
        if version.item_id not in latest or version.number > latest[version.item_id].number:
            latest[version.item_id] = version
    judged = {
        item.id: by_id.get(item.published_version_id) or latest.get(item.id)
        for item in items
        if item.published_version_id or item.id in latest
    }
    judged_ids = [v.id for v in judged.values() if v is not None]
    reviews: dict[uuid.UUID, QualityReview] = {}
    for review in db.scalars(
        select(QualityReview)
        .where(QualityReview.version_id.in_(judged_ids))
        .order_by(QualityReview.created_at)
    ):
        reviews[review.version_id] = review  # the newest wins
    ratings: dict[uuid.UUID, dict[uuid.UUID, ContentRating]] = defaultdict(dict)
    for rating in db.scalars(
        select(ContentRating)
        .where(ContentRating.version_id.in_(judged_ids))
        .order_by(ContentRating.id)
    ).unique():
        ratings[rating.version_id][rating.admin_id] = rating  # each admin's latest
    checks = CheckContext(db)
    items_by_topic: dict[uuid.UUID, dict[Component, ContentItem]] = defaultdict(dict)
    for item in items:
        items_by_topic[item.topic_id][item.component] = item

    result: list[PilotTopic] = []
    for topic in topics:
        rows = []
        for component in COMPONENT_ORDER:
            if component is Component.PLAYGROUND and topic.slug not in TOPIC_WIDGETS:
                continue
            item = items_by_topic[topic.id].get(component)
            newest = latest.get(item.id) if item else None
            published = by_id.get(item.published_version_id) if item else None
            version = judged.get(item.id) if item else None  # what students see, else the draft
            report = check_report(db, version, checks) if version else {"errors": 0, "warnings": 0}
            review = reviews.get(version.id) if version else None
            averages = [
                mean([float(v) for v in r.scores.values()]) or 0.0
                for r in (ratings.get(version.id, {}).values() if version else [])
            ]
            rows.append(
                PilotComponent(
                    component=component,
                    latest_number=newest.number if newest else None,
                    latest_status=newest.status if newest else None,
                    published_number=published.number if published else None,
                    errors=report["errors"],
                    warnings=report["warnings"],
                    ai_score=review_average(review.scores) if review else None,
                    rating=mean(averages),
                    ratings=len(averages),
                )
            )
        result.append(PilotTopic(topic=topic_ref(topic), components=rows))

    every = [c for t in result for c in t.components]
    by_kind: dict[str, list[float]] = defaultdict(list)
    for c in every:
        if c.rating is not None:
            by_kind["rating"].append(c.rating)
        if c.ai_score is not None:
            by_kind["ai"].append(c.ai_score)
    return PilotEvaluation(
        expansion_approved=expansion_approved(db),
        topics=result,
        totals=PilotTotals(
            components=len(every),
            published=sum(c.published_number is not None for c in every),
            with_errors=sum(c.errors > 0 for c in every),
            ai_reviewed=len(by_kind["ai"]),
            rated=len(by_kind["rating"]),
            average_rating=mean(by_kind["rating"]),
            average_ai_score=mean(by_kind["ai"]),
        ),
    )
