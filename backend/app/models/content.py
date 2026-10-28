"""Learning content: one item per topic and component, with immutable versions moving through
draft → under review → approved → published → archived. Students only ever read the version an
item points at as published."""

import uuid
from datetime import datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import (
    BigInteger,
    ForeignKey,
    Identity,
    LargeBinary,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.admin import AdminUser
from app.models.base import Base, Timestamps, UUIDPrimaryKey, str_enum
from app.models.taxonomy import Topic


class Component(StrEnum):
    LESSON = "lesson"
    PLAYGROUND = "playground"
    PYTHON = "python"
    INTERVIEW = "interview"
    QUIZ = "quiz"
    REVISION = "revision"
    VIDEO = "video"


class VersionStatus(StrEnum):
    DRAFT = "draft"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    PUBLISHED = "published"
    ARCHIVED = "archived"
    REJECTED = "rejected"


class VersionOrigin(StrEnum):
    # Written by the AI development assistant while building the pilot; reviewed like any draft.
    STARTER = "starter"
    AI_GENERATED = "ai_generated"
    # A person's edit of an earlier version (or a restored earlier version).
    EDITED = "edited"


class ContentItem(UUIDPrimaryKey, Timestamps, Base):
    __tablename__ = "content_items"
    __table_args__ = (UniqueConstraint("topic_id", "component"),)

    topic_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("topics.id"), index=True)
    component: Mapped[Component] = mapped_column(str_enum(Component, "content_component"))
    published_version_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("content_versions.id", use_alter=True)
    )

    topic: Mapped[Topic] = relationship(lazy="joined")


class ContentVersion(UUIDPrimaryKey, Base):
    """An immutable snapshot of a component. A database trigger rejects changes to `body`; edits
    and restores create new versions, so history is never rewritten."""

    __tablename__ = "content_versions"
    __table_args__ = (UniqueConstraint("item_id", "number"),)

    item_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("content_items.id"), index=True)
    number: Mapped[int]
    body: Mapped[dict[str, Any]] = mapped_column(JSONB)
    status: Mapped[VersionStatus] = mapped_column(
        str_enum(VersionStatus, "version_status"), default=VersionStatus.DRAFT, index=True
    )
    origin: Mapped[VersionOrigin] = mapped_column(str_enum(VersionOrigin, "version_origin"))
    based_on_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("content_versions.id"))
    model: Mapped[str | None] = mapped_column(String(200))
    job_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("jobs.id"), index=True)
    note: Mapped[str | None] = mapped_column(String(500))
    created_by_admin_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("admin_users.id"))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    reviewed_by_admin_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("admin_users.id"))
    reviewed_at: Mapped[datetime | None]
    review_note: Mapped[str | None] = mapped_column(String(1000))
    published_at: Mapped[datetime | None]

    item: Mapped[ContentItem] = relationship(foreign_keys=[item_id], lazy="joined")
    created_by: Mapped[AdminUser | None] = relationship(
        foreign_keys=[created_by_admin_id], lazy="joined"
    )
    reviewed_by: Mapped[AdminUser | None] = relationship(
        foreign_keys=[reviewed_by_admin_id], lazy="joined"
    )


class CodeCheck(Base):
    """A run of a Python lab's code (in a reviewer's browser sandbox). Append-only. Publishing a
    Python version needs a passing check for exactly its code."""

    __tablename__ = "code_checks"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    version_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("content_versions.id"), index=True)
    code_hash: Mapped[str] = mapped_column(String(64))
    passed: Mapped[bool]
    output: Mapped[str] = mapped_column(Text)
    error: Mapped[str | None] = mapped_column(Text)
    runtime: Mapped[str] = mapped_column(String(100))
    duration_ms: Mapped[int]
    ran_by_admin_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("admin_users.id"))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class MediaAsset(UUIDPrimaryKey, Base):
    """Generated media for a version, e.g. one narration clip per video scene."""

    __tablename__ = "media_assets"
    __table_args__ = (UniqueConstraint("version_id", "kind", "position"),)

    version_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("content_versions.id"), index=True)
    kind: Mapped[str] = mapped_column(String(32))
    position: Mapped[int]
    content_type: Mapped[str] = mapped_column(String(100))
    data: Mapped[bytes] = mapped_column(LargeBinary)
    size: Mapped[int]
    model: Mapped[str | None] = mapped_column(String(200))
    voice: Mapped[str | None] = mapped_column(String(100))
    job_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("jobs.id"))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class PlatformSetting(Base):
    """Platform-wide switches decided by admins, e.g. the content-expansion gate."""

    __tablename__ = "platform_settings"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[Any] = mapped_column(JSONB)
    updated_by_admin_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("admin_users.id"))
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())


EXPANSION_APPROVED = "content_expansion_approved"
