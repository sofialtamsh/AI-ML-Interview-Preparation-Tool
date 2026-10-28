"""Content studio: review, edit, version, publish, generate and narrate learning content.

Nothing here publishes automatically: every step is an explicit admin action, recorded in the
audit log, and publishing needs `content.publish`."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.ai import openrouter
from app.api.admin.agents import CONTENT_KINDS, agent_jobs, queue_job, request_stop
from app.auth.deps import AdminContext, require_any_permission, require_permission
from app.auth.permissions import Perm
from app.content.generation import TOPIC_WIDGETS
from app.content.schemas import COMPONENT_ORDER
from app.content.service import (
    TRANSITIONS,
    ContentError,
    apply_transition,
    create_version,
    expansion_approved,
    get_item,
    may_generate,
    program_hash,
    record_code_check,
    restore,
)
from app.core.audit import record_audit
from app.core.config import get_settings
from app.core.db import get_db
from app.jobs.runner import notify_worker
from app.models import (
    EXPANSION_APPROVED,
    CodeCheck,
    Component,
    ContentItem,
    ContentVersion,
    Domain,
    Job,
    JobEvent,
    JobKind,
    MediaAsset,
    PlatformSetting,
    Topic,
    VersionOrigin,
)
from app.schemas.common import Page
from app.schemas.content import (
    BulkTransitionIn,
    BulkTransitionResult,
    CodeCheckIn,
    CodeCheckOut,
    ComponentState,
    ContentJob,
    ContentJobDetail,
    ContentOverview,
    ExpansionIn,
    GenerateIn,
    GenerateSkipped,
    MediaOut,
    NarrateIn,
    TopicContent,
    TopicContentSummary,
    TopicRefOut,
    TransitionIn,
    VersionDetail,
    VersionEdit,
    VersionSummary,
)
from app.schemas.sources import JobEventOut

router = APIRouter(prefix="/content", tags=["admin-content"])

can_read = require_any_permission(Perm.CONTENT_GENERATE, Perm.CONTENT_REVIEW, Perm.CONTENT_PUBLISH)
can_edit = require_any_permission(Perm.CONTENT_GENERATE, Perm.CONTENT_REVIEW)
can_check = require_any_permission(Perm.CONTENT_REVIEW, Perm.CONTENT_PUBLISH)
can_generate = require_permission(Perm.CONTENT_GENERATE)
can_transition = require_any_permission(
    Perm.CONTENT_GENERATE, Perm.CONTENT_REVIEW, Perm.CONTENT_PUBLISH
)


def topic_ref(topic: Topic) -> TopicRefOut:
    return TopicRefOut(
        id=topic.id,
        slug=topic.slug,
        name=topic.name,
        domain_name=topic.domain.name,
        is_pilot=topic.is_pilot,
    )


def _get_topic(db: Session, topic_id: uuid.UUID) -> Topic:
    topic = db.get(Topic, topic_id)
    if topic is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Topic not found.")
    return topic


def _get_version(db: Session, version_id: uuid.UUID) -> ContentVersion:
    version = db.get(ContentVersion, version_id)
    if version is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Version not found.")
    return version


def _topic_content(db: Session, topic: Topic) -> TopicContent:
    items = {
        item.component: item
        for item in db.scalars(select(ContentItem).where(ContentItem.topic_id == topic.id))
    }
    versions: dict[uuid.UUID, list[ContentVersion]] = {}
    if items:
        for version in db.scalars(
            select(ContentVersion)
            .where(ContentVersion.item_id.in_([i.id for i in items.values()]))
            .order_by(ContentVersion.number.desc())
        ).unique():
            versions.setdefault(version.item_id, []).append(version)
    states = []
    for component in COMPONENT_ORDER:
        item = items.get(component)
        history = versions.get(item.id, []) if item else []
        published = next((v for v in history if item and v.id == item.published_version_id), None)
        states.append(
            ComponentState(
                component=component,
                item_id=item.id if item else None,
                published_number=published.number if published else None,
                latest=VersionSummary.of(history[0]) if history else None,
                versions=[VersionSummary.of(v) for v in history],
            )
        )
    return TopicContent(
        topic=topic_ref(topic),
        may_generate=may_generate(db, topic),
        has_playground=topic.slug in TOPIC_WIDGETS,
        components=states,
    )


def _version_detail(db: Session, version: ContentVersion) -> VersionDetail:
    checks = db.scalars(
        select(CodeCheck).where(CodeCheck.version_id == version.id).order_by(CodeCheck.id.desc())
    ).all()
    current_hash = program_hash(version.body) if version.item.component is Component.PYTHON else ""
    narration = db.execute(
        select(MediaAsset.id, MediaAsset.position, MediaAsset.size, MediaAsset.voice)
        .where(MediaAsset.version_id == version.id, MediaAsset.kind == "narration")
        .order_by(MediaAsset.position)
    ).all()
    return VersionDetail(
        **VersionSummary.of(version).model_dump(),
        component=version.item.component,
        topic=topic_ref(version.item.topic),
        body=version.body,
        published=version.item.published_version_id == version.id,
        code_checks=[
            CodeCheckOut(
                id=c.id,
                passed=c.passed,
                output=c.output,
                error=c.error,
                runtime=c.runtime,
                duration_ms=c.duration_ms,
                created_at=c.created_at,
                current=c.code_hash == current_hash,
            )
            for c in checks
        ],
        narration=[MediaOut(id=i, position=p, size=s, voice=v) for i, p, s, v in narration],
    )


# --- Overview & topics ----------------------------------------------------------------------------


@router.get("", response_model=ContentOverview, dependencies=[Depends(can_read)])
def overview(db: Session = Depends(get_db)) -> ContentOverview:
    """Pilot topics, plus any other topic that already has content."""
    with_content = select(ContentItem.topic_id)
    topics = db.scalars(
        select(Topic)
        .join(Domain, Topic.domain_id == Domain.id)
        .where(Topic.archived_at.is_(None), (Topic.is_pilot) | Topic.id.in_(with_content))
        .order_by(Domain.position, Topic.position)
    ).unique()
    summaries = []
    for topic in topics:
        state = _topic_content(db, topic)
        summaries.append(
            TopicContentSummary(
                topic=state.topic,
                statuses={
                    s.component.value: s.latest.status.value if s.latest else None
                    for s in state.components
                },
                live=[s.component.value for s in state.components if s.published_number],
                published=sum(1 for s in state.components if s.published_number),
                may_generate=state.may_generate,
            )
        )
    settings = get_settings()
    return ContentOverview(
        expansion_approved=expansion_approved(db),
        ai_configured=openrouter.ai_configured(),
        content_model=settings.model_content,
        narration_model=settings.model_narration,
        narration_voices=settings.narration_voices,
        topics=summaries,
    )


@router.get("/topics/{topic_id}", response_model=TopicContent, dependencies=[Depends(can_read)])
def topic_content(topic_id: uuid.UUID, db: Session = Depends(get_db)) -> TopicContent:
    return _topic_content(db, _get_topic(db, topic_id))


@router.get(
    "/versions/{version_id}", response_model=VersionDetail, dependencies=[Depends(can_read)]
)
def get_version(version_id: uuid.UUID, db: Session = Depends(get_db)) -> VersionDetail:
    return _version_detail(db, _get_version(db, version_id))


# --- Editing and the lifecycle -----------------------------------------------------------------


@router.post(
    "/topics/{topic_id}/components/{component}/versions",
    response_model=VersionDetail,
    status_code=status.HTTP_201_CREATED,
)
def save_edit(
    topic_id: uuid.UUID,
    component: Component,
    body: VersionEdit,
    request: Request,
    ctx: AdminContext = Depends(can_edit),
    db: Session = Depends(get_db),
) -> VersionDetail:
    """An edit is a new draft version; the version it was based on stays untouched."""
    topic = _get_topic(db, topic_id)
    item = get_item(db, topic, component)
    based_on = _get_version(db, body.based_on_id) if body.based_on_id else None
    if based_on and based_on.item_id != item.id:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, "That version is another component's."
        )
    try:
        version = create_version(
            db,
            item,
            body.body,
            origin=VersionOrigin.EDITED,
            admin_id=ctx.admin.id,
            note=body.note or (f"Edited from version {based_on.number}" if based_on else "Edited"),
            based_on=based_on,
        )
    except ContentError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from None
    record_audit(
        db,
        request,
        ctx,
        "content.edited",
        "content_version",
        version.id,
        {"topic": topic.slug, "component": component.value, "number": version.number},
    )
    db.commit()
    db.refresh(version)
    return _version_detail(db, version)


@router.post("/versions/{version_id}/transition", response_model=VersionDetail)
def transition(
    version_id: uuid.UUID,
    body: TransitionIn,
    request: Request,
    ctx: AdminContext = Depends(can_transition),
    db: Session = Depends(get_db),
) -> VersionDetail:
    version = _get_version(db, version_id)
    try:
        previous = apply_transition(
            db,
            version,
            body.action,
            admin_id=ctx.admin.id,
            permissions=ctx.permissions,
            note=body.note,
        )
    except PermissionError:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "You do not have permission to perform this action."
        ) from None
    except ContentError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from None
    record_audit(
        db,
        request,
        ctx,
        f"content.{body.action}",
        "content_version",
        version.id,
        {
            "topic": version.item.topic.slug,
            "component": version.item.component.value,
            "number": version.number,
            "status": {"from": previous.value, "to": version.status.value},
        },
    )
    db.commit()
    db.refresh(version)
    return _version_detail(db, version)


@router.post("/topics/{topic_id}/bulk", response_model=BulkTransitionResult)
def bulk_transition(
    topic_id: uuid.UUID,
    body: BulkTransitionIn,
    request: Request,
    ctx: AdminContext = Depends(can_transition),
    db: Session = Depends(get_db),
) -> BulkTransitionResult:
    """Apply one step to the latest version of every component where it applies. Publishing
    still checks each Python lab's code check; nothing is skipped silently."""
    topic = _get_topic(db, topic_id)
    rule = TRANSITIONS[body.action]
    if not rule.needs & ctx.permissions:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "You do not have permission to perform this action."
        )
    changed: list[str] = []
    skipped: dict[str, str] = {}
    for item in db.scalars(select(ContentItem).where(ContentItem.topic_id == topic.id)):
        latest = db.scalar(
            select(ContentVersion)
            .where(ContentVersion.item_id == item.id)
            .order_by(ContentVersion.number.desc())
            .limit(1)
        )
        if latest is None or latest.status not in rule.sources:
            continue
        try:
            apply_transition(
                db, latest, body.action, admin_id=ctx.admin.id, permissions=ctx.permissions
            )
        except ContentError as exc:
            skipped[item.component.value] = str(exc)
            continue
        changed.append(item.component.value)
    if changed:
        record_audit(
            db,
            request,
            ctx,
            f"content.bulk_{body.action}",
            "topic",
            topic.id,
            {"topic": topic.slug, "components": changed},
        )
    db.commit()
    return BulkTransitionResult(changed=changed, skipped=skipped)


