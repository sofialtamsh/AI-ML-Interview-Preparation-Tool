"""Source operations shared by the admin API and the job worker."""

import hashlib
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from typing import Any

from pydantic import BaseModel, TypeAdapter, ValidationError
from sqlalchemy import exists, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import UserFacingError
from app.core.security import utcnow
from app.core.vault import VaultError, get_vault
from app.jobs.runner import JobCancelled, JobContext
from app.models import (
    AdminUser,
    AuthMethod,
    ConnectionStatus,
    ConnectorType,
    InterviewSource,
    Job,
    JobEvent,
    JobEventLevel,
    JobKind,
    JobStatus,
    RawSourceRecord,
    SourceCredential,
)
from app.sources.auth import AUTH_SPECS, FormLoginSettings, form_login, request_auth
from app.sources.connectors import CONNECTORS, Connector, FetchedRecord
from app.sources.fields import WebUrl
from app.sources.files import parse_upload
from app.sources.http import AccessBlocked, SafeHttp, SourceError, describe, origin_of


class ConfigError(UserFacingError):
    """Settings that don't fit the chosen connector or sign-in method."""


class SettingsInvalid(UserFacingError):
    """Field-level problems, as (section, field, message) where section is the request field
    (base_url, config or auth_config)."""

    def __init__(self, problems: list[tuple[str, str, str]]) -> None:
        super().__init__("; ".join(message for _, _, message in problems))
        self.problems = problems

    @classmethod
    def from_validation(cls, section: str, exc: ValidationError) -> "SettingsInvalid":
        problems = []
        for error in exc.errors(include_input=False, include_url=False):
            location = [part for part in error["loc"] if isinstance(part, str)]
            items = [part for part in error["loc"] if isinstance(part, int)]
            field = location[0] if location else section
            message = error["msg"].removeprefix("Value error, ")
            if items:
                message = f"Line {items[0] + 1}: {message}"
            problems.append((section, field, message))
        return cls(problems)


_BASE_URL = TypeAdapter(WebUrl)


def make_http(*, min_interval: float) -> SafeHttp:
    """The HTTP client for one test or run. Tests replace this with a mock transport."""
    return SafeHttp(
        allow_private=get_settings().sources_allow_private_networks, min_interval=min_interval
    )


# --- Settings ---------------------------------------------------------------------------------


def validate_settings(
    connector_type: ConnectorType,
    base_url: str | None,
    auth_method: AuthMethod,
    config: dict[str, Any],
    auth_config: dict[str, Any],
) -> tuple[str | None, dict[str, Any], dict[str, Any]]:
    """Normalised (base_url, config, auth_config). Raises ConfigError or SettingsInvalid."""
    connector = CONNECTORS[connector_type]
    if auth_method not in connector.auth_methods:
        raise ConfigError(
            f'"{AUTH_SPECS[auth_method].label}" can\'t be used with {connector.label} sources.'
        )
    if not connector.uses_url:
        base_url = None
    elif not base_url:
        raise SettingsInvalid([("base_url", "base_url", f"{connector.label} sources need a URL")])
    else:
        try:
            base_url = _BASE_URL.validate_python(base_url)
        except ValidationError as exc:
            raise SettingsInvalid.from_validation("base_url", exc) from None
    try:
        settings = connector.settings_model.model_validate(config, context={"base_url": base_url})
    except ValidationError as exc:
        raise SettingsInvalid.from_validation("config", exc) from None
    try:
        auth_settings = AUTH_SPECS[auth_method].settings_model.model_validate(auth_config)
    except ValidationError as exc:
        raise SettingsInvalid.from_validation("auth_config", exc) from None
    return base_url, settings.model_dump(mode="json"), auth_settings.model_dump(mode="json")


def credential_destinations(source: InterviewSource) -> set[str]:
    """The sites a source's credentials can be sent to. If this changes, stored credentials are
    cleared, so someone who may edit sources but not credentials can't redirect the secrets."""
    destinations = {origin_of(source.base_url)} if source.base_url else set()
    login_url = source.auth_config.get("login_url")
    if source.auth_method is AuthMethod.FORM_LOGIN and login_url:
        destinations.add(origin_of(login_url))
    return destinations


# --- Credentials --------------------------------------------------------------------------------


def required_fields(source: InterviewSource) -> list[str]:
    return [field.key for field in AUTH_SPECS[source.auth_method].secret_fields]


def credentials_complete(source: InterviewSource) -> bool:
    stored = set(source.credential.fields) if source.credential else set()
    return set(required_fields(source)) <= stored


