"""Interview Data Sources: configuration, credentials, connection tests, fetches and imports.

Secrets are write-only: no endpoint returns them, and responses only say which fields are set.
"""

import uuid
from typing import Any

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Request,
    Response,
    UploadFile,
    status,
)
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth.deps import AdminContext, require_permission
from app.auth.permissions import Perm
from app.core.audit import record_audit
from app.core.db import get_db
from app.core.errors import UserFacingError
from app.core.security import utcnow
from app.core.vault import get_vault
from app.jobs.runner import notify_worker
from app.models import (
    ACTIVE_JOB_STATUSES,
    ConnectionStatus,
    InterviewSource,
    Job,
    JobEvent,
    JobEventLevel,
    JobKind,
    JobStatus,
    RawSourceRecord,
)
from app.schemas.common import Page
from app.schemas.sources import (
    AuthMethodInfo,
    ConnectorInfo,
    CredentialStatus,
    CredentialsUpdate,
    FetchRequest,
    FetchResult,
    FetchSkipped,
    JobDetail,
    JobEventOut,
    JobSummary,
    RecordDetail,
    RecordListItem,
    SourceCatalog,
    SourceCreate,
    SourceDetail,
    SourceListItem,
    SourceUpdate,
    source_fields,
)
from app.sources import service
from app.sources.auth import AUTH_SPECS
from app.sources.connectors import CONNECTORS
from app.sources.files import MAX_UPLOAD_BYTES, SUPPORTED_EXTENSIONS, safe_filename
from app.sources.http import SourceError, origin_of

router = APIRouter(prefix="/sources", tags=["admin-sources"])

can_view = require_permission(Perm.SOURCES_VIEW)
can_manage = require_permission(Perm.SOURCES_MANAGE)
can_set_credentials = require_permission(Perm.SOURCE_CREDENTIALS_MANAGE)
can_read_records = require_permission(Perm.INTELLIGENCE_VIEW)

MAX_SECRET_LENGTH = 4096


# --- Helpers ------------------------------------------------------------------------------------


def _get_source(db: Session, source_id: uuid.UUID, *, active: bool = False) -> InterviewSource:
    source = db.get(InterviewSource, source_id)
    if source is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Source not found.")
    if active and source.archived_at is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "This source was removed.")
    return source


def _settings_error(exc: UserFacingError) -> HTTPException:
    if isinstance(exc, service.SettingsInvalid):
        return HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            [
                {"loc": ["body", section, field], "msg": message, "type": "value_error"}
                for section, field, message in exc.problems
            ],
        )
    return HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc))


def _credential_status(source: InterviewSource) -> CredentialStatus:
    credential = source.credential
    return CredentialStatus(
        required=service.required_fields(source),
        stored=list(credential.fields) if credential else [],
        complete=service.credentials_complete(source),
        updated_at=credential.updated_at if credential else None,
        updated_by=credential.updated_by.full_name
        if credential and credential.updated_by
        else None,
    )


def _active_jobs(db: Session, source_ids: list[uuid.UUID]) -> dict[uuid.UUID, Job]:
    jobs = db.scalars(
        select(Job).where(
            Job.source_id.in_(source_ids),
            Job.kind == JobKind.SOURCE_FETCH,
            Job.status.in_(ACTIVE_JOB_STATUSES),
        )
    ).all()
    return {job.source_id: job for job in jobs if job.source_id}


def _record_counts(db: Session, source_ids: list[uuid.UUID]) -> dict[uuid.UUID, int]:
    rows = db.execute(
        select(RawSourceRecord.source_id, func.count(func.distinct(RawSourceRecord.external_id)))
        .where(RawSourceRecord.source_id.in_(source_ids))
        .group_by(RawSourceRecord.source_id)
    ).all()
    return {source_id: count for source_id, count in rows}


def _list_items(db: Session, sources: list[InterviewSource]) -> list[SourceListItem]:
    ids = [s.id for s in sources]
    active, counts = _active_jobs(db, ids), _record_counts(db, ids)
    return [
        SourceListItem(
            **source_fields(s),
            record_count=counts.get(s.id, 0),
            credentials=_credential_status(s),
            active_job=JobSummary.of(active[s.id]) if s.id in active else None,
        )
        for s in sources
    ]


def _detail(db: Session, source: InterviewSource) -> SourceDetail:
    item = _list_items(db, [source])[0]
    return SourceDetail(**item.model_dump(), config=source.config, auth_config=source.auth_config)


