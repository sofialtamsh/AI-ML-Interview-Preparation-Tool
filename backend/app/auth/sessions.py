"""Server-side sessions carried in audience-specific, path-scoped httpOnly cookies."""

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta

from fastapi import Request, Response
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import hash_token, new_token, utcnow
from app.models import Audience, AuthSession


@dataclass(frozen=True)
class CookieSpec:
    name: str
    path: str


# Scoping each cookie to its own API prefix means the browser never even sends a student
# session to admin endpoints (or vice versa); the audience check below is the second wall.
COOKIES: dict[Audience, CookieSpec] = {
    Audience.ADMIN: CookieSpec("ipp_admin_session", "/api/admin"),
    Audience.STUDENT: CookieSpec("ipp_student_session", "/api/student"),
}

_TOUCH_INTERVAL = timedelta(minutes=1)


def client_ip(request: Request) -> str | None:
    return request.client.host if request.client else None


def user_agent(request: Request) -> str | None:
    ua = request.headers.get("user-agent")
    return ua[:512] if ua else None


def _ttl(audience: Audience) -> timedelta:
    settings = get_settings()
    if audience is Audience.ADMIN:
        return timedelta(hours=settings.admin_session_ttl_hours)
    return timedelta(days=settings.student_session_ttl_days)


def start_session(
    db: Session,
    request: Request,
    *,
    audience: Audience,
    admin_user_id: uuid.UUID | None = None,
    student_id: uuid.UUID | None = None,
) -> tuple[str, datetime]:
    """Create a session row (caller commits) and return the raw token and its expiry."""
    token = new_token()
    now = utcnow()
    expires_at = now + _ttl(audience)
    db.add(
        AuthSession(
            token_hash=hash_token(token),
            audience=audience,
            admin_user_id=admin_user_id,
            student_id=student_id,
            last_seen_at=now,
            expires_at=expires_at,
            ip_address=client_ip(request),
            user_agent=user_agent(request),
        )
    )
    return token, expires_at


def resolve_session(db: Session, token: str, audience: Audience) -> AuthSession | None:
    session = db.scalar(
        select(AuthSession).where(
            AuthSession.token_hash == hash_token(token), AuthSession.audience == audience
        )
    )
    now = utcnow()
    if session is None or session.revoked_at is not None or session.expires_at <= now:
        return None
    if audience is Audience.ADMIN:
        idle_limit = timedelta(minutes=get_settings().admin_session_idle_minutes)
        if now - session.last_seen_at > idle_limit:
            session.revoked_at = now
            db.commit()
            return None
    # Avoid a write on every request; minute-level precision is enough for idle tracking.
    if now - session.last_seen_at > _TOUCH_INTERVAL:
        session.last_seen_at = now
        db.commit()
    return session


def revoke_sessions(
    db: Session,
    *,
    admin_user_id: uuid.UUID | None = None,
    student_id: uuid.UUID | None = None,
    except_session_id: uuid.UUID | None = None,
) -> int:
    """Revoke all active sessions of one principal (caller commits). Returns the count."""
    if (admin_user_id is None) == (student_id is None):
        raise ValueError("Pass exactly one of admin_user_id or student_id.")
    stmt = update(AuthSession).where(AuthSession.revoked_at.is_(None))
    if admin_user_id is not None:
        stmt = stmt.where(AuthSession.admin_user_id == admin_user_id)
    else:
        stmt = stmt.where(AuthSession.student_id == student_id)
    if except_session_id is not None:
        stmt = stmt.where(AuthSession.id != except_session_id)
    return db.execute(stmt.values(revoked_at=utcnow())).rowcount


def set_session_cookie(
    response: Response, audience: Audience, token: str, expires_at: datetime
) -> None:
    spec = COOKIES[audience]
    response.set_cookie(
        spec.name,
        token,
        expires=expires_at,
        path=spec.path,
        httponly=True,
        secure=get_settings().cookie_secure,
        samesite="lax",
    )


def clear_session_cookie(response: Response, audience: Audience) -> None:
    spec = COOKIES[audience]
    response.delete_cookie(
        spec.name,
        path=spec.path,
        httponly=True,
        secure=get_settings().cookie_secure,
        samesite="lax",
    )
