import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Any, Literal

from pydantic import Field, StringConstraints

from app.auth.permissions import Perm
from app.models import AdminStatus, AdminUser, Role, Student, StudentStatus
from app.schemas.common import ApiModel, NewPassword, NormalizedEmail, PersonName

RoleName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=120)]
ShortText = Annotated[str, StringConstraints(strip_whitespace=True, max_length=1000)]


class RoleSummary(ApiModel):
    id: uuid.UUID
    key: str
    name: str


class AdminMe(ApiModel):
    id: uuid.UUID
    email: str
    full_name: str
    must_change_password: bool
    roles: list[RoleSummary]
    permissions: list[str]

    @classmethod
    def of(cls, admin: AdminUser) -> "AdminMe":
        return cls(
            id=admin.id,
            email=admin.email,
            full_name=admin.full_name,
            must_change_password=admin.must_change_password,
            roles=[RoleSummary.model_validate(r) for r in admin.roles],
            permissions=sorted(admin.permission_keys),
        )


# --- Admin team ---------------------------------------------------------------------------


class AdminUserOut(ApiModel):
    id: uuid.UUID
    email: str
    full_name: str
    status: AdminStatus
    must_change_password: bool
    roles: list[RoleSummary]
    last_login_at: datetime | None
    created_at: datetime


class AdminUserCreate(ApiModel):
    email: NormalizedEmail
    full_name: PersonName
    temporary_password: NewPassword
    role_ids: list[uuid.UUID] = Field(min_length=1)


class AdminUserUpdate(ApiModel):
    full_name: PersonName | None = None
    status: AdminStatus | None = None
    role_ids: list[uuid.UUID] | None = Field(default=None, min_length=1)
    temporary_password: NewPassword | None = None


class PermissionOut(ApiModel):
    key: str
    description: str


class RoleOut(ApiModel):
    id: uuid.UUID
    key: str
    name: str
    description: str
    is_system: bool
    permissions: list[str]
    admin_count: int

    @classmethod
    def of(cls, role: Role, admin_count: int) -> "RoleOut":
        return cls(
            id=role.id,
            key=role.key,
            name=role.name,
            description=role.description,
            is_system=role.is_system,
            permissions=sorted(p.key for p in role.permissions),
            admin_count=admin_count,
        )


class RoleCreate(ApiModel):
    name: RoleName
    description: ShortText = ""
    permissions: list[Perm] = Field(min_length=1)


class RoleUpdate(ApiModel):
    name: RoleName | None = None
    description: ShortText | None = None
    permissions: list[Perm] | None = Field(default=None, min_length=1)


# --- Students & cohorts -------------------------------------------------------------------


class CohortOut(ApiModel):
    id: uuid.UUID
    name: str
    description: str


class CohortWithCount(CohortOut):
    student_count: int


class CohortCreate(ApiModel):
    name: RoleName
    description: ShortText = ""


class StudentListItem(ApiModel):
    id: uuid.UUID
    student_code: str
    full_name: str
    email: str
    status: StudentStatus
    cohort: CohortOut | None
    created_at: datetime
    last_login_at: datetime | None

    @classmethod
    def of(cls, student: Student) -> "StudentListItem":
        return cls(
            id=student.id,
            student_code=student.student_code,
            full_name=student.full_name,
            email=student.email,
            status=student.status,
            cohort=CohortOut.model_validate(student.cohort) if student.cohort else None,
            created_at=student.created_at,
            last_login_at=student.last_login_at,
        )


class LoginEventOut(ApiModel):
    created_at: datetime
    success: bool
    failure_reason: str | None
    ip_address: str | None
    user_agent: str | None


class StudentDetail(StudentListItem):
    locked_until: datetime | None
    active_sessions: int
    recent_logins: list[LoginEventOut]


class StudentUpdate(ApiModel):
    status: StudentStatus | None = None
    cohort_id: uuid.UUID | None = None  # explicit null removes the cohort


# --- Overview & audit ---------------------------------------------------------------------


class DailyCount(ApiModel):
    day: date
    count: int


class StudentStats(ApiModel):
    total: int
    by_status: dict[str, int]
    active_last_7_days: int
    new_last_7_days: int
    new_last_30_days: int
    registrations_last_30_days: list[DailyCount]
    recent: list[StudentListItem]


class Overview(ApiModel):
    students: StudentStats | None
    active_admins: int | None


class AuditLogOut(ApiModel):
    id: int
    action: str
    entity_type: str
    entity_id: str | None
    details: dict[str, Any]
    actor_name: str | None
    actor_email: str | None
    ip_address: str | None
    created_at: datetime


class UsageTotals(ApiModel):
    calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: Decimal = Decimal(0)


class UsageWeek(UsageTotals):
    start: date
    end: date  # last day of the week, inclusive


class UsageSlice(ApiModel):
    key: str
    calls: int
    cost_usd: Decimal


class UsageWeekDetail(ApiModel):
    start: date
    end: date
    by_feature: list[UsageSlice]
    by_model: list[UsageSlice]


class AiUsageReport(ApiModel):
    currency: Literal["USD"] = "USD"
    tracking_start: date
    timezone: str
    weeks: list[UsageWeek]  # newest first, every week since tracking started
    selected: UsageWeekDetail | None
    all_time: UsageTotals


class SpendCap(ApiModel):
    limit_usd: Decimal
    remaining_usd: Decimal | None
    reset_interval: str | None
    resets_at: datetime | None = None


class AiProviderStatus(ApiModel):
    provider: Literal["openrouter"] = "openrouter"
    configured: bool
    ok: bool = False
    error: str | None = None
    key_usage_usd: Decimal | None = None
    cap: SpendCap | None = None
    is_free_tier: bool | None = None