def _start_fetch(
    db: Session, source: InterviewSource, ctx: AdminContext
) -> tuple[Job | None, str | None]:
    """Queue a fetch, or say why it can't start."""
    if source.archived_at is not None:
        return None, "The source was removed."
    if not source.enabled:
        return None, "The source is turned off."
    if not CONNECTORS[source.connector_type].uses_url:
        return None, "File-import sources aren't fetched; upload files instead."
    if not service.credentials_complete(source):
        return None, "The source needs credentials first."
    if source.id in _active_jobs(db, [source.id]):
        return None, "A fetch is already running for this source."
    job = Job(kind=JobKind.SOURCE_FETCH, source_id=source.id, triggered_by_admin_id=ctx.admin.id)
    try:
        with db.begin_nested():
            db.add(job)
            db.flush()
    except IntegrityError:  # another admin started one at the same moment
        return None, "A fetch is already running for this source."
    db.add(JobEvent(job_id=job.id, level=JobEventLevel.INFO, message="Queued."))
    return job, None


# --- Catalog & sources --------------------------------------------------------------------------


@router.get("/catalog", response_model=SourceCatalog, dependencies=[Depends(can_view)])
def catalog() -> SourceCatalog:
    return SourceCatalog(
        connectors=[
            ConnectorInfo(
                key=c.type,
                label=c.label,
                description=c.description,
                uses_url=c.uses_url,
                auth_methods=list(c.auth_methods),
                settings_fields=c.settings_fields,
            )
            for c in CONNECTORS.values()
        ],
        auth_methods=[
            AuthMethodInfo(
                key=spec.method,
                label=spec.label,
                description=spec.description,
                settings_fields=spec.settings_fields,
                secret_fields=spec.secret_fields,
            )
            for spec in AUTH_SPECS.values()
        ],
        credential_storage_ready=get_vault() is not None,
        upload_extensions=sorted(SUPPORTED_EXTENSIONS),
        max_upload_mb=MAX_UPLOAD_BYTES // (1024 * 1024),
    )


@router.get("", response_model=list[SourceListItem], dependencies=[Depends(can_view)])
def list_sources(
    include_removed: bool = False, db: Session = Depends(get_db)
) -> list[SourceListItem]:
    query = select(InterviewSource).order_by(func.lower(InterviewSource.name))
    if not include_removed:
        query = query.where(InterviewSource.archived_at.is_(None))
    return _list_items(db, list(db.scalars(query).unique()))


@router.post("", response_model=SourceDetail, status_code=status.HTTP_201_CREATED)
def create_source(
    body: SourceCreate,
    request: Request,
    ctx: AdminContext = Depends(can_manage),
    db: Session = Depends(get_db),
) -> SourceDetail:
    try:
        base_url, config, auth_config = service.validate_settings(
            body.connector_type, body.base_url, body.auth_method, body.config, body.auth_config
        )
    except UserFacingError as exc:
        raise _settings_error(exc) from None
    source = InterviewSource(
        name=body.name,
        description=body.description,
        connector_type=body.connector_type,
        base_url=base_url,
        auth_method=body.auth_method,
        config=config,
        auth_config=auth_config,
        enabled=body.enabled,
        created_by_admin_id=ctx.admin.id,
    )
    if not CONNECTORS[body.connector_type].uses_url:
        source.connection_status = ConnectionStatus.MANUAL_IMPORT_REQUIRED
        source.connection_message = "Upload files to add records."
    db.add(source)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT, "A source with this name already exists."
        ) from None
    record_audit(
        db,
        request,
        ctx,
        "source.created",
        "interview_source",
        source.id,
        {"name": source.name, "type": source.connector_type.value, "site": _site(source)},
    )
    db.commit()
    return _detail(db, source)


def _site(source: InterviewSource) -> str | None:
    return origin_of(source.base_url) if source.base_url else None


@router.get("/{source_id}", response_model=SourceDetail, dependencies=[Depends(can_view)])
def get_source(source_id: uuid.UUID, db: Session = Depends(get_db)) -> SourceDetail:
    return _detail(db, _get_source(db, source_id))


