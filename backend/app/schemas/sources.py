import uuid
from datetime import datetime
from typing import Annotated, Any

from pydantic import Field, SecretStr, StringConstraints

from app.models import (
    AuthMethod,
    ConnectionStatus,
    ConnectorType,
    InterviewSource,
    Job,
    JobEventLevel,
    JobKind,
    JobStatus,
)
from app.schemas.common import ApiModel
from app.sources.fields import FieldSpec

SourceName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=120)]
Description = Annotated[str, StringConstraints(strip_whitespace=True, max_length=2000)]
BaseUrl = Annotated[str, StringConstraints(strip_whitespace=True, max_length=2048)]


class ConnectorInfo(ApiModel):
    key: ConnectorType
    label: str
    description: str
    uses_url: bool
    auth_methods: list[AuthMethod]
    settings_fields: list[FieldSpec]


class AuthMethodInfo(ApiModel):
    key: AuthMethod
    label: str
    description: str
    settings_fields: list[FieldSpec]
    secret_fields: list[FieldSpec]


class SourceCatalog(ApiModel):
    connectors: list[ConnectorInfo]
    auth_methods: list[AuthMethodInfo]
    # False when IPP_CREDENTIALS_KEYS is not configured: secrets can't be stored then.
    credential_storage_ready: bool
    upload_extensions: list[str]
    max_upload_mb: int


class CredentialStatus(ApiModel):
    """What is stored, never the values."""

    required: list[str]
    stored: list[str]
    complete: bool
    updated_at: datetime | None
    updated_by: str | None


class JobSummary(ApiModel):
    id: uuid.UUID
    kind: JobKind
    status: JobStatus
    source_id: uuid.UUID | None
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
    progress_done: int
    progress_total: int | None
    result: dict[str, Any]
    error: str | None
    cancel_requested: bool
    triggered_by: str | None
    file_name: str | None

    @classmethod
    def of(cls, job: Job) -> "JobSummary":
        return cls(
            id=job.id,
            kind=job.kind,
            status=job.status,
            source_id=job.source_id,
            created_at=job.created_at,
            started_at=job.started_at,
            finished_at=job.finished_at,
            progress_done=job.progress_done,
            progress_total=job.progress_total,
            result=job.result,
            error=job.error,
            cancel_requested=job.cancel_requested,
            triggered_by=job.triggered_by.full_name if job.triggered_by else None,
            file_name=job.payload.get("file_name"),
        )


class JobEventOut(ApiModel):
    level: JobEventLevel
    message: str
    created_at: datetime


class JobDetail(JobSummary):
    events: list[JobEventOut]


class SourceListItem(ApiModel):
    id: uuid.UUID
    name: str
    description: str
    connector_type: ConnectorType
    base_url: str | None
    auth_method: AuthMethod
    enabled: bool
    removed_at: datetime | None
    connection_status: ConnectionStatus
    connection_message: str | None
    last_tested_at: datetime | None
    last_attempted_sync_at: datetime | None
    last_successful_sync_at: datetime | None
    record_count: int
    credentials: CredentialStatus
    active_job: JobSummary | None
    created_at: datetime


class SourceDetail(SourceListItem):
    config: dict[str, Any]
    auth_config: dict[str, Any]


def source_fields(source: InterviewSource) -> dict[str, Any]:
    return {
        "id": source.id,
        "name": source.name,
        "description": source.description,
        "connector_type": source.connector_type,
        "base_url": source.base_url,
        "auth_method": source.auth_method,
        "enabled": source.enabled,
        "removed_at": source.archived_at,
        "connection_status": source.connection_status,
        "connection_message": source.connection_message,
        "last_tested_at": source.last_tested_at,
        "last_attempted_sync_at": source.last_attempted_sync_at,
        "last_successful_sync_at": source.last_successful_sync_at,
        "created_at": source.created_at,
    }


class SourceCreate(ApiModel):
    name: SourceName
    description: Description = ""
    connector_type: ConnectorType
    base_url: BaseUrl | None = None
    auth_method: AuthMethod = AuthMethod.NONE
    config: dict[str, Any] = Field(default_factory=dict)
    auth_config: dict[str, Any] = Field(default_factory=dict)
    enabled: bool = True


class SourceUpdate(ApiModel):
    name: SourceName | None = None
    description: Description | None = None
    base_url: BaseUrl | None = None
    auth_method: AuthMethod | None = None
    config: dict[str, Any] | None = None
    auth_config: dict[str, Any] | None = None
    enabled: bool | None = None


class CredentialsUpdate(ApiModel):
    # SecretStr keeps values out of error messages and reprs. A blank value keeps what's stored.
    values: dict[str, SecretStr] = Field(max_length=10)


class FetchRequest(ApiModel):
    source_ids: list[uuid.UUID] = Field(min_length=1, max_length=50)


class FetchSkipped(ApiModel):
    source_id: uuid.UUID
    name: str | None
    reason: str


class FetchResult(ApiModel):
    started: list[JobSummary]
    skipped: list[FetchSkipped]


class RecordListItem(ApiModel):
    id: int
    external_id: str
    revision: int
    url: str | None
    title: str | None
    content_type: str
    content_length: int
    published_at: datetime | None
    fetched_at: datetime
    job_id: uuid.UUID


class RecordDetail(RecordListItem):
    content: str
    meta: dict[str, Any]
