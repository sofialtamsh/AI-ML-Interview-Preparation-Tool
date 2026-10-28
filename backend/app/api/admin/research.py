"""Market research reports, curriculum recommendations and research-derived questions.

Deciding on a recommendation never generates content. Approving "add a topic" adds it to the
taxonomy (not as a pilot topic), so content for it stays blocked by the pilot gate."""

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.admin.intelligence import topic_ref
from app.auth.deps import AdminContext, require_any_permission, require_permission
from app.auth.permissions import Perm
from app.core.audit import record_audit
from app.core.db import get_db
from app.core.security import utcnow
from app.intelligence.taxonomy import topic_slug
from app.models import (
    CurriculumRecommendation,
    Decision,
    Domain,
    FindingEvidence,
    RecommendationKind,
    ResearchFinding,
    ResearchQuestion,
    ResearchReport,
    ResearchSource,
    ReviewStatus,
    Topic,
)
from app.schemas.common import Page
from app.schemas.intelligence import (
    EvidenceOut,
    FindingOut,
    NamedRef,
    RecommendationDecision,
    RecommendationOut,
    ReportDetail,
    ReportSummary,
    ResearchQuestionOut,
    ResearchQuestionReview,
    ResearchSourceOut,
)

router = APIRouter(prefix="/research", tags=["admin-research"])

can_read = require_any_permission(Perm.AGENTS_VIEW, Perm.INTELLIGENCE_VIEW, Perm.TAXONOMY_MANAGE)


def _summaries(db: Session, reports: list[ResearchReport]) -> list[ReportSummary]:
    ids = [r.id for r in reports]

    def counts(column: Any, *conditions: Any) -> dict[uuid.UUID, int]:
        return dict(
            db.execute(
                select(column, func.count()).where(column.in_(ids), *conditions).group_by(column)
            ).all()
        )

    sources = counts(ResearchSource.report_id)
    findings = counts(ResearchFinding.report_id)
    pending = counts(
        CurriculumRecommendation.report_id, CurriculumRecommendation.status == Decision.PENDING
    )
    questions = counts(ResearchQuestion.report_id)
    return [
        ReportSummary(
            id=r.id,
            job_id=r.job_id,
            title=r.title,
            scope=r.scope,
            model=r.model,
            created_at=r.created_at,
            triggered_by=r.triggered_by.full_name if r.triggered_by else None,
            sources=sources.get(r.id, 0),
            findings=findings.get(r.id, 0),
            pending_recommendations=pending.get(r.id, 0),
            questions=questions.get(r.id, 0),
        )
        for r in reports
    ]


def _recommendation(rec: CurriculumRecommendation, report_title: str) -> RecommendationOut:
    return RecommendationOut(
        id=rec.id,
        report_id=rec.report_id,
        report_title=report_title,
        kind=rec.kind,
        topic=topic_ref(rec.topic),
        domain=NamedRef(id=rec.domain.id, name=rec.domain.name) if rec.domain else None,
        proposed_name=rec.proposed_name,
        rationale=rec.rationale,
        finding_ids=rec.finding_ids,
        status=rec.status,
        decided_by=rec.decided_by.full_name if rec.decided_by else None,
        decided_at=rec.decided_at,
        decision_note=rec.decision_note,
        created_topic_id=rec.created_topic_id,
        created_at=rec.created_at,
    )


def _research_question(q: ResearchQuestion) -> ResearchQuestionOut:
    return ResearchQuestionOut(
        id=q.id,
        text=q.text,
        topic=topic_ref(q.topic),
        topic_label=q.topic_label,
        role=q.role,
        rationale=q.rationale,
        finding_ids=q.finding_ids,
        status=q.status,
    )


