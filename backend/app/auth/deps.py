"""FastAPI dependencies that authenticate and authorise every admin and student request."""

from collections.abc import Callable
from dataclasses import dataclass

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.auth.permissions import Perm
from app.auth.sessions import COOKIES, resolve_session
from app.core.db import get_db
from app.models import AdminStatus, AdminUser, Audience, AuthSession, Student, StudentStatus

CSRF_HEADER = "x-requested-with"
CSRF_HEADER_VALUE = "ipp-web"
_SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}


def require_csrf_header(request: Request) -> None:
    """Reject state-changing requests that lack our custom header.

    Browsers only let cross-origin pages set custom headers after a CORS preflight, which this
    API does not grant, so a forged form post or cross-site fetch cannot satisfy this check.
    """
    if request.method not in _SAFE_METHODS and (
        request.headers.get(CSRF_HEADER) != CSRF_HEADER_VALUE
    ):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Missing or invalid request header.")


def _unauthenticated() -> HTTPException:
    return HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated.")


@dataclass
class AdminContext:
    admin: AdminUser
    session: AuthSession

    @property
    def permissions(self) -> set[str]:
        return self.admin.permission_keys


@dataclass
class StudentContext:
    student: Student
    session: AuthSession


def get_admin_context(request: Request, db: Session = Depends(get_db)) -> AdminContext:
    token = request.cookies.get(COOKIES[Audience.ADMIN].name)
    session = resolve_session(db, token, Audience.ADMIN) if token else None
    if session is None or session.admin_user is None:
        raise _unauthenticated()
    if session.admin_user.status is not AdminStatus.ACTIVE:
        raise _unauthenticated()
    return AdminContext(admin=session.admin_user, session=session)


def get_student_context(request: Request, db: Session = Depends(get_db)) -> StudentContext:
    token = request.cookies.get(COOKIES[Audience.STUDENT].name)
    session = resolve_session(db, token, Audience.STUDENT) if token else None
    if session is None or session.student is None:
        raise _unauthenticated()
    if session.student.status is not StudentStatus.ACTIVE:
        raise _unauthenticated()
    return StudentContext(student=session.student, session=session)


def get_ready_admin(ctx: AdminContext = Depends(get_admin_context)) -> AdminContext:
    """An authenticated admin who has replaced any temporary password they were issued."""
    if ctx.admin.must_change_password:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "Change your temporary password before continuing."
        )
    return ctx


def require_permission(*required: Perm) -> Callable[..., AdminContext]:
    """Dependency factory: the admin must hold every listed permission."""

    def checker(ctx: AdminContext = Depends(get_ready_admin)) -> AdminContext:
        if not {p.value for p in required} <= ctx.permissions:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN, "You do not have permission to perform this action."
            )
        return ctx

    return checker


def require_any_permission(*candidates: Perm) -> Callable[..., AdminContext]:
    """Dependency factory: the admin must hold at least one of the listed permissions."""

    def checker(ctx: AdminContext = Depends(get_ready_admin)) -> AdminContext:
        if not {p.value for p in candidates} & ctx.permissions:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN, "You do not have permission to perform this action."
            )
        return ctx

    return checker
