"""Importing this package registers every model on Base.metadata (used by Alembic)."""

from app.models.admin import AdminStatus, AdminUser, Permission, Role
from app.models.ai_usage import AiUsageEvent
from app.models.audit import AuditLog
from app.models.auth import Audience, AuthSession, LoginEvent, PasswordResetToken
from app.models.base import Base
from app.models.jobs import ACTIVE_JOB_STATUSES, Job, JobEvent, JobEventLevel, JobKind, JobStatus
from app.models.sources import (
    AuthMethod,
    ConnectionStatus,
    ConnectorType,
    InterviewSource,
    RawSourceRecord,
    SourceCredential,
)
from app.models.student import Cohort, Student, StudentStatus

__all__ = [
    "ACTIVE_JOB_STATUSES",
    "AdminStatus",
    "AdminUser",
    "AiUsageEvent",
    "Audience",
    "AuditLog",
    "AuthMethod",
    "AuthSession",
    "Base",
    "Cohort",
    "ConnectionStatus",
    "ConnectorType",
    "InterviewSource",
    "Job",
    "JobEvent",
    "JobEventLevel",
    "JobKind",
    "JobStatus",
    "LoginEvent",
    "PasswordResetToken",
    "Permission",
    "RawSourceRecord",
    "Role",
    "SourceCredential",
    "Student",
    "StudentStatus",
]
