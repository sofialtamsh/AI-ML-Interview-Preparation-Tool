"""Agent runs: start the Exploration and Market Research agents, and the execution history of
every background job. Agents only ever start from these explicit admin actions."""

import uuid
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.agents.exploration import unexplored_count
from app.agents.research import ROLE_PRESETS
from app.ai import openrouter
from app.auth.deps import AdminContext, require_any_permission, require_permission
from app.auth.permissions import Perm
from app.core.audit import record_audit
from app.core.config import get_settings
from app.core.db import get_db
from app.core.security import utcnow
from app.jobs.runner import notify_worker
from app.models import (
    ACTIVE_JOB_STATUSES,
    AiUsageEvent,
    InterviewQuestion,
    InterviewSource,
    Job,
    JobEvent,
    JobEventLevel,
    JobKind,
    JobStatus,
    RawSourceRecord,
    RecordExtraction,
    ResearchReport,
    ReviewStatus,
)
from app.schemas.common import Page
from app.schemas.intelligence import (
    AgentJob,
    AgentJobDetail,
    AgentStatus,
    ExplorationSource,
    ExplorationStart,
    ResearchStart,
    StartResult,
    StartSkipped,
)
from app.schemas.sources import JobEventOut, JobSummary
from app.sources.connectors import CONNECTORS

router = APIRouter(prefix="/agents", tags=["admin-agents"])

can_view = require_permission(Perm.AGENTS_VIEW)
can_run = require_permission(Perm.AGENTS_RUN)
AGENT_KINDS = (JobKind.EXPLORATION, JobKind.MARKET_RESEARCH)
CONTENT_KINDS = (JobKind.CONTENT_GENERATION, JobKind.CONTENT_NARRATION)


def _require_ai() -> None:
    if not openrouter.ai_configured():
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "The AI provider isn't connected. Set IPP_OPENROUTER_API_KEY on the server first.",
        )


def _costs(db: Session, job_ids: list[uuid.UUID]) -> dict[uuid.UUID, Decimal]:
    rows = db.execute(
        select(AiUsageEvent.job_id, func.sum(AiUsageEvent.cost_usd))
        .where(AiUsageEvent.job_id.in_(job_ids))
        .group_by(AiUsageEvent.job_id)
    )
    return {job_id: total for job_id, total in rows}


def agent_jobs(db: Session, jobs: list[Job]) -> list[AgentJob]:
    ids = [j.id for j in jobs]
    costs = _costs(db, ids)
    names = dict(
        db.execute(
            select(InterviewSource.id, InterviewSource.name).where(
                InterviewSource.id.in_({j.source_id for j in jobs if j.source_id})
            )
        ).all()
    )
    reports = dict(
        db.execute(
            select(ResearchReport.job_id, ResearchReport.id).where(ResearchReport.job_id.in_(ids))
        ).all()
    )
    return [
        AgentJob(
            **JobSummary.of(job).model_dump(),
            source_name=names.get(job.source_id) if job.source_id else None,
            cost_usd=costs.get(job.id, Decimal(0)),
            report_id=reports.get(job.id),
        )
        for job in jobs
    ]


@router.get(
    "/status",
    response_model=AgentStatus,
    dependencies=[
        Depends(
            require_any_permission(
                Perm.AGENTS_VIEW, Perm.AGENTS_RUN, Perm.INTELLIGENCE_VIEW, Perm.TAXONOMY_MANAGE
            )
        )
    ],
)
def agent_status() -> AgentStatus:
    settings = get_settings()
    return AgentStatus(
        ai_configured=openrouter.ai_configured(),
        extraction_model=settings.model_extraction,
        research_model=settings.model_research,
        search_engine=settings.research_search_engine,
        max_records_per_run=settings.agent_max_records_per_run,
        max_cost_per_run_usd=settings.agent_max_cost_per_run_usd,
        role_presets=ROLE_PRESETS,
    )


# --- Exploration ----------------------------------------------------------------------------------