@router.get("/reports", response_model=Page[ReportSummary], dependencies=[Depends(can_read)])
def list_reports(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=50),
    db: Session = Depends(get_db),
) -> Page[ReportSummary]:
    total = db.scalar(select(func.count()).select_from(ResearchReport)) or 0
    reports = db.scalars(
        select(ResearchReport)
        .order_by(ResearchReport.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).unique()
    return Page(items=_summaries(db, list(reports)), total=total, page=page, page_size=page_size)


@router.get("/reports/{report_id}", response_model=ReportDetail, dependencies=[Depends(can_read)])
def get_report(report_id: uuid.UUID, db: Session = Depends(get_db)) -> ReportDetail:
    report = db.get(ResearchReport, report_id)
    if report is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Report not found.")
    sources = db.scalars(
        select(ResearchSource)
        .where(ResearchSource.report_id == report.id)
        .order_by(ResearchSource.id)
    ).all()
    findings = db.scalars(
        select(ResearchFinding)
        .where(ResearchFinding.report_id == report.id)
        .order_by(ResearchFinding.id)
    ).unique()
    findings = list(findings)
    evidence: dict[int, list[EvidenceOut]] = {}
    for item in db.scalars(
        select(FindingEvidence)
        .where(FindingEvidence.finding_id.in_([f.id for f in findings]))
        .order_by(FindingEvidence.id)
    ):
        evidence.setdefault(item.finding_id, []).append(
            EvidenceOut(
                source_id=item.source_id, quote=item.quote, quote_verified=item.quote_verified
            )
        )
    recommendations = db.scalars(
        select(CurriculumRecommendation)
        .where(CurriculumRecommendation.report_id == report.id)
        .order_by(CurriculumRecommendation.created_at)
    ).unique()
    questions = db.scalars(
        select(ResearchQuestion)
        .where(ResearchQuestion.report_id == report.id)
        .order_by(ResearchQuestion.created_at)
    ).unique()
    return ReportDetail(
        **_summaries(db, [report])[0].model_dump(),
        summary=report.summary,
        source_list=[ResearchSourceOut.model_validate(s) for s in sources],
        finding_list=[
            FindingOut(
                id=f.id,
                topic=topic_ref(f.topic),
                topic_label=f.topic_label,
                roles=f.roles,
                skills=f.skills,
                observation=f.observation,
                trend=f.trend,
                evidence=evidence.get(f.id, []),
            )
            for f in findings
        ],
        recommendations=[_recommendation(r, report.title) for r in recommendations],
        question_list=[_research_question(q) for q in questions],
    )


@router.get(
    "/recommendations", response_model=list[RecommendationOut], dependencies=[Depends(can_read)]
)
def list_recommendations(
    status_filter: Decision | None = Query(default=Decision.PENDING, alias="status"),
    db: Session = Depends(get_db),
) -> list[RecommendationOut]:
    query = (
        select(CurriculumRecommendation, ResearchReport.title)
        .join(ResearchReport, CurriculumRecommendation.report_id == ResearchReport.id)
        .order_by(CurriculumRecommendation.created_at.desc())
        .limit(200)
    )
    if status_filter is not None:
        query = query.where(CurriculumRecommendation.status == status_filter)
    return [_recommendation(rec, title) for rec, title in db.execute(query).unique()]


@router.post("/recommendations/{recommendation_id}/decision", response_model=RecommendationOut)
def decide(
    recommendation_id: uuid.UUID,
    body: RecommendationDecision,
    request: Request,
    ctx: AdminContext = Depends(require_permission(Perm.TAXONOMY_MANAGE)),
    db: Session = Depends(get_db),
) -> RecommendationOut:
    rec = db.get(CurriculumRecommendation, recommendation_id)
    if rec is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Recommendation not found.")
    if rec.status in (Decision.APPROVED, Decision.REJECTED):
        raise HTTPException(status.HTTP_409_CONFLICT, "This recommendation was already decided.")
    decision = Decision(body.decision)
    details: dict[str, str | None] = {"decision": decision.value, "kind": rec.kind.value}

    if decision is Decision.APPROVED and rec.kind is RecommendationKind.ADD_TOPIC:
        domain = db.get(Domain, rec.domain_id) if rec.domain_id else None
        if domain is None or domain.archived_at is not None or not rec.proposed_name:
            raise HTTPException(
                status.HTTP_409_CONFLICT, "The recommended domain no longer exists."
            )
        slug = topic_slug(domain.slug, rec.proposed_name)
        if db.scalar(select(Topic.id).where(Topic.slug == slug)):
            raise HTTPException(
                status.HTTP_409_CONFLICT, f'A topic called "{rec.proposed_name}" already exists.'
            )
        position = db.scalar(
            select(func.coalesce(func.max(Topic.position), -1)).where(Topic.domain_id == domain.id)
        )
        topic = Topic(
            domain_id=domain.id,
            slug=slug,
            name=rec.proposed_name,
            position=(position or 0) + 1,
            created_by_admin_id=ctx.admin.id,
        )
        db.add(topic)
        db.flush()
        rec.created_topic_id = topic.id
        details["created_topic"] = topic.slug

    rec.status = decision
    rec.decided_by_admin_id = ctx.admin.id
    rec.decided_at = utcnow()
    rec.decision_note = body.note or None
    record_audit(
        db,
        request,
        ctx,
        "research.recommendation_decided",
        "curriculum_recommendation",
        rec.id,
        details,
    )
    db.commit()
    db.refresh(rec)  # load the decider just set
    report = db.get(ResearchReport, rec.report_id)
    return _recommendation(rec, report.title if report else "")


@router.patch("/questions/{question_id}", response_model=ResearchQuestionOut)
def review_research_question(
    question_id: uuid.UUID,
    body: ResearchQuestionReview,
    request: Request,
    ctx: AdminContext = Depends(require_permission(Perm.INTELLIGENCE_REVIEW)),
    db: Session = Depends(get_db),
) -> ResearchQuestionOut:
    question = db.get(ResearchQuestion, question_id)
    if question is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Question not found.")
    target = ReviewStatus(body.status)
    if question.status is not target:
        record_audit(
            db,
            request,
            ctx,
            "research.question_reviewed",
            "research_question",
            question.id,
            {"status": {"from": question.status.value, "to": target.value}},
        )
        question.status = target
        question.reviewed_by_admin_id = ctx.admin.id
        question.reviewed_at = utcnow()
        db.commit()
    return _research_question(question)