@router.patch("/{source_id}", response_model=SourceDetail)
def update_source(
    source_id: uuid.UUID,
    body: SourceUpdate,
    request: Request,
    ctx: AdminContext = Depends(can_manage),
    db: Session = Depends(get_db),
) -> SourceDetail:
    source = _get_source(db, source_id, active=True)
    sent = body.model_fields_set
    changed: list[str] = []
    destinations_before = service.credential_destinations(source)

    for field in ("name", "description", "enabled"):
        value = getattr(body, field)
        if field in sent and value is not None and value != getattr(source, field):
            setattr(source, field, value)
            changed.append(field)

    connection_fields = {"base_url", "auth_method", "config", "auth_config"} & sent
    if connection_fields:
        method_before = source.auth_method
        try:
            base_url, config, auth_config = service.validate_settings(
                source.connector_type,
                body.base_url if "base_url" in sent else source.base_url,
                body.auth_method or source.auth_method,
                body.config if body.config is not None else source.config,
                body.auth_config if body.auth_config is not None else source.auth_config,
            )
        except UserFacingError as exc:
            raise _settings_error(exc) from None
        new_values = {
            "base_url": base_url,
            "auth_method": body.auth_method or source.auth_method,
            "config": config,
            "auth_config": auth_config,
        }
        for field, value in new_values.items():
            if value != getattr(source, field):
                setattr(source, field, value)
                changed.append(field)
        if {"base_url", "auth_method", "config", "auth_config"} & set(changed):
            source.connection_status = ConnectionStatus.UNTESTED
            source.connection_message = None

        details: dict[str, Any] = {}
        if source.credential is not None:
            if service.credential_destinations(source) != destinations_before:
                source.credential = None
                details["credentials_cleared"] = "the site they are sent to changed"
            elif source.auth_method != method_before and (
                dropped := service.prune_credentials(source)
            ):
                details["credential_fields_dropped"] = dropped
        if details:
            changed.append("credentials")
    else:
        details = {}

    if changed:
        record_audit(
            db,
            request,
            ctx,
            "source.updated",
            "interview_source",
            source.id,
            {"fields": sorted(set(changed)), **details},
        )
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            raise HTTPException(
                status.HTTP_409_CONFLICT, "A source with this name already exists."
            ) from None
    return _detail(db, source)


@router.delete("/{source_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_source(
    source_id: uuid.UUID,
    request: Request,
    ctx: AdminContext = Depends(can_manage),
    db: Session = Depends(get_db),
) -> Response:
    """Removes a source from use. Its records and history are kept permanently; its stored
    credentials are deleted."""
    source = _get_source(db, source_id, active=True)
    source.archived_at = utcnow()
    source.enabled = False
    had_credentials = source.credential is not None
    source.credential = None
    for job in _active_jobs(db, [source.id]).values():
        job.cancel_requested = True
    record_audit(
        db,
        request,
        ctx,
        "source.removed",
        "interview_source",
        source.id,
        {"name": source.name, "credentials_deleted": had_credentials},
    )
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# --- Credentials ----------------------------------------------------------------------------------


@router.put("/{source_id}/credentials", response_model=SourceDetail)
def set_credentials(
    source_id: uuid.UUID,
    body: CredentialsUpdate,
    request: Request,
    ctx: AdminContext = Depends(can_set_credentials),
    db: Session = Depends(get_db),
) -> SourceDetail:
    source = _get_source(db, source_id, active=True)
    if not service.required_fields(source):
        raise HTTPException(
            status.HTTP_409_CONFLICT, "This source's sign-in method doesn't use credentials."
        )
    values = {key: secret.get_secret_value() for key, secret in body.values.items()}
    if any(len(value) > MAX_SECRET_LENGTH for value in values.values()):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            f"Credential values can be at most {MAX_SECRET_LENGTH} characters.",
        )
    try:
        changed = service.store_credentials(source, values, ctx.admin)
    except UserFacingError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from None
    if changed:
        source.connection_status = ConnectionStatus.UNTESTED
        source.connection_message = None
        # Field names only: the values never reach the audit log.
        record_audit(
            db,
            request,
            ctx,
            "source.credentials_set",
            "interview_source",
            source.id,
            {"fields": changed},
        )
    db.commit()
    return _detail(db, source)


@router.delete("/{source_id}/credentials", response_model=SourceDetail)
def clear_credentials(
    source_id: uuid.UUID,
    request: Request,
    ctx: AdminContext = Depends(can_set_credentials),
    db: Session = Depends(get_db),
) -> SourceDetail:
    source = _get_source(db, source_id, active=True)
    if source.credential is not None:
        source.credential = None
        source.connection_status = ConnectionStatus.UNTESTED
        source.connection_message = None
        record_audit(db, request, ctx, "source.credentials_cleared", "interview_source", source.id)
        db.commit()
    return _detail(db, source)