@router.get(
    "/exploration/sources",
    response_model=list[ExplorationSource],
    dependencies=[Depends(can_view)],
)
def exploration_sources(db: Session = Depends(get_db)) -> list[ExplorationSource]:
    sources = db.scalars(
        select(InterviewSource)
        .where(InterviewSource.archived_at.is_(None))
        .order_by(func.lower(InterviewSource.name))
    ).unique()
    sources = list(sources)
    ids = [s.id for s in sources]
    records = dict(
        db.execute(
            select(
                RawSourceRecord.source_id, func.count(func.distinct(RawSourceRecord.external_id))
            )
            .where(RawSourceRecord.source_id.in_(ids))
            .group_by(RawSourceRecord.source_id)
        ).all()
    )
    question_counts = {
        (source_id, state): count
        for source_id, state, count in db.execute(
            select(InterviewQuestion.source_id, InterviewQuestion.status, func.count())
            .where(InterviewQuestion.source_id.in_(ids))
            .group_by(InterviewQuestion.source_id, InterviewQuestion.status)
        )
    }
    last_explored = dict(
        db.execute(
            select(RecordExtraction.source_id, func.max(RecordExtraction.created_at))
            .where(RecordExtraction.source_id.in_(ids))
            .group_by(RecordExtraction.source_id)
        ).all()
    )
    active = {
        job.source_id: job
        for job in db.scalars(
            select(Job).where(
                Job.source_id.in_(ids),
                Job.kind.in_([JobKind.EXPLORATION, JobKind.SOURCE_FETCH]),
                Job.status.in_(ACTIVE_JOB_STATUSES),
            )
        )
    }
    return [
        ExplorationSource(
            id=s.id,
            name=s.name,
            connector_type=s.connector_type,
            enabled=s.enabled,
            fetchable=CONNECTORS[s.connector_type].uses_url,
            record_count=records.get(s.id, 0),
            unexplored=unexplored_count(db, s.id) if records.get(s.id) else 0,
            questions=sum(question_counts.get((s.id, state), 0) for state in ReviewStatus),
            pending_review=question_counts.get((s.id, ReviewStatus.PENDING), 0),
            last_explored_at=last_explored.get(s.id),
            active_job=JobSummary.of(active[s.id]) if s.id in active else None,
        )
        for s in sources
    ]


def queue_job(db: Session, job: Job) -> bool:
    """Add a job; False if the one-active-run-per-source rule refuses it."""
    try:
        with db.begin_nested():
            db.add(job)
            db.flush()
    except IntegrityError:
        return False
    db.add(JobEvent(job_id=job.id, level=JobEventLevel.INFO, message="Queued."))
    return True


@router.post("/exploration", response_model=StartResult, status_code=status.HTTP_202_ACCEPTED)
def start_exploration(
    body: ExplorationStart,
    request: Request,
    ctx: AdminContext = Depends(can_run),
    db: Session = Depends(get_db),
) -> StartResult:
    """One exploration run per selected source, each in the background."""
    _require_ai()
    settings = get_settings()
    payload = {
        "fetch_first": body.fetch_first,
        "max_records": min(body.max_records, settings.agent_max_records_per_run),
        "max_cost_usd": str(min(body.max_cost_usd, settings.agent_max_cost_per_run_usd)),
    }
    started: list[Job] = []
    skipped: list[StartSkipped] = []
    for source_id in dict.fromkeys(body.source_ids):
        source = db.get(InterviewSource, source_id)
        reason = None
        if source is None:
            reason = "Not found."
        elif source.archived_at is not None:
            reason = "The source was removed."
        elif not source.enabled:
            reason = "The source is turned off."
        if reason:
            skipped.append(
                StartSkipped(
                    source_id=source_id, name=source.name if source else None, reason=reason
                )
            )
            continue
        job = Job(
            kind=JobKind.EXPLORATION,
            source_id=source_id,
            payload=payload,
            triggered_by_admin_id=ctx.admin.id,
        )
        if not queue_job(db, job):
            skipped.append(
                StartSkipped(
                    source_id=source_id,
                    name=source.name,
                    reason="A fetch or exploration is already running for this source.",
                )
            )
            continue
        started.append(job)
        record_audit(
            db,
            request,
            ctx,
            "agent.exploration_started",
            "interview_source",
            source_id,
            {"job_id": str(job.id), **payload},
        )
    db.commit()
    if started:
        notify_worker()
    return StartResult(started=agent_jobs(db, started), skipped=skipped)


@router.post("/research", response_model=AgentJob, status_code=status.HTTP_202_ACCEPTED)
def start_research(
    body: ResearchStart,
    request: Request,
    ctx: AdminContext = Depends(can_run),
    db: Session = Depends(get_db),
) -> AgentJob:
    _require_ai()
    settings = get_settings()
    payload = body.model_dump(mode="json")
    payload["max_cost_usd"] = str(min(body.max_cost_usd, settings.agent_max_cost_per_run_usd))
    job = Job(kind=JobKind.MARKET_RESEARCH, payload=payload, triggered_by_admin_id=ctx.admin.id)
    queue_job(db, job)
    record_audit(db, request, ctx, "agent.research_started", "job", job.id, {"roles": body.roles})
    db.commit()
    notify_worker()
    return agent_jobs(db, [job])[0]


# --- Execution history ------------------------------------------------------------------------


