import uuid
from datetime import datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import (
    BigInteger,
    ForeignKey,
    Identity,
    Index,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.admin import AdminUser
from app.models.base import Base, Timestamps, UUIDPrimaryKey, str_enum


class ConnectorType(StrEnum):
    WEB_PAGES = "web_pages"
    JSON_API = "json_api"
    RSS_FEED = "rss_feed"
    FILE_UPLOAD = "file_upload"


class AuthMethod(StrEnum):
    NONE = "none"
    HTTP_BASIC = "http_basic"
    BEARER_TOKEN = "bearer_token"  # noqa: S105 (a method name, not a secret)
    API_KEY_HEADER = "api_key_header"
    API_KEY_QUERY = "api_key_query"
    FORM_LOGIN = "form_login"


class ConnectionStatus(StrEnum):
    UNTESTED = "untested"
    OK = "ok"
    FAILED = "failed"
    # The source blocks automated access (robots.txt, CAPTCHA, MFA): import files instead.
    MANUAL_IMPORT_REQUIRED = "manual_import_required"


class InterviewSource(UUIDPrimaryKey, Timestamps, Base):
    """An admin-configured place interview data comes from. Removing one archives it, so the
    records it produced keep their provenance."""

    __tablename__ = "interview_sources"

    name: Mapped[str] = mapped_column(String(120))
    description: Mapped[str] = mapped_column(Text, default="")
    base_url: Mapped[str | None] = mapped_column(String(2048))
    connector_type: Mapped[ConnectorType] = mapped_column(str_enum(ConnectorType, "connector_type"))
    auth_method: Mapped[AuthMethod] = mapped_column(
        str_enum(AuthMethod, "auth_method"), default=AuthMethod.NONE
    )
    # Non-secret settings only: connector options and auth details such as a header name.
    config: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    auth_config: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    # Connector-specific incremental cursor (e.g. the time of the last successful API sync).
    sync_state: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    enabled: Mapped[bool] = mapped_column(default=True)
    archived_at: Mapped[datetime | None]

    connection_status: Mapped[ConnectionStatus] = mapped_column(
        str_enum(ConnectionStatus, "connection_status"), default=ConnectionStatus.UNTESTED
    )
    connection_message: Mapped[str | None] = mapped_column(String(500))
    last_tested_at: Mapped[datetime | None]
    last_attempted_sync_at: Mapped[datetime | None]
    last_successful_sync_at: Mapped[datetime | None]
    created_by_admin_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("admin_users.id"))

    credential: Mapped["SourceCredential | None"] = relationship(
        lazy="joined", cascade="all, delete-orphan", passive_deletes=True
    )


# Names are unique (case-insensitively) among sources that have not been removed.
Index(
    "uq_interview_sources_active_name",
    func.lower(InterviewSource.name),
    unique=True,
    postgresql_where=InterviewSource.archived_at.is_(None),
)


class SourceCredential(Base):
    """A source's secrets as one Fernet token. Only the *names* of the stored fields are kept in
    clear text, so the console can say what is set without ever being able to show it."""

    __tablename__ = "source_credentials"

    source_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("interview_sources.id", ondelete="CASCADE"), primary_key=True
    )
    ciphertext: Mapped[str] = mapped_column(Text)
    key_id: Mapped[str] = mapped_column(String(16))
    fields: Mapped[list[str]] = mapped_column(ARRAY(String(64)))
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())
    updated_by_admin_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("admin_users.id"))

    updated_by: Mapped[AdminUser | None] = relationship(lazy="joined")


class RawSourceRecord(Base):
    """One document exactly as fetched or imported from a source. Append-only and permanent:
    a changed document is stored as a new revision, so provenance is never rewritten."""

    __tablename__ = "raw_source_records"
    __table_args__ = (UniqueConstraint("source_id", "external_id", "revision"),)

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    source_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("interview_sources.id"), index=True)
    job_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("jobs.id"), index=True)
    # The source's own identifier: page URL, API item id, feed GUID or file row.
    external_id: Mapped[str] = mapped_column(String(1024))
    revision: Mapped[int] = mapped_column(default=1)
    url: Mapped[str | None] = mapped_column(String(2048))
    title: Mapped[str | None] = mapped_column(String(500))
    content_type: Mapped[str] = mapped_column(String(100))
    content: Mapped[str] = mapped_column(Text)
    content_hash: Mapped[str] = mapped_column(String(64))
    published_at: Mapped[datetime | None]
    meta: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    fetched_at: Mapped[datetime] = mapped_column(server_default=func.now(), index=True)
