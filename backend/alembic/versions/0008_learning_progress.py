"""Learning progress: events, per-topic progress, quiz attempts and responses (never overwritten)

Revision ID: 0008
Revises: 0007
Create Date: 2026-10-28 14:10:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0008"
down_revision: str | Sequence[str] | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

APPEND_ONLY_TABLES = ("learning_events", "quiz_attempts", "quiz_responses")
UNDELETABLE_TABLES = ("topic_progress",)


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "topic_progress",
        sa.Column("student_id", sa.Uuid(), nullable=False),
        sa.Column("topic_id", sa.Uuid(), nullable=False),
        sa.Column("sections", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("last_component", sa.String(length=32), nullable=True),
        sa.Column(
            "first_visited_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "last_visited_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["student_id"], ["students.id"], name=op.f("fk_topic_progress_student_id_students")
        ),
        sa.ForeignKeyConstraint(
            ["topic_id"], ["topics.id"], name=op.f("fk_topic_progress_topic_id_topics")
        ),
        sa.PrimaryKeyConstraint("student_id", "topic_id", name=op.f("pk_topic_progress")),
    )
    op.create_index(
        op.f("ix_topic_progress_last_visited_at"),
        "topic_progress",
        ["last_visited_at"],
        unique=False,
    )
    op.create_table(
        "learning_events",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), nullable=False),
        sa.Column("student_id", sa.Uuid(), nullable=False),
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
        sa.Column(
            "kind",
            sa.Enum(
                "section_opened",
                "section_done",
                "lesson_progress",
                "playground_task",
                "video_progress",
                "code_run",
                "interview_take",
                name="event_kind",
                native_enum=False,
                create_constraint=True,
                length=32,
            ),
            nullable=False,
        ),
        sa.Column("version_id", sa.Uuid(), nullable=True),
        sa.Column("data", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "occurred_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["student_id"], ["students.id"], name=op.f("fk_learning_events_student_id_students")
        ),
        sa.ForeignKeyConstraint(
            ["topic_id"], ["topics.id"], name=op.f("fk_learning_events_topic_id_topics")
        ),
        sa.ForeignKeyConstraint(
            ["version_id"],
            ["content_versions.id"],
            name=op.f("fk_learning_events_version_id_content_versions"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_learning_events")),
    )
    op.create_index(
        "ix_learning_events_student_time",
        "learning_events",
        ["student_id", "occurred_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_learning_events_topic_id"), "learning_events", ["topic_id"], unique=False
    )
    op.create_table(
        "quiz_attempts",
        sa.Column("student_id", sa.Uuid(), nullable=False),
        sa.Column("topic_id", sa.Uuid(), nullable=False),
        sa.Column("version_id", sa.Uuid(), nullable=False),
        sa.Column("attempt_number", sa.Integer(), nullable=False),
        sa.Column("total", sa.Integer(), nullable=False),
        sa.Column("correct", sa.Integer(), nullable=False),
        sa.Column("score_pct", sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column("duration_seconds", sa.Integer(), nullable=True),
        sa.Column(
            "submitted_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["student_id"], ["students.id"], name=op.f("fk_quiz_attempts_student_id_students")
        ),
        sa.ForeignKeyConstraint(
            ["topic_id"], ["topics.id"], name=op.f("fk_quiz_attempts_topic_id_topics")
        ),
        sa.ForeignKeyConstraint(
            ["version_id"],
            ["content_versions.id"],
            name=op.f("fk_quiz_attempts_version_id_content_versions"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_quiz_attempts")),
    )
    op.create_index(
        "ix_quiz_attempts_student_topic",
        "quiz_attempts",
        ["student_id", "topic_id", "submitted_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_quiz_attempts_submitted_at"), "quiz_attempts", ["submitted_at"], unique=False
    )
    op.create_index(op.f("ix_quiz_attempts_topic_id"), "quiz_attempts", ["topic_id"], unique=False)
    op.create_table(
        "quiz_responses",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), nullable=False),
        sa.Column("attempt_id", sa.Uuid(), nullable=False),
        sa.Column("question_index", sa.Integer(), nullable=False),
        sa.Column("chosen", sa.Integer(), nullable=True),
        sa.Column("correct", sa.Boolean(), nullable=False),
        sa.Column("difficulty", sa.String(length=16), nullable=False),
        sa.Column("kind", sa.String(length=16), nullable=False),
        sa.ForeignKeyConstraint(
            ["attempt_id"],
            ["quiz_attempts.id"],
            name=op.f("fk_quiz_responses_attempt_id_quiz_attempts"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_quiz_responses")),
    )
    op.create_index(
        op.f("ix_quiz_responses_attempt_id"), "quiz_responses", ["attempt_id"], unique=False
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
    op.drop_index(op.f("ix_quiz_responses_attempt_id"), table_name="quiz_responses")
    op.drop_table("quiz_responses")
    op.drop_index(op.f("ix_quiz_attempts_topic_id"), table_name="quiz_attempts")
    op.drop_index(op.f("ix_quiz_attempts_submitted_at"), table_name="quiz_attempts")
    op.drop_index("ix_quiz_attempts_student_topic", table_name="quiz_attempts")
    op.drop_table("quiz_attempts")
    op.drop_index(op.f("ix_learning_events_topic_id"), table_name="learning_events")
    op.drop_index("ix_learning_events_student_time", table_name="learning_events")
    op.drop_table("learning_events")
    op.drop_index(op.f("ix_topic_progress_last_visited_at"), table_name="topic_progress")
    op.drop_table("topic_progress")
