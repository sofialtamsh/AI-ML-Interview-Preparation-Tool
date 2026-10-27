from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.deps import AdminContext, get_admin_context
from app.auth.login import authenticate
from app.auth.sessions import (
    COOKIES,
    clear_session_cookie,
    resolve_session,
    revoke_sessions,
    set_session_cookie,
    start_session,
)
from app.core.config import get_settings
from app.core.db import get_db
from app.core.rate_limit import RateLimiter
from app.core.security import hash_password, utcnow, verify_password
from app.models import AdminUser, Audience
from app.schemas.admin import AdminMe
from app.schemas.common import ChangePasswordRequest, LoginRequest

router = APIRouter(prefix="/auth", tags=["admin-auth"])

login_limiter = RateLimiter("admin-login", get_settings().auth_rate_limit_per_minute)


@router.post("/login", response_model=AdminMe, dependencies=[Depends(login_limiter)])
def login(
    body: LoginRequest, request: Request, response: Response, db: Session = Depends(get_db)
) -> AdminMe:
    admin = authenticate(
        db,
        request,
        audience=Audience.ADMIN,
        account=db.scalar(select(AdminUser).where(AdminUser.email == body.email)),
        email=body.email,
        password=body.password,
    )
    token, expires_at = start_session(db, request, audience=Audience.ADMIN, admin_user_id=admin.id)
    db.commit()
    set_session_cookie(response, Audience.ADMIN, token, expires_at)
    return AdminMe.of(admin)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(request: Request, response: Response, db: Session = Depends(get_db)) -> None:
    token = request.cookies.get(COOKIES[Audience.ADMIN].name)
    session = resolve_session(db, token, Audience.ADMIN) if token else None
    if session is not None:
        session.revoked_at = utcnow()
        db.commit()
    clear_session_cookie(response, Audience.ADMIN)


@router.get("/me", response_model=AdminMe)
def me(ctx: AdminContext = Depends(get_admin_context)) -> AdminMe:
    return AdminMe.of(ctx.admin)


@router.post("/change-password", response_model=AdminMe)
def change_password(
    body: ChangePasswordRequest,
    ctx: AdminContext = Depends(get_admin_context),
    db: Session = Depends(get_db),
) -> AdminMe:
    admin = ctx.admin
    if not verify_password(admin.password_hash, body.current_password):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Current password is incorrect.")
    if body.new_password == body.current_password:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "Choose a password different from the current one."
        )
    admin.password_hash = hash_password(body.new_password)
    admin.password_changed_at = utcnow()
    admin.must_change_password = False
    revoke_sessions(db, admin_user_id=admin.id, except_session_id=ctx.session.id)
    db.commit()
    return AdminMe.of(admin)