# --- Testing, fetching and importing -------------------------------------------------------------


@router.post("/{source_id}/test", response_model=SourceDetail)
def test_source(
    source_id: uuid.UUID,
    request: Request,
    ctx: AdminContext = Depends(can_manage),
    db: Session = Depends(get_db),
) -> SourceDetail:
    source = _get_source(db, source_id, active=True)
    if not CONNECTORS[source.connector_type].uses_url:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "File-import sources don't connect anywhere to test."
        )
    result, message = service.check_connection(source)
    service.set_connection_status(source, result, message)
    source.last_tested_at = utcnow()
    record_audit(
        db,
        request,
        ctx,
        "source.connection_tested",
        "interview_source",
        source.id,
        {"result": result.value},
    )
    db.commit()
    return _detail(db, source)


@router.post("/fetch", response_model=FetchResult, status_code=status.HTTP_202_ACCEPTED)
def fetch_sources(
    body: FetchRequest,
    request: Request,
    ctx: AdminContext = Depends(can_manage),
    db: Session = Depends(get_db),
) -> FetchResult:
    """Start fetches for several sources; each runs as its own background job."""
    started: list[Job] = []
    skipped: list[FetchSkipped] = []
    for source_id in dict.fromkeys(body.source_ids):
        source = db.get(InterviewSource, source_id)
        if source is None:
            skipped.append(FetchSkipped(source_id=source_id, name=None, reason="Not found."))
            continue
        job, reason = _start_fetch(db, source, ctx)
        if job is None:
            skipped.append(FetchSkipped(source_id=source_id, name=source.name, reason=reason or ""))
            continue
        started.append(job)
        record_audit(
            db,
            request,
            ctx,
            "source.fetch_started",
            "interview_source",
            source.id,
            {"job_id": str(job.id)},
        )
    db.commit()
    if started:
        notify_worker()
    return FetchResult(started=[JobSummary.of(j) for j in started], skipped=skipped)


@router.post("/{source_id}/fetch", response_model=JobSummary, status_code=status.HTTP_202_ACCEPTED)
def fetch_source(
    source_id: uuid.UUID,
    request: Request,
    ctx: AdminContext = Depends(can_manage),
    db: Session = Depends(get_db),
) -> JobSummary:
    source = _get_source(db, source_id)
    job, reason = _start_fetch(db, source, ctx)
    if job is None:
        raise HTTPException(status.HTTP_409_CONFLICT, reason)
    record_audit(
        db,
        request,
        ctx,
        "source.fetch_started",
        "interview_source",
        source.id,
        {"job_id": str(job.id)},
    )
    db.commit()
    notify_worker()
    return JobSummary.of(job)


@router.post("/{source_id}/upload", response_model=JobSummary, status_code=status.HTTP_201_CREATED)
def upload_file(
    source_id: uuid.UUID,
    request: Request,
    file: UploadFile = File(...),
    id_field: str = Form(default="", max_length=200),
    title_field: str = Form(default="", max_length=200),
    ctx: AdminContext = Depends(can_manage),
    db: Session = Depends(get_db),
) -> JobSummary:
    """Import one file as records: for documents, exports, and sites that block automation."""
    source = _get_source(db, source_id, active=True)
    if not source.enabled:
        raise HTTPException(status.HTTP_409_CONFLICT, "Turn the source on before importing.")
    data = file.file.read(MAX_UPLOAD_BYTES + 1)
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status.HTTP_413_CONTENT_TOO_LARGE,
            f"Files can be at most {MAX_UPLOAD_BYTES // (1024 * 1024)} MB.",
        )
    file_name = safe_filename(file.filename)
    try:
        job = service.import_file(
            db,
            source,
            ctx.admin,
            file_name,
            data,
            id_field=id_field.strip(),
            title_field=title_field.strip(),
        )
    except SourceError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from None
    record_audit(
        db,
        request,
        ctx,
        "source.file_imported",
        "interview_source",
        source.id,
        {
            "file_name": file_name,
            "job_id": str(job.id),
            **{key: job.result[key] for key in ("new", "updated", "unchanged")},
        },
    )
    db.commit()
    return JobSummary.of(job)


# --- Run history ---------------------------------------------------------------------------------


