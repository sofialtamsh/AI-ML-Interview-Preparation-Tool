"""Content quality: AI review reports, reviewer ratings, the content_review job kind

Revision ID: 0007
Revises: 0006
Create Date: 2026-10-28 13:05:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0007"
down_revision: str | Sequence[str] | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

OLD_JOB_KINDS = (
    "source_fetch",
    "source_import",
    "exploration",
    "market_research",
    "content_generation",
    "content_narration",
)
NEW_JOB_KINDS = (*OLD_JOB_KINDS, "content_review")
APPEND_ONLY_TABLES = ("content_quality_reviews", "content_ratings")


def _job_kinds(kinds: tuple[str, ...]) -> None:
    op.drop_constraint(op.f("ck_jobs_job_kind"), "jobs", type_="check")
    allowed = ", ".join(f"'{kind}'" for kind in kinds)
    op.create_check_constraint(op.f("ck_jobs_job_kind"), "jobs", sa.text(f"kind IN ({allowed})"))


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "content_quality_reviews",
        sa.Column("version_id", sa.Uuid(), nullable=False),
        sa.Column("job_id", sa.Uuid(), nullable=True),
        sa.Column("model", sa.String(length=200), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("scores", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("issues", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("quiz_check", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("dropped_issues", sa.Integer(), nullable=False),
        sa.Column("requested_by_admin_id", sa.Uuid(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["job_id"], ["jobs.id"], name=op.f("fk_content_quality_reviews_job_id_jobs")
        ),
        sa.ForeignKeyConstraint(
            ["requested_by_admin_id"],
            ["admin_users.id"],
            name=op.f("fk_content_quality_reviews_requested_by_admin_id_admin_users"),
        ),
        sa.ForeignKeyConstraint(
            ["version_id"],
            ["content_versions.id"],
            name=op.f("fk_content_quality_reviews_version_id_content_versions"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_content_quality_reviews")),
    )
    op.create_index(
        op.f("ix_content_quality_reviews_version_id"), "content_quality_reviews", ["version_id"]
    )
    op.create_table(
        "content_ratings",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), nullable=False),
        sa.Column("version_id", sa.Uuid(), nullable=False),
        sa.Column("admin_id", sa.Uuid(), nullable=False),
        sa.Column("scores", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("note", sa.String(length=1000), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["admin_id"], ["admin_users.id"], name=op.f("fk_content_ratings_admin_id_admin_users")
        ),
        sa.ForeignKeyConstraint(
            ["version_id"],
            ["content_versions.id"],
            name=op.f("fk_content_ratings_version_id_content_versions"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_content_ratings")),
    )
    op.create_index(op.f("ix_content_ratings_version_id"), "content_ratings", ["version_id"])
    _job_kinds(NEW_JOB_KINDS)
    for table in APPEND_ONLY_TABLES:
        op.execute(
            f"CREATE TRIGGER {table}_append_only BEFORE UPDATE OR DELETE ON {table} "
            "FOR EACH ROW EXECUTE FUNCTION forbid_row_change()"
        )


def downgrade() -> None:
    """Downgrade schema."""
    for table in APPEND_ONLY_TABLES:
        op.execute(f"DROP TRIGGER {table}_append_only ON {table}")
    _job_kinds(OLD_JOB_KINDS)
    op.drop_index(op.f("ix_content_ratings_version_id"), table_name="content_ratings")
    op.drop_table("content_ratings")
    op.drop_index(
        op.f("ix_content_quality_reviews_version_id"), table_name="content_quality_reviews"
    )
    op.drop_table("content_quality_reviews")
