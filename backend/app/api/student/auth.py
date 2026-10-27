from datetime import timedelta

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    Request,
    Response,
    status,
)
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth.deps import StudentContext, get_student_context
from app.auth.login import authenticate
from app.auth.sessions import (
    COOKIES,
    clear_session_cookie,
    client_ip,
    resolve_session,
    revoke_sessions,
    set_session_cookie,
    start_session,
    user_agent,
)
from app.core.config import get_settings
from app.core.db import get_db
from app.core.email import EmailMessage, EmailSender, get_email_sender
from app.core.rate_limit import RateLimiter
from app.core.security import hash_password, hash_token, new_token, utcnow
from app.models import Audience, LoginEvent, PasswordResetToken, Student, StudentStatus
from app.schemas.common import LoginRequest, Message
from app.schemas.student import (
    PasswordResetConfirm,
    PasswordResetRequest,
    StudentMe,
    StudentRegister,
)

router = APIRouter(prefix="/auth", tags=["student-auth"])

_per_minute = get_settings().auth_rate_limit_per_minute
login_limiter = RateLimiter("student-login", _per_minute)
register_limiter = RateLimiter("student-register", _per_minute)
reset_limiter = RateLimiter("student-password-reset", max(3, _per_minute // 4))

RESET_REQUESTED = "If an account exists for that email, we've sent a password reset link."


def _sign_in(db: Session, request: Request, response: Response, student: Student) -> None:
    token, expires_at = start_session(db, request, audience=Audience.STUDENT, student_id=student.id)
    db.commit()
    set_session_cookie(response, Audience.STUDENT, token, expires_at)


@router.post(
    "/register",
    response_model=StudentMe,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(register_limiter)],
)
def register(
    body: StudentRegister, request: Request, response: Response, db: Session = Depends(get_db)
) -> StudentMe:
    student = Student(
        email=body.email,
        full_name=body.full_name,
        password_hash=hash_password(body.password),
        last_login_at=utcnow(),
    )
    db.add(student)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "An account with this email already exists. Try signing in instead.",
        ) from None
    db.add(
        LoginEvent(
            audience=Audience.STUDENT,
            student_id=student.id,
            email=student.email,
            success=True,
            failure_reason=None,
            ip_address=client_ip(request),
            user_agent=user_agent(request),
        )
    )
    _sign_in(db, request, response, student)
    db.refresh(student)
    return StudentMe.of(student)


@router.post("/login", response_model=StudentMe, dependencies=[Depends(login_limiter)])
def login(
    body: LoginRequest, request: Request, response: Response, db: Session = Depends(get_db)
) -> StudentMe:
    student = authenticate(
        db,
        request,
        audience=Audience.STUDENT,
        account=db.scalar(select(Student).where(Student.email == body.email)),
        email=body.email,
        password=body.password,
    )
    _sign_in(db, request, response, student)
    return StudentMe.of(student)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(request: Request, response: Response, db: Session = Depends(get_db)) -> None:
    token = request.cookies.get(COOKIES[Audience.STUDENT].name)
    session = resolve_session(db, token, Audience.STUDENT) if token else None
    if session is not None:
        session.revoked_at = utcnow()
        db.commit()
    clear_session_cookie(response, Audience.STUDENT)


@router.get("/me", response_model=StudentMe)
def me(ctx: StudentContext = Depends(get_student_context)) -> StudentMe:
    return StudentMe.of(ctx.student)


@router.post(
    "/password-reset/request",
    response_model=Message,
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(reset_limiter)],
)
def request_password_reset(
    body: PasswordResetRequest,
    request: Request,
    background: BackgroundTasks,
    db: Session = Depends(get_db),
    sender: EmailSender = Depends(get_email_sender),
) -> Message:
    """Always answers the same way so the endpoint cannot be used to discover accounts."""
    student = db.scalar(select(Student).where(Student.email == body.email))
    if student is not None and student.status is StudentStatus.ACTIVE:
        now = utcnow()
        # Only the newest link works.
        db.execute(
            update(PasswordResetToken)
            .where(
                PasswordResetToken.student_id == student.id,
                PasswordResetToken.used_at.is_(None),
            )
            .values(used_at=now)
        )
        token = new_token()
        ttl = get_settings().password_reset_ttl_minutes
        db.add(
            PasswordResetToken(
                student_id=student.id,
                token_hash=hash_token(token),
                expires_at=now + timedelta(minutes=ttl),
                requested_ip=client_ip(request),
            )
        )
        db.commit()
        link = f"{get_settings().frontend_base_url}/reset-password?token={token}"
        background.add_task(
            sender.send,
            EmailMessage(
                to=student.email,
                subject="Reset your password",
                body=(
                    f"Hi {student.full_name},\n\nUse this link to choose a new password. "
                    f"It expires in {ttl} minutes and can be used once:\n{link}\n\n"
                    "If you didn't ask for this, you can ignore this email."
                ),
            ),
        )
    return Message(message=RESET_REQUESTED)


@router.post("/password-reset/confirm", response_model=Message)
def confirm_password_reset(body: PasswordResetConfirm, db: Session = Depends(get_db)) -> Message:
    now = utcnow()
    reset = db.scalar(
        select(PasswordResetToken)
        .where(PasswordResetToken.token_hash == hash_token(body.token))
        .with_for_update()
    )
    student = db.get(Student, reset.student_id) if reset else None
    if (
        reset is None
        or student is None
        or reset.used_at is not None
        or reset.expires_at <= now
        or student.status is not StudentStatus.ACTIVE
    ):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "This reset link is invalid or has expired. Please request a new one.",
        )
    reset.used_at = now
    student.password_hash = hash_password(body.new_password)
    student.password_changed_at = now
    student.failed_login_count = 0
    student.locked_until = None
    revoke_sessions(db, student_id=student.id)
    db.commit()
    return Message(message="Your password has been reset. You can now sign in.")
