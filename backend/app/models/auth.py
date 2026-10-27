import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import BigInteger, CheckConstraint, ForeignKey, Identity, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.admin import AdminUser
from app.models.base import Base, UUIDPrimaryKey, str_enum
from app.models.student import Student


class Audience(StrEnum):
    ADMIN = "admin"
    STUDENT = "student"


class AuthSession(UUIDPrimaryKey, Base):
    """A server-side login session. Admin and student sessions share the mechanism but never
    the principal: the CHECK constraint ties each audience to exactly one principal column."""

    __tablename__ = "auth_sessions"
    __table_args__ = (
        CheckConstraint(
            "(audience = 'admin' AND admin_user_id IS NOT NULL AND student_id IS NULL)"
            " OR (audience = 'student' AND student_id IS NOT NULL AND admin_user_id IS NULL)",
            name="one_principal",
        ),
    )

    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    audience: Mapped[Audience] = mapped_column(str_enum(Audience, "session_audience"))
    admin_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("admin_users.id", ondelete="CASCADE"), index=True
    )
    student_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("students.id", ondelete="CASCADE"), index=True
    )
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    last_seen_at: Mapped[datetime] = mapped_column(index=True)
    expires_at: Mapped[datetime]
    revoked_at: Mapped[datetime | None]
    ip_address: Mapped[str | None] = mapped_column(String(45))
    user_agent: Mapped[str | None] = mapped_column(String(512))

    admin_user: Mapped[AdminUser | None] = relationship(lazy="joined")
    student: Mapped[Student | None] = relationship(lazy="joined")


class PasswordResetToken(UUIDPrimaryKey, Base):
    __tablename__ = "password_reset_tokens"

    student_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("students.id", ondelete="CASCADE"), index=True
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    expires_at: Mapped[datetime]
    used_at: Mapped[datetime | None]
    requested_ip: Mapped[str | None] = mapped_column(String(45))


class LoginEvent(Base):
    """Every login attempt, successful or not, for security review."""

    __tablename__ = "login_events"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    audience: Mapped[Audience] = mapped_column(str_enum(Audience, "login_event_audience"))
    admin_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("admin_users.id", ondelete="SET NULL"), index=True
    )
    student_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("students.id", ondelete="SET NULL"), index=True
    )
    email: Mapped[str] = mapped_column(String(320))
    success: Mapped[bool]
    failure_reason: Mapped[str | None] = mapped_column(String(64))
    ip_address: Mapped[str | None] = mapped_column(String(45))
    user_agent: Mapped[str | None] = mapped_column(String(512))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), index=True)