def store_credentials(
    source: InterviewSource, values: dict[str, str], admin: AdminUser
) -> list[str]:
    """Encrypt and store secrets. Blank values keep what is stored. Returns the changed fields."""
    vault = get_vault()
    if vault is None:
        raise VaultError(
            "Credential storage isn't set up: IPP_CREDENTIALS_KEYS is missing on the server."
        )
    allowed = required_fields(source)
    unknown = sorted(set(values) - set(allowed))
    if unknown:
        raise ConfigError(f"Unexpected credential fields: {', '.join(unknown)}.")
    changed = {key: value for key, value in values.items() if value != ""}
    current = vault.decrypt(source.credential.ciphertext) if source.credential else {}
    merged = {key: value for key, value in {**current, **changed}.items() if key in allowed}
    missing = [key for key in allowed if not merged.get(key)]
    if missing:
        labels = {f.key: f.label for f in AUTH_SPECS[source.auth_method].secret_fields}
        raise ConfigError(f"Enter: {', '.join(labels[key] for key in missing)}.")
    ciphertext = vault.encrypt(merged)
    if source.credential is None:
        source.credential = SourceCredential(
            ciphertext=ciphertext,
            key_id=vault.current_key_id,
            fields=sorted(merged),
            updated_by_admin_id=admin.id,
        )
    else:
        source.credential.ciphertext = ciphertext
        source.credential.key_id = vault.current_key_id
        source.credential.fields = sorted(merged)
        source.credential.updated_by_admin_id = admin.id
        source.credential.updated_at = utcnow()
    return sorted(changed)


def prune_credentials(source: InterviewSource) -> list[str]:
    """After a sign-in method change, drop secrets the new method doesn't use (a username and
    password carry over between methods that both need them). Returns the dropped field names."""
    if source.credential is None:
        return []
    keep = set(required_fields(source))
    stored = set(source.credential.fields)
    dropped = sorted(stored - keep)
    if not dropped:
        return []
    vault = get_vault()
    try:
        values = vault.decrypt(source.credential.ciphertext) if vault else {}
    except VaultError:
        values = {}
    kept = {key: value for key, value in values.items() if key in keep}
    if not kept or vault is None:
        source.credential = None
        return sorted(stored)
    source.credential.ciphertext = vault.encrypt(kept)
    source.credential.key_id = vault.current_key_id
    source.credential.fields = sorted(kept)
    source.credential.updated_at = utcnow()
    return dropped


def load_secrets(source: InterviewSource) -> dict[str, str]:
    """Decrypted secrets, in memory only, for the duration of one test or run."""
    if not required_fields(source):
        return {}
    if not credentials_complete(source):
        raise SourceError("This source needs credentials. Add them on the source page first.")
    vault = get_vault()
    if vault is None:
        raise VaultError(
            "Credential storage isn't set up: IPP_CREDENTIALS_KEYS is missing on the server."
        )
    assert source.credential is not None  # noqa: S101 (checked by credentials_complete)
    return vault.decrypt(source.credential.ciphertext)


# --- Connecting ---------------------------------------------------------------------------------


@contextmanager
def connect(source: InterviewSource, secrets: dict[str, str]) -> Iterator[Connector]:
    connector_cls = CONNECTORS[source.connector_type]
    if not connector_cls.uses_url or not source.base_url:
        raise SourceError("File-import sources don't connect anywhere; upload files instead.")
    settings: BaseModel = connector_cls.settings_model.model_validate(source.config)
    auth_settings = AUTH_SPECS[source.auth_method].settings_model.model_validate(source.auth_config)
    http = make_http(min_interval=float(getattr(settings, "delay_seconds", 0.0)))
    try:
        http.set_auth(
            request_auth(source.auth_method, auth_settings, secrets, origin_of(source.base_url))
        )
        if isinstance(auth_settings, FormLoginSettings):
            form_login(http, auth_settings, secrets)
        yield connector_cls(source.base_url, settings, http)
    finally:
        http.close()


def check_connection(source: InterviewSource) -> tuple[ConnectionStatus, str]:
    try:
        with connect(source, load_secrets(source)) as connector:
            return ConnectionStatus.OK, connector.test_connection()
    except AccessBlocked as exc:
        return ConnectionStatus.MANUAL_IMPORT_REQUIRED, str(exc)
    except UserFacingError as exc:
        return ConnectionStatus.FAILED, str(exc)


def set_connection_status(source: InterviewSource, status: ConnectionStatus, message: str) -> None:
    source.connection_status = status
    source.connection_message = message[:500]


# --- Records ------------------------------------------------------------------------------------


def store_record(db: Session, source: InterviewSource, job: Job, record: FetchedRecord) -> str:
    """Append a record, or a new revision if its content changed. Returns new/updated/unchanged."""
    content_hash = hashlib.sha256(record.content.encode()).hexdigest()
    latest = db.execute(
        select(RawSourceRecord.revision, RawSourceRecord.content_hash)
        .where(
            RawSourceRecord.source_id == source.id,
            RawSourceRecord.external_id == record.external_id,
        )
        .order_by(RawSourceRecord.revision.desc())
        .limit(1)
    ).first()
    if latest is not None and latest.content_hash == content_hash:
        return "unchanged"
    db.add(
        RawSourceRecord(
            source_id=source.id,
            job_id=job.id,
            external_id=record.external_id,
            revision=latest.revision + 1 if latest else 1,
            url=record.url,
            title=record.title,
            content_type=record.content_type,
            content=record.content,
            content_hash=content_hash,
            published_at=record.published_at,
            meta=record.meta,
        )
    )
    db.flush()
    return "updated" if latest else "new"


def _counts() -> dict[str, int]:
    return {"seen": 0, "new": 0, "updated": 0, "unchanged": 0, "skipped_known": 0}


