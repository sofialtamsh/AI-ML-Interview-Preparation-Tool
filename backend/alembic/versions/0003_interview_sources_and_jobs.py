"""Interview data sources, encrypted credentials, background jobs and permanent raw records

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-27 12:16:37.463036

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0003"
down_revision: str | Sequence[str] | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Source records and job logs are permanent (product owner decision, 2026-10-27): the database
# rejects any change or deletion. Sources and jobs change state, but are never deleted either.
APPEND_ONLY_TABLES = ("raw_source_records", "job_events")
UNDELETABLE_TABLES = ("interview_sources", "jobs")


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "interview_sources",
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("base_url", sa.String(length=2048), nullable=True),
        sa.Column(
            "connector_type",
            sa.Enum(
                "web_pages",
                "json_api",
                "rss_feed",
                "file_upload",
                name="connector_type",
                native_enum=False,
                create_constraint=True,
                length=32,
            ),
            nullable=False,
        ),
        sa.Column(
            "auth_method",
            sa.Enum(
                "none",
                "http_basic",
                "bearer_token",
                "api_key_header",
                "api_key_query",
                "form_login",
                name="auth_method",
                native_enum=False,
                create_constraint=True,
                length=32,
            ),
            nullable=False,
        ),
        sa.Column("config", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("auth_config", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("sync_state", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "connection_status",
            sa.Enum(
                "untested",
                "ok",
                "failed",
                "manual_import_required",
                name="connection_status",
                native_enum=False,
                create_constraint=True,
                length=32,
            ),
            nullable=False,
        ),
        sa.Column("connection_message", sa.String(length=500), nullable=True),
        sa.Column("last_tested_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_attempted_sync_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_successful_sync_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by_admin_id", sa.Uuid(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["created_by_admin_id"],
            ["admin_users.id"],
            name=op.f("fk_interview_sources_created_by_admin_id_admin_users"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_interview_sources")),
    )
    op.create_index(
        "uq_interview_sources_active_name",
        "interview_sources",
        [sa.literal_column("lower(name)")],
        unique=True,
        postgresql_where=sa.text("archived_at IS NULL"),
    )
    op.create_table(
        "jobs",
        sa.Column(
            "kind",
            sa.Enum(
                "source_fetch",
                "source_import",
                name="job_kind",
                native_enum=False,
                create_constraint=True,
                length=32,
            ),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum(
                "queued",
                "running",
                "succeeded",
                "completed_with_errors",
                "failed",
                "cancelled",
                name="job_status",
                native_enum=False,
                create_constraint=True,
                length=32,
            ),
            nullable=False,
        ),
        sa.Column("source_id", sa.Uuid(), nullable=True),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("result", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("progress_done", sa.Integer(), nullable=False),
        sa.Column("progress_total", sa.Integer(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("cancel_requested", sa.Boolean(), nullable=False),
        sa.Column("triggered_by_admin_id", sa.Uuid(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("heartbeat_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["source_id"],
            ["interview_sources.id"],
            name=op.f("fk_jobs_source_id_interview_sources"),
        ),
        sa.ForeignKeyConstraint(
            ["triggered_by_admin_id"],
            ["admin_users.id"],
            name=op.f("fk_jobs_triggered_by_admin_id_admin_users"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_jobs")),
    )
    op.create_index(op.f("ix_jobs_created_at"), "jobs", ["created_at"], unique=False)
    op.create_index(op.f("ix_jobs_kind"), "jobs", ["kind"], unique=False)
    op.create_index(op.f("ix_jobs_source_id"), "jobs", ["source_id"], unique=False)
    op.create_index(op.f("ix_jobs_status"), "jobs", ["status"], unique=False)
    op.create_index(
        op.f("ix_jobs_triggered_by_admin_id"), "jobs", ["triggered_by_admin_id"], unique=False
    )
    op.create_index(
        "uq_jobs_one_active_fetch_per_source",
        "jobs",
        ["source_id"],
        unique=True,
        postgresql_where=sa.text("kind = 'source_fetch' AND status IN ('queued', 'running')"),
    )
    op.create_table(
        "source_credentials",
        sa.Column("source_id", sa.Uuid(), nullable=False),
        sa.Column("ciphertext", sa.Text(), nullable=False),
        sa.Column("key_id", sa.String(length=16), nullable=False),
        sa.Column("fields", postgresql.ARRAY(sa.String(length=64)), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("updated_by_admin_id", sa.Uuid(), nullable=True),
        sa.ForeignKeyConstraint(
            ["source_id"],
            ["interview_sources.id"],
            name=op.f("fk_source_credentials_source_id_interview_sources"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["updated_by_admin_id"],
            ["admin_users.id"],
            name=op.f("fk_source_credentials_updated_by_admin_id_admin_users"),
        ),
        sa.PrimaryKeyConstraint("source_id", name=op.f("pk_source_credentials")),
    )
    op.create_table(
        "job_events",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), nullable=False),
        sa.Column("job_id", sa.Uuid(), nullable=False),
        sa.Column(
            "level",
            sa.Enum(
                "info",
                "warning",
                "error",
                name="job_event_level",
                native_enum=False,
                create_constraint=True,
                length=32,
            ),
            nullable=False,
        ),
        sa.Column("message", sa.String(length=1000), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"], name=op.f("fk_job_events_job_id_jobs")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_job_events")),
    )
    op.create_index(op.f("ix_job_events_job_id"), "job_events", ["job_id"], unique=False)
    op.create_table(
        "raw_source_records",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), nullable=False),
        sa.Column("source_id", sa.Uuid(), nullable=False),
        sa.Column("job_id", sa.Uuid(), nullable=False),
        sa.Column("external_id", sa.String(length=1024), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("url", sa.String(length=2048), nullable=True),
        sa.Column("title", sa.String(length=500), nullable=True),
        sa.Column("content_type", sa.String(length=100), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("meta", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "fetched_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["job_id"], ["jobs.id"], name=op.f("fk_raw_source_records_job_id_jobs")
        ),
        sa.ForeignKeyConstraint(
            ["source_id"],
            ["interview_sources.id"],
            name=op.f("fk_raw_source_records_source_id_interview_sources"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_raw_source_records")),
        sa.UniqueConstraint(
            "source_id", "external_id", "revision", name=op.f("uq_raw_source_records_source_id")
        ),
    )
    op.create_index(
        op.f("ix_raw_source_records_fetched_at"), "raw_source_records", ["fetched_at"], unique=False
    )
    op.create_index(
        op.f("ix_raw_source_records_job_id"), "raw_source_records", ["job_id"], unique=False
    )
    op.create_index(
        op.f("ix_raw_source_records_source_id"), "raw_source_records", ["source_id"], unique=False
    )

    for table in APPEND_ONLY_TABLES:
        op.execute(
            f"CREATE TRIGGER {table}_append_only BEFORE UPDATE OR DELETE ON {table} "
            "FOR EACH ROW EXECUTE FUNCTION forbid_row_change()"
        )
    op.execute(
        """
        CREATE FUNCTION forbid_row_delete() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION '% rows are kept permanently and cannot be deleted', TG_TABLE_NAME;
        END
        $$
        """
    )
    for table in UNDELETABLE_TABLES:
        op.execute(
            f"CREATE TRIGGER {table}_no_delete BEFORE DELETE ON {table} "
            "FOR EACH ROW EXECUTE FUNCTION forbid_row_delete()"
        )


def downgrade() -> None:
    """Downgrade schema."""
    for table in UNDELETABLE_TABLES:
        op.execute(f"DROP TRIGGER {table}_no_delete ON {table}")
    op.execute("DROP FUNCTION forbid_row_delete()")
    for table in APPEND_ONLY_TABLES:
        op.execute(f"DROP TRIGGER {table}_append_only ON {table}")

    op.drop_index(op.f("ix_raw_source_records_source_id"), table_name="raw_source_records")
    op.drop_index(op.f("ix_raw_source_records_job_id"), table_name="raw_source_records")
    op.drop_index(op.f("ix_raw_source_records_fetched_at"), table_name="raw_source_records")
    op.drop_table("raw_source_records")
    op.drop_index(op.f("ix_job_events_job_id"), table_name="job_events")
    op.drop_table("job_events")
    op.drop_table("source_credentials")
    op.drop_index(
        "uq_jobs_one_active_fetch_per_source",
        table_name="jobs",
        postgresql_where=sa.text("kind = 'source_fetch' AND status IN ('queued', 'running')"),
    )
    op.drop_index(op.f("ix_jobs_triggered_by_admin_id"), table_name="jobs")
    op.drop_index(op.f("ix_jobs_status"), table_name="jobs")
    op.drop_index(op.f("ix_jobs_source_id"), table_name="jobs")
    op.drop_index(op.f("ix_jobs_kind"), table_name="jobs")
    op.drop_index(op.f("ix_jobs_created_at"), table_name="jobs")
    op.drop_table("jobs")
    op.drop_index(
        "uq_interview_sources_active_name",
        table_name="interview_sources",
        postgresql_where=sa.text("archived_at IS NULL"),
    )
    op.drop_table("interview_sources")
