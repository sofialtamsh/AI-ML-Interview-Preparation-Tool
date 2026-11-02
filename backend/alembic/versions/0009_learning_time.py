"""Time spent learning: an active_time learning event and a per-topic total

Revision ID: 0009
Revises: 0008
Create Date: 2026-10-28 18:30:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0009"
down_revision: str | Sequence[str] | None = "0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

KINDS = (
    "section_opened",
    "section_done",
    "lesson_progress",
    "playground_task",
    "video_progress",
    "code_run",
    "interview_take",
)


def _event_kinds(kinds: tuple[str, ...]) -> None:
    op.drop_constraint(op.f("ck_learning_events_event_kind"), "learning_events", type_="check")
    allowed = ", ".join(f"'{kind}'" for kind in kinds)
    op.create_check_constraint(
        op.f("ck_learning_events_event_kind"), "learning_events", sa.text(f"kind IN ({allowed})")
    )


def upgrade() -> None:
    """Upgrade schema."""
    _event_kinds((*KINDS, "active_time"))
    op.add_column(
        "topic_progress",
        sa.Column("active_seconds", sa.Integer(), server_default="0", nullable=False),
    )


def downgrade() -> None:
    """Downgrade schema. learning_events is append-only, so active_time rows must be gone first."""
    op.drop_column("topic_progress", "active_seconds")
    _event_kinds(KINDS)