def summarise(counts: dict[str, int]) -> str:
    parts = [f"{counts.get('new', 0)} new", f"{counts.get('updated', 0)} updated"]
    if counts.get("unchanged"):
        parts.append(f"{counts['unchanged']} unchanged")
    if counts.get("skipped_known"):
        parts.append(f"{counts['skipped_known']} already fetched")
    return ", ".join(parts)


class _FetchRun:
    def __init__(self, ctx: JobContext, source: InterviewSource) -> None:
        self._ctx = ctx
        self._source = source
        self.state: dict[str, Any] = dict(source.sync_state)
        self.counts = _counts()

    def info(self, message: str) -> None:
        self._ctx.info(message)

    def warn(self, message: str) -> None:
        self._ctx.warn(message)

    def is_known(self, external_id: str) -> bool:
        return bool(
            self._ctx.db.scalar(
                select(
                    exists().where(
                        RawSourceRecord.source_id == self._source.id,
                        RawSourceRecord.external_id == external_id,
                    )
                )
            )
        )

    def skipped_known(self) -> None:
        self.counts["skipped_known"] += 1


def active_source(ctx: JobContext) -> InterviewSource:
    source = ctx.db.get(InterviewSource, ctx.job.source_id)
    if source is None or source.archived_at is not None or not source.enabled:
        raise SourceError("The source was removed or turned off before the run started.")
    return source


def fetch_records(
    ctx: JobContext, source: InterviewSource, on_record: Callable[[dict[str, int]], None]
) -> dict[str, int]:
    """Fetch new and changed records into the job, updating the source's status. Raises
    UserFacingError if the source can't be read. Shared by fetch runs and exploration runs."""
    db, job = ctx.db, ctx.job
    source.last_attempted_sync_at = utcnow()
    db.commit()
    connector_label = CONNECTORS[source.connector_type].label
    ctx.info(f"Fetching {source.name} ({connector_label}) from {describe(source.base_url or '')}.")

    run = _FetchRun(ctx, source)
    try:
        with connect(source, load_secrets(source)) as connector:
            for record in connector.fetch(run):
                ctx.check_cancelled()
                outcome = store_record(db, source, job, record)
                run.counts["seen"] += 1
                run.counts[outcome] += 1
                on_record(run.counts)
    except AccessBlocked as exc:
        set_connection_status(source, ConnectionStatus.MANUAL_IMPORT_REQUIRED, str(exc))
        db.commit()
        raise
    except JobCancelled:
        on_record(run.counts)  # the run's counts so far stay on record
        raise
    except UserFacingError as exc:
        set_connection_status(source, ConnectionStatus.FAILED, str(exc))
        db.commit()
        raise

    state = dict(run.state)
    if "run_started_at" in state:
        state["last_success_started_at"] = state.pop("run_started_at")
    source.sync_state = state
    source.last_successful_sync_at = utcnow()
    set_connection_status(source, ConnectionStatus.OK, f"Last fetch: {summarise(run.counts)}.")
    db.commit()
    return run.counts


def run_source_fetch(ctx: JobContext) -> None:
    """Job handler: fetch new and changed records from one source."""
    source = active_source(ctx)
    ctx.check_cancelled()
    counts = fetch_records(
        ctx, source, lambda counts: ctx.report(done=counts["seen"], result=counts)
    )
    ctx.report(result=counts)
    ctx.info(f"Done: {summarise(counts)}.")


def import_file(
    db: Session,
    source: InterviewSource,
    admin: AdminUser,
    file_name: str,
    data: bytes,
    *,
    id_field: str = "",
    title_field: str = "",
) -> Job:
    """Import an uploaded file as records, recorded as a finished job. Raises SourceError (after
    recording the failed job) if the file can't be read."""
    now = utcnow()
    job = Job(
        kind=JobKind.SOURCE_IMPORT,
        status=JobStatus.RUNNING,
        source_id=source.id,
        payload={
            "file_name": file_name,
            "file_size": len(data),
            "file_sha256": hashlib.sha256(data).hexdigest(),
        },
        result=_counts(),
        triggered_by_admin_id=admin.id,
        started_at=now,
        heartbeat_at=now,
        attempts=1,
    )
    db.add(job)
    db.flush()
    try:
        records = parse_upload(file_name, data, id_field=id_field, title_field=title_field)
    except SourceError as exc:
        job.status, job.error, job.finished_at = JobStatus.FAILED, str(exc), utcnow()
        db.add(JobEvent(job_id=job.id, level=JobEventLevel.ERROR, message=f"Failed: {exc}"[:1000]))
        db.commit()
        raise

    counts = _counts()
    for record in records:
        outcome = store_record(db, source, job, record)
        counts["seen"] += 1
        counts[outcome] += 1
    job.result = counts
    job.progress_done = counts["seen"]
    job.status = JobStatus.SUCCEEDED
    job.finished_at = utcnow()
    db.add(
        JobEvent(
            job_id=job.id,
            level=JobEventLevel.INFO,
            message=f"Imported {file_name}: {summarise(counts)}."[:1000],
        )
    )
    return job
