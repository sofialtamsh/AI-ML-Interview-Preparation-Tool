from datetime import datetime
from enum import StrEnum

from sqlalchemy import Column, ForeignKey, String, Table, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, Timestamps, UUIDPrimaryKey, str_enum


class AdminStatus(StrEnum):
    ACTIVE = "active"
    DISABLED = "disabled"


role_permissions = Table(
    "role_permissions",
    Base.metadata,
    Column("role_id", ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
    Column("permission_key", ForeignKey("permissions.key", ondelete="CASCADE"), primary_key=True),
)

admin_user_roles = Table(
    "admin_user_roles",
    Base.metadata,
    Column("admin_user_id", ForeignKey("admin_users.id", ondelete="CASCADE"), primary_key=True),
    Column("role_id", ForeignKey("roles.id", ondelete="RESTRICT"), primary_key=True),
)


class Permission(Base):
    """A permission key defined in code (app.auth.permissions) and mirrored here for integrity."""

    __tablename__ = "permissions"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    description: Mapped[str] = mapped_column(String(255))


class Role(UUIDPrimaryKey, Timestamps, Base):
    __tablename__ = "roles"

    key: Mapped[str] = mapped_column(String(64), unique=True)
    name: Mapped[str] = mapped_column(String(120))
    description: Mapped[str] = mapped_column(Text, default="")
    # System roles are defined in code and re-synced on deploy; they cannot be edited in the UI.
    is_system: Mapped[bool] = mapped_column(default=False)

    permissions: Mapped[list[Permission]] = relationship(
        secondary=role_permissions, lazy="selectin", order_by=Permission.key
    )


class AdminUser(UUIDPrimaryKey, Timestamps, Base):
    __tablename__ = "admin_users"

    email: Mapped[str] = mapped_column(String(320), unique=True)
    full_name: Mapped[str] = mapped_column(String(200))
    password_hash: Mapped[str] = mapped_column(String(255))
    status: Mapped[AdminStatus] = mapped_column(
        str_enum(AdminStatus, "admin_status"), default=AdminStatus.ACTIVE
    )
    must_change_password: Mapped[bool] = mapped_column(default=False)
    failed_login_count: Mapped[int] = mapped_column(default=0)
    locked_until: Mapped[datetime | None]
    last_login_at: Mapped[datetime | None]
    password_changed_at: Mapped[datetime | None]

    roles: Mapped[list[Role]] = relationship(
        secondary=admin_user_roles, lazy="selectin", order_by=Role.name
    )

    @property
    def permission_keys(self) -> set[str]:
        return {p.key for role in self.roles for p in role.permissions}