@router.post("/versions/{version_id}/restore", response_model=VersionDetail, status_code=201)
def restore_version(
    version_id: uuid.UUID,
    request: Request,
    ctx: AdminContext = Depends(can_edit),
    db: Session = Depends(get_db),
) -> VersionDetail:
    source = _get_version(db, version_id)
    version = restore(db, source, ctx.admin.id)
    record_audit(
        db,
        request,
        ctx,
        "content.restored",
        "content_version",
        version.id,
        {"from_number": source.number, "number": version.number},
    )
    db.commit()
    db.refresh(version)
    return _version_detail(db, version)


@router.post(
    "/versions/{version_id}/code-checks",
    response_model=CodeCheckOut,
    status_code=status.HTTP_201_CREATED,
)
def code_check(
    version_id: uuid.UUID,
    body: CodeCheckIn,
    request: Request,
    ctx: AdminContext = Depends(can_check),
    db: Session = Depends(get_db),
) -> CodeCheckOut:
    """Record a run of the lab made in the reviewer's browser sandbox (Pyodide). The server
    decides pass or fail by comparing the output with the expected output."""
    version = _get_version(db, version_id)
    try:
        check = record_code_check(
            db,
            version,
            output=body.output,
            error=body.error,
            duration_ms=body.duration_ms,
            runtime=body.runtime,
            admin_id=ctx.admin.id,
        )
    except ContentError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from None
    record_audit(
        db,
        request,
        ctx,
        "content.code_checked",
        "content_version",
        version.id,
        {"passed": check.passed, "runtime": check.runtime},
    )
    db.commit()
    return CodeCheckOut(
        id=check.id,
        passed=check.passed,
        output=check.output,
        error=check.error,
        runtime=check.runtime,
        duration_ms=check.duration_ms,
        created_at=check.created_at,
        current=True,
    )


