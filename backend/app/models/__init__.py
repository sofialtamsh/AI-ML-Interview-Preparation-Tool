"""Importing this package registers every model on Base.metadata (used by Alembic)."""

from app.models.admin import AdminStatus, AdminUser, Permission, Role
from app.models.ai_usage import AiUsageEvent
from app.models.audit import AuditLog
from app.models.auth import Audience, AuthSession, LoginEvent, PasswordResetToken
from app.models.base import Base
from app.models.content import (
    EXPANSION_APPROVED,
    CodeCheck,
    Component,
    ContentItem,
    ContentVersion,
    MediaAsset,
    PlatformSetting,
    VersionOrigin,
    VersionStatus,
)
from app.models.intelligence import (
    Difficulty,
    ExtractionStatus,
    InterviewExperience,
    InterviewQuestion,
    QuestionType,
    RecordExtraction,
    ReviewStatus,
)
from app.models.jobs import ACTIVE_JOB_STATUSES, Job, JobEvent, JobEventLevel, JobKind, JobStatus
from app.models.research import (
    CurriculumRecommendation,
    Decision,
    FindingEvidence,
    RecommendationKind,
    ResearchFinding,
    ResearchQuestion,
    ResearchReport,
    ResearchSource,
    Trend,
)
from app.models.sources import (
    AuthMethod,
    ConnectionStatus,
    ConnectorType,
    InterviewSource,
    RawSourceRecord,
    SourceCredential,
)
from app.models.student import Cohort, Student, StudentStatus
from app.models.taxonomy import Domain, Topic

__all__ = [
    "ACTIVE_JOB_STATUSES",
    "EXPANSION_APPROVED",
    "AdminStatus",
    "AdminUser",
    "AiUsageEvent",
    "Audience",
    "AuditLog",
    "AuthMethod",
    "AuthSession",
    "Base",
    "CodeCheck",
    "Cohort",
    "Component",
    "ConnectionStatus",
    "ConnectorType",
    "ContentItem",
    "ContentVersion",
    "CurriculumRecommendation",
    "Decision",
    "Difficulty",
    "Domain",
    "ExtractionStatus",
    "FindingEvidence",
    "InterviewExperience",
    "InterviewQuestion",
    "InterviewSource",
    "Job",
    "JobEvent",
    "JobEventLevel",
    "JobKind",
    "JobStatus",
    "LoginEvent",
    "MediaAsset",
    "PasswordResetToken",
    "Permission",
    "PlatformSetting",
    "QuestionType",
    "RawSourceRecord",
    "RecommendationKind",
    "RecordExtraction",
    "ResearchFinding",
    "ResearchQuestion",
    "ResearchReport",
    "ResearchSource",
    "ReviewStatus",
    "Role",
    "SourceCredential",
    "Student",
    "StudentStatus",
    "Topic",
    "Trend",
    "VersionOrigin",
    "VersionStatus",
]
