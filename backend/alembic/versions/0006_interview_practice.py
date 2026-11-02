"""Interview practice: spoken-answer attempts with AI feedback; AI spend attributed to students

Revision ID: 0006
Revises: 0005
Create Date: 2026-10-28 10:12:54.842321

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0006"
down_revision: str | Sequence[str] | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "practice_attempts",
        sa.Column("student_id", sa.Uuid(), nullable=False),
        sa.Column("topic_id", sa.Uuid(), nullable=False),
        sa.Column("version_id", sa.Uuid(), nullable=False),
        sa.Column("question_index", sa.Integer(), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "queued",
                "processing",
                "completed",
                "no_answer",
                "failed",
                name="attempt_status",
                native_enum=False,
                create_constraint=True,
                length=32,
            ),
            nullable=False,
        ),
        sa.Column("duration_ms", sa.Integer(), nullable=False),
        sa.Column("audio", sa.LargeBinary(), nullable=True),
        sa.Column("transcript", sa.Text(), nullable=True),
        sa.Column("delivery", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("feedback", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("score", sa.Numeric(precision=3, scale=1), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("transcription_model", sa.String(length=200), nullable=True),
        sa.Column("feedback_model", sa.String(length=200), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("heartbeat_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["student_id"], ["students.id"], name=op.f("fk_practice_attempts_student_id_students")
        ),
        sa.ForeignKeyConstraint(
            ["topic_id"], ["topics.id"], name=op.f("fk_practice_attempts_topic_id_topics")
        ),
        sa.ForeignKeyConstraint(
            ["version_id"],
            ["content_versions.id"],
            name=op.f("fk_practice_attempts_version_id_content_versions"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_practice_attempts")),
    )
    op.create_index(op.f("ix_practice_attempts_status"), "practice_attempts", ["status"])
    op.create_index(
        "ix_practice_attempts_student_created", "practice_attempts", ["student_id", "created_at"]
    )
    op.create_index(op.f("ix_practice_attempts_topic_id"), "practice_attempts", ["topic_id"])
    op.add_column("ai_usage_events", sa.Column("triggered_by_student_id", sa.Uuid(), nullable=True))
    op.add_column("ai_usage_events", sa.Column("practice_attempt_id", sa.Uuid(), nullable=True))
    op.create_index(
        op.f("ix_ai_usage_events_practice_attempt_id"), "ai_usage_events", ["practice_attempt_id"]
    )
    op.create_index(
        op.f("ix_ai_usage_events_triggered_by_student_id"),
        "ai_usage_events",
        ["triggered_by_student_id"],
    )
    op.create_foreign_key(
        op.f("fk_ai_usage_events_practice_attempt_id_practice_attempts"),
        "ai_usage_events",
        "practice_attempts",
        ["practice_attempt_id"],
        ["id"],
    )
    op.create_foreign_key(
        op.f("fk_ai_usage_events_triggered_by_student_id_students"),
        "ai_usage_events",
        "students",
        ["triggered_by_student_id"],
        ["id"],
    )
    # A student's "delete" erases the transcript and feedback; the row itself stays.
    op.execute(
        "CREATE TRIGGER practice_attempts_no_delete BEFORE DELETE ON practice_attempts "
        "FOR EACH ROW EXECUTE FUNCTION forbid_row_delete()"
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("DROP TRIGGER practice_attempts_no_delete ON practice_attempts")
    op.drop_constraint(
        op.f("fk_ai_usage_events_triggered_by_student_id_students"),
        "ai_usage_events",
        type_="foreignkey",
    )
    op.drop_constraint(
        op.f("fk_ai_usage_events_practice_attempt_id_practice_attempts"),
        "ai_usage_events",
        type_="foreignkey",
    )
    op.drop_index(op.f("ix_ai_usage_events_triggered_by_student_id"), table_name="ai_usage_events")
    op.drop_index(op.f("ix_ai_usage_events_practice_attempt_id"), table_name="ai_usage_events")
    op.drop_column("ai_usage_events", "practice_attempt_id")
    op.drop_column("ai_usage_events", "triggered_by_student_id")
    op.drop_index(op.f("ix_practice_attempts_topic_id"), table_name="practice_attempts")
    op.drop_index("ix_practice_attempts_student_created", table_name="practice_attempts")
    op.drop_index(op.f("ix_practice_attempts_status"), table_name="practice_attempts")
    op.drop_table("practice_attempts")
