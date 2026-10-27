"""AI usage ledger; activity logs become permanent (append-only)

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-27 10:46:06.739758

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0002"
down_revision: str | Sequence[str] | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Activity logs and the spend ledger are kept permanently: the database itself rejects any
# UPDATE or DELETE, so no application bug or admin action can rewrite history.
APPEND_ONLY_TABLES = ("audit_logs", "login_events", "ai_usage_events")


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "ai_usage_events",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), nullable=False),
        sa.Column(
            "occurred_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("feature", sa.String(length=64), nullable=False),
        sa.Column("model", sa.String(length=200), nullable=False),
        sa.Column("generation_id", sa.String(length=128), nullable=True),
        sa.Column("input_tokens", sa.Integer(), nullable=True),
        sa.Column("output_tokens", sa.Integer(), nullable=True),
        sa.Column("cost_usd", sa.Numeric(precision=16, scale=8), nullable=False),
        sa.Column("triggered_by_admin_id", sa.Uuid(), nullable=True),
        sa.ForeignKeyConstraint(
            ["triggered_by_admin_id"],
            ["admin_users.id"],
            name=op.f("fk_ai_usage_events_triggered_by_admin_id_admin_users"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ai_usage_events")),
        sa.UniqueConstraint("generation_id", name=op.f("uq_ai_usage_events_generation_id")),
    )
    op.create_index(op.f("ix_ai_usage_events_feature"), "ai_usage_events", ["feature"])
    op.create_index(op.f("ix_ai_usage_events_occurred_at"), "ai_usage_events", ["occurred_at"])
    op.create_index(
        op.f("ix_ai_usage_events_triggered_by_admin_id"),
        "ai_usage_events",
        ["triggered_by_admin_id"],
    )

    op.execute(
        """
        CREATE FUNCTION forbid_row_change() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION '% is append-only: its rows are kept permanently', TG_TABLE_NAME;
        END
        $$
        """
    )
    for table in APPEND_ONLY_TABLES:
        op.execute(
            f"CREATE TRIGGER {table}_append_only BEFORE UPDATE OR DELETE ON {table} "
            "FOR EACH ROW EXECUTE FUNCTION forbid_row_change()"
        )


def downgrade() -> None:
    """Downgrade schema."""
    for table in APPEND_ONLY_TABLES:
        op.execute(f"DROP TRIGGER {table}_append_only ON {table}")
    op.execute("DROP FUNCTION forbid_row_change()")

    op.drop_index(op.f("ix_ai_usage_events_triggered_by_admin_id"), table_name="ai_usage_events")
    op.drop_index(op.f("ix_ai_usage_events_occurred_at"), table_name="ai_usage_events")
    op.drop_index(op.f("ix_ai_usage_events_feature"), table_name="ai_usage_events")
    op.drop_table("ai_usage_events")
