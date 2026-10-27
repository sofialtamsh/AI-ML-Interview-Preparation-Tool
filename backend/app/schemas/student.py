import uuid
from datetime import datetime

from app.models import Student, StudentStatus
from app.schemas.common import AnyPassword, ApiModel, NewPassword, NormalizedEmail, PersonName


class StudentRegister(ApiModel):
    full_name: PersonName
    email: NormalizedEmail
    password: NewPassword


class StudentMe(ApiModel):
    id: uuid.UUID
    student_code: str
    full_name: str
    email: str
    status: StudentStatus
    cohort_name: str | None
    created_at: datetime
    last_login_at: datetime | None

    @classmethod
    def of(cls, student: Student) -> "StudentMe":
        return cls(
            id=student.id,
            student_code=student.student_code,
            full_name=student.full_name,
            email=student.email,
            status=student.status,
            cohort_name=student.cohort.name if student.cohort else None,
            created_at=student.created_at,
            last_login_at=student.last_login_at,
        )


class StudentProfileUpdate(ApiModel):
    full_name: PersonName


class PasswordResetRequest(ApiModel):
    email: NormalizedEmail


class PasswordResetConfirm(ApiModel):
    token: AnyPassword
    new_password: NewPassword


class SessionOut(ApiModel):
    id: uuid.UUID
    created_at: datetime
    last_seen_at: datetime
    expires_at: datetime
    ip_address: str | None
    user_agent: str | None
    current: bool
