"""Credential verification shared by the admin and student login flows."""

from datetime import timedelta

from fastapi import HTTPException, Request, status
from sqlalchemy.orm import Session

from app.auth.sessions import client_ip, user_agent
from app.core.config import get_settings
from app.core.security import hash_password, password_needs_rehash, utcnow, verify_password
from app.models import AdminStatus, AdminUser, Audience, LoginEvent, Student, StudentStatus

INVALID_CREDENTIALS = "Invalid email or password."

_INACTIVE_MESSAGES = {
    Audience.ADMIN: "This admin account is disabled. Contact a super admin.",
    Audience.STUDENT: "This account is not active. Please contact support.",
}


def _record(
    db: Session,
    request: Request,
    audience: Audience,
    account: AdminUser | Student | None,
    email: str,
    reason: str | None,
) -> None:
    db.add(
        LoginEvent(
            audience=audience,
            admin_user_id=account.id if isinstance(account, AdminUser) else None,
            student_id=account.id if isinstance(account, Student) else None,
            email=email,
            success=reason is None,
            failure_reason=reason,
            ip_address=client_ip(request),
            user_agent=user_agent(request),
        )
    )


def authenticate[A: (AdminUser, Student)](
    db: Session,
    request: Request,
    *,
    audience: Audience,
    account: A | None,
    email: str,
    password: str,
) -> A:
    """Verify a login attempt or raise. On success, updates login bookkeeping (caller commits)
    and returns the verified account.

    The same generic error is returned for unknown emails and wrong passwords. Lockout and
    inactive-account messages are only revealed to someone who supplied the correct password.
    """
    settings = get_settings()
    now = utcnow()

    password_ok = verify_password(account.password_hash if account else None, password)

    if account is None:
        _record(db, request, audience, None, email, "unknown_email")
        db.commit()
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, INVALID_CREDENTIALS)

    if account.locked_until is not None and account.locked_until > now:
        _record(db, request, audience, account, email, "locked")
        db.commit()
        if password_ok:
            minutes = max(1, int((account.locked_until - now).total_seconds() // 60) + 1)
            raise HTTPException(
                status.HTTP_429_TOO_MANY_REQUESTS,
                f"Too many failed attempts. Try again in {minutes} minute(s)"
                + (" or reset your password." if audience is Audience.STUDENT else "."),
            )
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, INVALID_CREDENTIALS)

    if not password_ok:
        account.failed_login_count += 1
        if account.failed_login_count >= settings.max_failed_logins:
            account.locked_until = now + timedelta(minutes=settings.lockout_minutes)
            account.failed_login_count = 0
        _record(db, request, audience, account, email, "bad_password")
        db.commit()
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, INVALID_CREDENTIALS)

    active = AdminStatus.ACTIVE if isinstance(account, AdminUser) else StudentStatus.ACTIVE
    if account.status != active:
        _record(db, request, audience, account, email, f"status_{account.status.value}")
        db.commit()
        raise HTTPException(status.HTTP_403_FORBIDDEN, _INACTIVE_MESSAGES[audience])

    account.failed_login_count = 0
    account.locked_until = None
    account.last_login_at = now
    if password_needs_rehash(account.password_hash):
        account.password_hash = hash_password(password)
    _record(db, request, audience, account, email, None)
    return account