def _get_job(db: Session, source_id: uuid.UUID, job_id: uuid.UUID) -> Job:
    job = db.get(Job, job_id)
    if job is None or job.source_id != source_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Run not found.")
    return job


@router.get("/{source_id}/jobs", response_model=Page[JobSummary], dependencies=[Depends(can_view)])
def list_jobs(
    source_id: uuid.UUID,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    db: Session = Depends(get_db),
) -> Page[JobSummary]:
    _get_source(db, source_id)
    total = db.scalar(select(func.count()).where(Job.source_id == source_id)) or 0
    jobs = db.scalars(
        select(Job)
        .where(Job.source_id == source_id)
        .order_by(Job.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return Page(items=[JobSummary.of(j) for j in jobs], total=total, page=page, page_size=page_size)


@router.get(
    "/{source_id}/jobs/{job_id}", response_model=JobDetail, dependencies=[Depends(can_view)]
)
def get_job(source_id: uuid.UUID, job_id: uuid.UUID, db: Session = Depends(get_db)) -> JobDetail:
    job = _get_job(db, source_id, job_id)
    events = db.scalars(
        select(JobEvent).where(JobEvent.job_id == job.id).order_by(JobEvent.id).limit(1000)
    ).all()
    return JobDetail(
        **JobSummary.of(job).model_dump(),
        events=[JobEventOut.model_validate(e) for e in events],
    )


@router.post("/{source_id}/jobs/{job_id}/cancel", response_model=JobSummary)
def cancel_job(
    source_id: uuid.UUID,
    job_id: uuid.UUID,
    request: Request,
    ctx: AdminContext = Depends(can_manage),
    db: Session = Depends(get_db),
) -> JobSummary:
    job = _get_job(db, source_id, job_id)
    if job.status not in ACTIVE_JOB_STATUSES:
        raise HTTPException(status.HTTP_409_CONFLICT, "This run has already finished.")
    job.cancel_requested = True
    if job.status is JobStatus.QUEUED:
        job.status = JobStatus.CANCELLED
        job.finished_at = utcnow()
        db.add(JobEvent(job_id=job.id, level=JobEventLevel.INFO, message="Stopped by an admin."))
    record_audit(
        db,
        request,
        ctx,
        "source.fetch_stopped",
        "interview_source",
        source_id,
        {"job_id": str(job.id)},
    )
    db.commit()
    return JobSummary.of(job)


# --- Raw records (intelligence.view: they can name companies and people) ------------------------


@router.get(
    "/{source_id}/records",
    response_model=Page[RecordListItem],
    dependencies=[Depends(can_read_records)],
)
def list_records(
    source_id: uuid.UUID,
    q: str | None = Query(default=None, max_length=200),
    job_id: uuid.UUID | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> Page[RecordListItem]:
    _get_source(db, source_id)
    conditions = [RawSourceRecord.source_id == source_id]
    if job_id is not None:
        conditions.append(RawSourceRecord.job_id == job_id)
    if q and q.strip():
        pattern = f"%{q.strip()}%"
        conditions.append(
            or_(
                RawSourceRecord.title.ilike(pattern),
                RawSourceRecord.url.ilike(pattern),
                RawSourceRecord.external_id.ilike(pattern),
            )
        )
    total = db.scalar(select(func.count()).select_from(RawSourceRecord).where(*conditions)) or 0
    rows = db.execute(
        select(RawSourceRecord, func.length(RawSourceRecord.content))
        .where(*conditions)
        .order_by(RawSourceRecord.fetched_at.desc(), RawSourceRecord.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return Page(
        items=[_record_item(record, length) for record, length in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


def _record_item(record: RawSourceRecord, length: int) -> RecordListItem:
    return RecordListItem(
        id=record.id,
        external_id=record.external_id,
        revision=record.revision,
        url=record.url,
        title=record.title,
        content_type=record.content_type,
        content_length=length,
        published_at=record.published_at,
        fetched_at=record.fetched_at,
        job_id=record.job_id,
    )


@router.get(
    "/{source_id}/records/{record_id}",
    response_model=RecordDetail,
    dependencies=[Depends(can_read_records)],
)
def get_record(source_id: uuid.UUID, record_id: int, db: Session = Depends(get_db)) -> RecordDetail:
    record = db.get(RawSourceRecord, record_id)
    if record is None or record.source_id != source_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Record not found.")
    return RecordDetail(
        **_record_item(record, len(record.content)).model_dump(),
        content=record.content,
        meta=record.meta,
    )