# --- Generation and narration ------------------------------------------------------------------


def _require_ai() -> None:
    if not openrouter.ai_configured():
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "The AI provider isn't connected. Set IPP_OPENROUTER_API_KEY on the server first.",
        )


@router.post("/generate", response_model=dict[str, object], status_code=status.HTTP_202_ACCEPTED)
def generate(
    body: GenerateIn,
    request: Request,
    ctx: AdminContext = Depends(can_generate),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    """One generation job per topic, grouped in a batch. Results arrive as drafts."""
    _require_ai()
    batch_id = uuid.uuid4()
    started: list[Job] = []
    skipped: list[GenerateSkipped] = []
    for topic_id in dict.fromkeys(body.topic_ids):
        topic = db.get(Topic, topic_id)
        if topic is None or topic.archived_at is not None:
            skipped.append(GenerateSkipped(topic_id=topic_id, name=None, reason="Topic not found."))
            continue
        if not may_generate(db, topic):
            skipped.append(
                GenerateSkipped(
                    topic_id=topic_id,
                    name=topic.name,
                    reason="Not a pilot topic, and content expansion hasn't been approved.",
                )
            )
            continue
        job = Job(
            kind=JobKind.CONTENT_GENERATION,
            topic_id=topic.id,
            batch_id=batch_id,
            payload={
                "components": [c.value for c in body.components],
                "use_intelligence": body.use_intelligence,
                "max_cost_usd": str(body.max_cost_usd),
            },
            triggered_by_admin_id=ctx.admin.id,
        )
        queue_job(db, job)
        started.append(job)
    if started:
        record_audit(
            db,
            request,
            ctx,
            "content.generation_started",
            "batch",
            batch_id,
            {"topics": len(started), "components": [c.value for c in body.components]},
        )
    db.commit()
    if started:
        notify_worker()
    return {
        "batch_id": str(batch_id),
        "started": [j.model_dump(mode="json") for j in content_jobs(db, started)],
        "skipped": [s.model_dump(mode="json") for s in skipped],
    }


@router.post(
    "/versions/{version_id}/narration",
    response_model=ContentJob,
    status_code=status.HTTP_202_ACCEPTED,
)
def narrate(
    version_id: uuid.UUID,
    body: NarrateIn,
    request: Request,
    ctx: AdminContext = Depends(can_generate),
    db: Session = Depends(get_db),
) -> ContentJob:
    _require_ai()
    version = _get_version(db, version_id)
    if version.item.component is not Component.VIDEO:
        raise HTTPException(status.HTTP_409_CONFLICT, "Only video scripts can be narrated.")
    if body.voice not in get_settings().narration_voices:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, "Choose one of the configured voices."
        )
    job = Job(
        kind=JobKind.CONTENT_NARRATION,
        topic_id=version.item.topic_id,
        payload={"version_id": str(version.id), "voice": body.voice},
        triggered_by_admin_id=ctx.admin.id,
    )
    queue_job(db, job)
    record_audit(
        db,
        request,
        ctx,
        "content.narration_started",
        "content_version",
        version.id,
        {"voice": body.voice},
    )
    db.commit()
    notify_worker()
    return content_jobs(db, [job])[0]


