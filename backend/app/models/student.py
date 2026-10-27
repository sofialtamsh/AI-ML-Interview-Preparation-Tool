import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import ForeignKey, Identity, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, Timestamps, UUIDPrimaryKey, str_enum


class StudentStatus(StrEnum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    DEACTIVATED = "deactivated"


class Cohort(UUIDPrimaryKey, Timestamps, Base):
    __tablename__ = "cohorts"

    name: Mapped[str] = mapped_column(String(120), unique=True)
    description: Mapped[str] = mapped_column(Text, default="")


class Student(UUIDPrimaryKey, Timestamps, Base):
    __tablename__ = "students"
    __table_args__ = (Index("ix_students_created_at", "created_at"),)

    # Human-friendly identifier shown in the UI (STU-001001); `id` stays the internal key.
    student_number: Mapped[int] = mapped_column(Identity(start=1001), unique=True)
    email: Mapped[str] = mapped_column(String(320), unique=True)
    full_name: Mapped[str] = mapped_column(String(200))
    password_hash: Mapped[str] = mapped_column(String(255))
    status: Mapped[StudentStatus] = mapped_column(
        str_enum(StudentStatus, "student_status"), default=StudentStatus.ACTIVE, index=True
    )
    cohort_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("cohorts.id", ondelete="SET NULL"), index=True
    )
    email_verified_at: Mapped[datetime | None]
    failed_login_count: Mapped[int] = mapped_column(default=0)
    locked_until: Mapped[datetime | None]
    last_login_at: Mapped[datetime | None] = mapped_column(index=True)
    password_changed_at: Mapped[datetime | None]

    cohort: Mapped[Cohort | None] = relationship(lazy="joined")

    @property
    def student_code(self) -> str:
        return f"STU-{self.student_number:06d}"
