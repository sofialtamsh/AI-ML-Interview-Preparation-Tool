"""Learning content: items, immutable versions, code checks, media, platform settings

Revision ID: 0005
Revises: 0004
Create Date: 2026-10-27 15:47:17.927384

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0005"
down_revision: str | Sequence[str] | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

OLD_JOB_KINDS = ("source_fetch", "source_import", "exploration", "market_research")
NEW_JOB_KINDS = (*OLD_JOB_KINDS, "content_generation", "content_narration")
APPEND_ONLY_TABLES = ("code_checks",)
UNDELETABLE_TABLES = ("content_items", "content_versions", "media_assets")
PUBLISHED_FK = "fk_content_items_published_version_id_content_versions"


def _job_kinds(kinds: tuple[str, ...]) -> None:
    op.drop_constraint(op.f("ck_jobs_job_kind"), "jobs", type_="check")
    allowed = ", ".join(f"'{kind}'" for kind in kinds)
    op.create_check_constraint(op.f("ck_jobs_job_kind"), "jobs", sa.text(f"kind IN ({allowed})"))


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "platform_settings",
        sa.Column("key", sa.String(length=64), nullable=False),
        sa.Column("value", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("updated_by_admin_id", sa.Uuid(), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["updated_by_admin_id"],
            ["admin_users.id"],
            name=op.f("fk_platform_settings_updated_by_admin_id_admin_users"),
        ),
        sa.PrimaryKeyConstraint("key", name=op.f("pk_platform_settings")),
    )
    op.create_table(
        "content_items",
        sa.Column("topic_id", sa.Uuid(), nullable=False),
        sa.Column(
            "component",
            sa.Enum(
                "lesson",
                "playground",
                "python",
                "interview",
                "quiz",
                "revision",
                "video",
                name="content_component",
                native_enum=False,
                create_constraint=True,
                length=32,
            ),
            nullable=False,
        ),
        sa.Column("published_version_id", sa.Uuid(), nullable=True),
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
            ["topic_id"], ["topics.id"], name=op.f("fk_content_items_topic_id_topics")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_content_items")),
        sa.UniqueConstraint("topic_id", "component", name=op.f("uq_content_items_topic_id")),
    )
    op.create_index(op.f("ix_content_items_topic_id"), "content_items", ["topic_id"], unique=False)
    op.create_table(
        "content_versions",
        sa.Column("item_id", sa.Uuid(), nullable=False),
        sa.Column("number", sa.Integer(), nullable=False),
        sa.Column("body", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "draft",
                "under_review",
                "approved",
                "published",
                "archived",
                "rejected",
                name="version_status",
                native_enum=False,
                create_constraint=True,
                length=32,
            ),
            nullable=False,
        ),
        sa.Column(
            "origin",
            sa.Enum(
                "starter",
                "ai_generated",
                "edited",
                name="version_origin",
                native_enum=False,
                create_constraint=True,
                length=32,
            ),
            nullable=False,
        ),
        sa.Column("based_on_id", sa.Uuid(), nullable=True),
        sa.Column("model", sa.String(length=200), nullable=True),
        sa.Column("job_id", sa.Uuid(), nullable=True),
        sa.Column("note", sa.String(length=500), nullable=True),
        sa.Column("created_by_admin_id", sa.Uuid(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("reviewed_by_admin_id", sa.Uuid(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("review_note", sa.String(length=1000), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["based_on_id"],
            ["content_versions.id"],
            name=op.f("fk_content_versions_based_on_id_content_versions"),
        ),
        sa.ForeignKeyConstraint(
            ["created_by_admin_id"],
            ["admin_users.id"],
            name=op.f("fk_content_versions_created_by_admin_id_admin_users"),
        ),
        sa.ForeignKeyConstraint(
            ["item_id"],
            ["content_items.id"],
            name=op.f("fk_content_versions_item_id_content_items"),
        ),
        sa.ForeignKeyConstraint(
            ["job_id"], ["jobs.id"], name=op.f("fk_content_versions_job_id_jobs")
        ),
        sa.ForeignKeyConstraint(
            ["reviewed_by_admin_id"],
            ["admin_users.id"],
            name=op.f("fk_content_versions_reviewed_by_admin_id_admin_users"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_content_versions")),
        sa.UniqueConstraint("item_id", "number", name=op.f("uq_content_versions_item_id")),
    )
    op.create_index(
        op.f("ix_content_versions_item_id"), "content_versions", ["item_id"], unique=False
    )
    op.create_index(
        op.f("ix_content_versions_job_id"), "content_versions", ["job_id"], unique=False
    )
    op.create_index(
        op.f("ix_content_versions_status"), "content_versions", ["status"], unique=False
    )
    op.create_table(
        "code_checks",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), nullable=False),
        sa.Column("version_id", sa.Uuid(), nullable=False),
        sa.Column("code_hash", sa.String(length=64), nullable=False),
        sa.Column("passed", sa.Boolean(), nullable=False),
        sa.Column("output", sa.Text(), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("runtime", sa.String(length=100), nullable=False),
        sa.Column("duration_ms", sa.Integer(), nullable=False),
        sa.Column("ran_by_admin_id", sa.Uuid(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["ran_by_admin_id"],
            ["admin_users.id"],
            name=op.f("fk_code_checks_ran_by_admin_id_admin_users"),
        ),
        sa.ForeignKeyConstraint(
            ["version_id"],
            ["content_versions.id"],
            name=op.f("fk_code_checks_version_id_content_versions"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_code_checks")),
    )
    op.create_index(op.f("ix_code_checks_version_id"), "code_checks", ["version_id"], unique=False)
    op.create_table(
        "media_assets",
        sa.Column("version_id", sa.Uuid(), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("content_type", sa.String(length=100), nullable=False),
        sa.Column("data", sa.LargeBinary(), nullable=False),
        sa.Column("size", sa.Integer(), nullable=False),
        sa.Column("model", sa.String(length=200), nullable=True),
        sa.Column("voice", sa.String(length=100), nullable=True),
        sa.Column("job_id", sa.Uuid(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"], name=op.f("fk_media_assets_job_id_jobs")),
        sa.ForeignKeyConstraint(
            ["version_id"],
            ["content_versions.id"],
            name=op.f("fk_media_assets_version_id_content_versions"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_media_assets")),
        sa.UniqueConstraint(
            "version_id", "kind", "position", name=op.f("uq_media_assets_version_id")
        ),
    )
    op.create_index(
        op.f("ix_media_assets_version_id"), "media_assets", ["version_id"], unique=False
    )
    op.add_column("jobs", sa.Column("topic_id", sa.Uuid(), nullable=True))
    op.add_column("jobs", sa.Column("batch_id", sa.Uuid(), nullable=True))
    op.create_index(op.f("ix_jobs_batch_id"), "jobs", ["batch_id"], unique=False)
    op.create_index(op.f("ix_jobs_topic_id"), "jobs", ["topic_id"], unique=False)
    op.create_foreign_key(op.f("fk_jobs_topic_id_topics"), "jobs", "topics", ["topic_id"], ["id"])

    op.create_foreign_key(
        op.f(PUBLISHED_FK), "content_items", "content_versions", ["published_version_id"], ["id"]
    )
    _job_kinds(NEW_JOB_KINDS)
    # A version's content never changes: edits and restores create new versions.
    op.execute(
        """
        CREATE FUNCTION forbid_version_body_change() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            IF NEW.body IS DISTINCT FROM OLD.body OR NEW.item_id IS DISTINCT FROM OLD.item_id
               OR NEW.number IS DISTINCT FROM OLD.number THEN
                RAISE EXCEPTION 'content versions are immutable: create a new version instead';
            END IF;
            RETURN NEW;
        END
        $$
        """
    )
    op.execute(
        "CREATE TRIGGER content_versions_immutable BEFORE UPDATE ON content_versions "
        "FOR EACH ROW EXECUTE FUNCTION forbid_version_body_change()"
    )
    for table in APPEND_ONLY_TABLES:
        op.execute(
            f"CREATE TRIGGER {table}_append_only BEFORE UPDATE OR DELETE ON {table} "
            "FOR EACH ROW EXECUTE FUNCTION forbid_row_change()"
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
    for table in APPEND_ONLY_TABLES:
        op.execute(f"DROP TRIGGER {table}_append_only ON {table}")
    op.execute("DROP TRIGGER content_versions_immutable ON content_versions")
    op.execute("DROP FUNCTION forbid_version_body_change()")
    _job_kinds(OLD_JOB_KINDS)
    op.drop_constraint(op.f(PUBLISHED_FK), "content_items", type_="foreignkey")
    op.drop_constraint(op.f("fk_jobs_topic_id_topics"), "jobs", type_="foreignkey")
    op.drop_index(op.f("ix_jobs_topic_id"), table_name="jobs")
    op.drop_index(op.f("ix_jobs_batch_id"), table_name="jobs")
    op.drop_column("jobs", "batch_id")
    op.drop_column("jobs", "topic_id")
    op.drop_index(op.f("ix_media_assets_version_id"), table_name="media_assets")
    op.drop_table("media_assets")
    op.drop_index(op.f("ix_code_checks_version_id"), table_name="code_checks")
    op.drop_table("code_checks")
    op.drop_index(op.f("ix_content_versions_status"), table_name="content_versions")
    op.drop_index(op.f("ix_content_versions_job_id"), table_name="content_versions")
    op.drop_index(op.f("ix_content_versions_item_id"), table_name="content_versions")
    op.drop_table("content_versions")
    op.drop_index(op.f("ix_content_items_topic_id"), table_name="content_items")
    op.drop_table("content_items")
    op.drop_table("platform_settings")