@router.get("/jobs", response_model=Page[AgentJob], dependencies=[Depends(can_view)])
def list_jobs(
    kind: JobKind | None = None,
    status_filter: JobStatus | None = Query(default=None, alias="status"),
    source_id: uuid.UUID | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> Page[AgentJob]:
    conditions = []
    if kind is not None:
        conditions.append(Job.kind == kind)
    if status_filter is not None:
        conditions.append(Job.status == status_filter)
    if source_id is not None:
        conditions.append(Job.source_id == source_id)
    total = db.scalar(select(func.count()).select_from(Job).where(*conditions)) or 0
    jobs = db.scalars(
        select(Job)
        .where(*conditions)
        .order_by(Job.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return Page(items=agent_jobs(db, list(jobs)), total=total, page=page, page_size=page_size)


def _get_job(db: Session, job_id: uuid.UUID) -> Job:
    job = db.get(Job, job_id)
    if job is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Run not found.")
    return job


@router.get("/jobs/{job_id}", response_model=AgentJobDetail, dependencies=[Depends(can_view)])
def get_job(job_id: uuid.UUID, db: Session = Depends(get_db)) -> AgentJobDetail:
    job = _get_job(db, job_id)
    events = db.scalars(
        select(JobEvent).where(JobEvent.job_id == job.id).order_by(JobEvent.id).limit(2000)
    ).all()
    payload = {k: v for k, v in job.payload.items() if k != "file_sha256"}
    return AgentJobDetail(
        **agent_jobs(db, [job])[0].model_dump(),
        payload=payload,
        events=[JobEventOut.model_validate(e) for e in events],
    )


def _may_control(ctx: AdminContext, job: Job) -> None:
    if job.kind in AGENT_KINDS:
        needed = Perm.AGENTS_RUN
    elif job.kind in CONTENT_KINDS:
        needed = Perm.CONTENT_GENERATE
    else:
        needed = Perm.SOURCES_MANAGE
    if needed.value not in ctx.permissions:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "You do not have permission to perform this action."
        )


def request_stop(db: Session, job: Job) -> None:
    """Ask a run to stop: a queued run is cancelled now, a running one at its next check."""
    if job.status not in ACTIVE_JOB_STATUSES:
        raise HTTPException(status.HTTP_409_CONFLICT, "This run has already finished.")
    job.cancel_requested = True
    if job.status is JobStatus.QUEUED:
        job.status = JobStatus.CANCELLED
        job.finished_at = utcnow()
        db.add(JobEvent(job_id=job.id, level=JobEventLevel.INFO, message="Stopped by an admin."))


@router.post("/jobs/{job_id}/cancel", response_model=AgentJob)
def cancel_job(
    job_id: uuid.UUID,
    request: Request,
    ctx: AdminContext = Depends(
        require_any_permission(Perm.AGENTS_RUN, Perm.SOURCES_MANAGE, Perm.CONTENT_GENERATE)
    ),
    db: Session = Depends(get_db),
) -> AgentJob:
    job = _get_job(db, job_id)
    _may_control(ctx, job)
    request_stop(db, job)
    record_audit(db, request, ctx, "agent.run_stopped", "job", job.id, {"kind": job.kind.value})
    db.commit()
    return agent_jobs(db, [job])[0]


@router.post("/jobs/{job_id}/retry", response_model=AgentJob, status_code=status.HTTP_202_ACCEPTED)
def retry_job(
    job_id: uuid.UUID,
    request: Request,
    ctx: AdminContext = Depends(require_any_permission(Perm.AGENTS_RUN, Perm.SOURCES_MANAGE)),
    db: Session = Depends(get_db),
) -> AgentJob:
    """Run a finished job again with the same settings. Exploration and fetches are incremental,
    so a retry only does the work that is still missing."""
    original = _get_job(db, job_id)
    _may_control(ctx, original)
    if original.kind in CONTENT_KINDS:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Start content generation again from the Content studio."
        )
    if original.kind is JobKind.SOURCE_IMPORT:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Imports can't be retried; upload the file again."
        )
    if original.status in ACTIVE_JOB_STATUSES:
        raise HTTPException(status.HTTP_409_CONFLICT, "This run is still in progress.")
    if original.kind in AGENT_KINDS:
        _require_ai()
    if original.source_id:
        source = db.get(InterviewSource, original.source_id)
        if source is None or source.archived_at is not None or not source.enabled:
            raise HTTPException(status.HTTP_409_CONFLICT, "The source is removed or turned off.")
    job = Job(
        kind=original.kind,
        source_id=original.source_id,
        payload=original.payload,
        triggered_by_admin_id=ctx.admin.id,
    )
    if not queue_job(db, job):
        raise HTTPException(
            status.HTTP_409_CONFLICT, "A fetch or exploration is already running for this source."
        )
    db.add(
        JobEvent(job_id=job.id, level=JobEventLevel.INFO, message=f"Retry of run {original.id}.")
    )
    record_audit(
        db, request, ctx, "agent.run_retried", "job", job.id, {"retry_of": str(original.id)}
    )
    db.commit()
    notify_worker()
    return agent_jobs(db, [job])[0]
