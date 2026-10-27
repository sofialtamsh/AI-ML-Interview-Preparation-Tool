"""The signed-in student's own account. Every query is scoped to the session's student, so
no endpoint here can read or change another student's data."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.deps import StudentContext, get_student_context
from app.auth.sessions import clear_session_cookie, revoke_sessions
from app.core.db import get_db
from app.core.security import hash_password, utcnow, verify_password
from app.models import Audience, AuthSession
from app.schemas.common import ChangePasswordRequest, Message
from app.schemas.student import SessionOut, StudentMe, StudentProfileUpdate

router = APIRouter(prefix="/me", tags=["student-account"])


@router.patch("", response_model=StudentMe)
def update_profile(
    body: StudentProfileUpdate,
    ctx: StudentContext = Depends(get_student_context),
    db: Session = Depends(get_db),
) -> StudentMe:
    ctx.student.full_name = body.full_name
    db.commit()
    return StudentMe.of(ctx.student)


@router.post("/password", response_model=Message)
def change_password(
    body: ChangePasswordRequest,
    ctx: StudentContext = Depends(get_student_context),
    db: Session = Depends(get_db),
) -> Message:
    student = ctx.student
    if not verify_password(student.password_hash, body.current_password):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Current password is incorrect.")
    if body.new_password == body.current_password:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "Choose a password different from the current one."
        )
    student.password_hash = hash_password(body.new_password)
    student.password_changed_at = utcnow()
    signed_out = revoke_sessions(db, student_id=student.id, except_session_id=ctx.session.id)
    db.commit()
    suffix = f" Signed out of {signed_out} other device(s)." if signed_out else ""
    return Message(message="Password updated." + suffix)


@router.get("/sessions", response_model=list[SessionOut])
def list_sessions(
    ctx: StudentContext = Depends(get_student_context), db: Session = Depends(get_db)
) -> list[SessionOut]:
    sessions = db.scalars(
        select(AuthSession)
        .where(
            AuthSession.student_id == ctx.student.id,
            AuthSession.revoked_at.is_(None),
            AuthSession.expires_at > utcnow(),
        )
        .order_by(AuthSession.last_seen_at.desc())
    ).all()
    return [
        SessionOut(
            id=s.id,
            created_at=s.created_at,
            last_seen_at=s.last_seen_at,
            expires_at=s.expires_at,
            ip_address=s.ip_address,
            user_agent=s.user_agent,
            current=s.id == ctx.session.id,
        )
        for s in sessions
    ]


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def revoke_session(
    session_id: uuid.UUID,
    response: Response,
    ctx: StudentContext = Depends(get_student_context),
    db: Session = Depends(get_db),
) -> None:
    session = db.scalar(
        select(AuthSession).where(
            AuthSession.id == session_id,
            AuthSession.student_id == ctx.student.id,
            AuthSession.revoked_at.is_(None),
        )
    )
    if session is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Session not found.")
    session.revoked_at = utcnow()
    db.commit()
    if session.id == ctx.session.id:
        clear_session_cookie(response, Audience.STUDENT)


@router.post("/sessions/revoke-others", response_model=Message)
def revoke_other_sessions(
    ctx: StudentContext = Depends(get_student_context), db: Session = Depends(get_db)
) -> Message:
    count = revoke_sessions(db, student_id=ctx.student.id, except_session_id=ctx.session.id)
    db.commit()
    return Message(message=f"Signed out of {count} other device(s).")