# --- Generation and narration runs -----------------------------------------------------------


def content_jobs(db: Session, jobs: list[Job]) -> list[ContentJob]:
    topic_ids = {j.topic_id for j in jobs if j.topic_id}
    topics = {t.id: t for t in db.scalars(select(Topic).where(Topic.id.in_(topic_ids))).unique()}
    return [
        ContentJob(
            **summary.model_dump(),
            topic=topic_ref(topics[job.topic_id]) if job.topic_id in topics else None,
        )
        for summary, job in zip(agent_jobs(db, jobs), jobs, strict=True)
    ]


def _get_content_job(db: Session, job_id: uuid.UUID) -> Job:
    job = db.get(Job, job_id)
    if job is None or job.kind not in CONTENT_KINDS:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Run not found.")
    return job


@router.get("/jobs", response_model=Page[ContentJob], dependencies=[Depends(can_read)])
def list_content_jobs(
    topic_id: uuid.UUID | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=50),
    db: Session = Depends(get_db),
) -> Page[ContentJob]:
    """Generation and narration runs, visible to everyone who works on content."""
    conditions = [Job.kind.in_(CONTENT_KINDS)]
    if topic_id is not None:
        conditions.append(Job.topic_id == topic_id)
    total = db.scalar(select(func.count()).select_from(Job).where(*conditions)) or 0
    jobs = db.scalars(
        select(Job)
        .where(*conditions)
        .order_by(Job.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return Page(items=content_jobs(db, list(jobs)), total=total, page=page, page_size=page_size)


@router.get("/jobs/{job_id}", response_model=ContentJobDetail, dependencies=[Depends(can_read)])
def get_content_job(job_id: uuid.UUID, db: Session = Depends(get_db)) -> ContentJobDetail:
    job = _get_content_job(db, job_id)
    events = db.scalars(
        select(JobEvent).where(JobEvent.job_id == job.id).order_by(JobEvent.id).limit(2000)
    ).all()
    return ContentJobDetail(
        **content_jobs(db, [job])[0].model_dump(),
        payload=job.payload,
        events=[JobEventOut.model_validate(e) for e in events],
    )


@router.post("/jobs/{job_id}/cancel", response_model=ContentJob)
def cancel_content_job(
    job_id: uuid.UUID,
    request: Request,
    ctx: AdminContext = Depends(can_generate),
    db: Session = Depends(get_db),
) -> ContentJob:
    job = _get_content_job(db, job_id)
    request_stop(db, job)
    record_audit(db, request, ctx, "content.run_stopped", "job", job.id, {"kind": job.kind.value})
    db.commit()
    return content_jobs(db, [job])[0]


@router.get("/media/{media_id}", dependencies=[Depends(can_read)])
def media(media_id: uuid.UUID, db: Session = Depends(get_db)) -> Response:
    asset = db.get(MediaAsset, media_id)
    if asset is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Media not found.")
    return Response(asset.data, media_type=asset.content_type)


# --- The pilot gate ------------------------------------------------------------------------------


@router.put("/expansion", response_model=dict[str, bool])
def set_expansion(
    body: ExpansionIn,
    request: Request,
    ctx: AdminContext = Depends(require_permission(Perm.SETTINGS_MANAGE)),
    db: Session = Depends(get_db),
) -> dict[str, bool]:
    """The explicit green signal to generate content beyond the pilot topics."""
    setting = db.get(PlatformSetting, EXPANSION_APPROVED)
    before = bool(setting and setting.value is True)
    if setting is None:
        setting = PlatformSetting(key=EXPANSION_APPROVED, value=body.approved)
        db.add(setting)
    setting.value = body.approved
    setting.updated_by_admin_id = ctx.admin.id
    if before != body.approved:
        record_audit(
            db,
            request,
            ctx,
            "content.expansion_decided",
            "platform_setting",
            EXPANSION_APPROVED,
            {"approved": {"from": before, "to": body.approved}},
        )
    try:
        db.commit()
    except IntegrityError:  # pragma: no cover - concurrent first write
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Try again.") from None
    return {"approved": body.approved}
