"""Taxonomy, interview intelligence and market research; agent jobs; run costs

Revision ID: 0004
Revises: 0003
Create Date: 2026-10-27 14:50:28.398635

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0004"
down_revision: str | Sequence[str] | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Reports, their evidence and extraction attempts are written once and kept as they are.
APPEND_ONLY_TABLES = (
    "record_extractions",
    "research_reports",
    "research_sources",
    "research_findings",
    "finding_evidence",
)
# Reviewed or decided rows change status, but are never deleted (provenance is permanent).
UNDELETABLE_TABLES = (
    "domains",
    "topics",
    "interview_experiences",
    "interview_questions",
    "curriculum_recommendations",
    "research_questions",
)
OLD_JOB_KINDS = ("source_fetch", "source_import")
NEW_JOB_KINDS = (*OLD_JOB_KINDS, "exploration", "market_research")


def _job_kinds(kinds: tuple[str, ...]) -> None:
    op.drop_constraint(op.f("ck_jobs_job_kind"), "jobs", type_="check")
    allowed = ", ".join(f"'{kind}'" for kind in kinds)
    op.create_check_constraint(op.f("ck_jobs_job_kind"), "jobs", sa.text(f"kind IN ({allowed})"))


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "domains",
        sa.Column("slug", sa.String(length=80), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.PrimaryKeyConstraint("id", name=op.f("pk_domains")),
        sa.UniqueConstraint("slug", name=op.f("uq_domains_slug")),
    )
    op.create_table(
        "topics",
        sa.Column("domain_id", sa.Uuid(), nullable=False),
        sa.Column("parent_id", sa.Uuid(), nullable=True),
        sa.Column("slug", sa.String(length=200), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("is_pilot", sa.Boolean(), nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
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
            name=op.f("fk_topics_created_by_admin_id_admin_users"),
        ),
        sa.ForeignKeyConstraint(
            ["domain_id"], ["domains.id"], name=op.f("fk_topics_domain_id_domains")
        ),
        sa.ForeignKeyConstraint(
            ["parent_id"], ["topics.id"], name=op.f("fk_topics_parent_id_topics")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_topics")),
        sa.UniqueConstraint("slug", name=op.f("uq_topics_slug")),
    )
    op.create_index(op.f("ix_topics_domain_id"), "topics", ["domain_id"], unique=False)
    op.create_index(op.f("ix_topics_parent_id"), "topics", ["parent_id"], unique=False)
    op.create_table(
        "research_reports",
        sa.Column("job_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("scope", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("model", sa.String(length=200), nullable=False),
        sa.Column("triggered_by_admin_id", sa.Uuid(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["job_id"], ["jobs.id"], name=op.f("fk_research_reports_job_id_jobs")
        ),
        sa.ForeignKeyConstraint(
            ["triggered_by_admin_id"],
            ["admin_users.id"],
            name=op.f("fk_research_reports_triggered_by_admin_id_admin_users"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_research_reports")),
        sa.UniqueConstraint("job_id", name=op.f("uq_research_reports_job_id")),
    )
    op.create_index(
        op.f("ix_research_reports_created_at"), "research_reports", ["created_at"], unique=False
    )
    op.create_table(
        "curriculum_recommendations",
        sa.Column("report_id", sa.Uuid(), nullable=False),
        sa.Column(
            "kind",
            sa.Enum(
                "add_topic",
                "prioritize",
                "deprioritize",
                "update_content",
                name="recommendation_kind",
                native_enum=False,
                create_constraint=True,
                length=32,
            ),
            nullable=False,
        ),
        sa.Column("topic_id", sa.Uuid(), nullable=True),
        sa.Column("domain_id", sa.Uuid(), nullable=True),
        sa.Column("proposed_name", sa.String(length=200), nullable=True),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("finding_ids", postgresql.ARRAY(sa.BigInteger()), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "pending",
                "approved",
                "rejected",
                "deferred",
                name="decision",
                native_enum=False,
                create_constraint=True,
                length=32,
            ),
            nullable=False,
        ),
        sa.Column("decided_by_admin_id", sa.Uuid(), nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("decision_note", sa.String(length=1000), nullable=True),
        sa.Column("created_topic_id", sa.Uuid(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["created_topic_id"],
            ["topics.id"],
            name=op.f("fk_curriculum_recommendations_created_topic_id_topics"),
        ),
        sa.ForeignKeyConstraint(
            ["decided_by_admin_id"],
            ["admin_users.id"],
            name=op.f("fk_curriculum_recommendations_decided_by_admin_id_admin_users"),
        ),
        sa.ForeignKeyConstraint(
            ["domain_id"],
            ["domains.id"],
            name=op.f("fk_curriculum_recommendations_domain_id_domains"),
        ),
        sa.ForeignKeyConstraint(
            ["report_id"],
            ["research_reports.id"],
            name=op.f("fk_curriculum_recommendations_report_id_research_reports"),
        ),
        sa.ForeignKeyConstraint(
            ["topic_id"], ["topics.id"], name=op.f("fk_curriculum_recommendations_topic_id_topics")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_curriculum_recommendations")),
    )
    op.create_index(
        op.f("ix_curriculum_recommendations_report_id"),
        "curriculum_recommendations",
        ["report_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_curriculum_recommendations_status"),
        "curriculum_recommendations",
        ["status"],
        unique=False,
    )
    op.create_table(
        "interview_experiences",
        sa.Column("source_id", sa.Uuid(), nullable=False),
        sa.Column("record_id", sa.BigInteger(), nullable=False),
        sa.Column("job_id", sa.Uuid(), nullable=False),
        sa.Column("company", sa.String(length=200), nullable=True),
        sa.Column("role", sa.String(length=200), nullable=True),
        sa.Column("interview_date", sa.Date(), nullable=True),
        sa.Column("period", sa.String(length=100), nullable=True),
        sa.Column("location", sa.String(length=200), nullable=True),
        sa.Column("technologies", postgresql.ARRAY(sa.String(length=100)), nullable=False),
        sa.Column("confidence", sa.Double(), nullable=True),
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
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["job_id"], ["jobs.id"], name=op.f("fk_interview_experiences_job_id_jobs")
        ),
        sa.ForeignKeyConstraint(
            ["record_id"],
            ["raw_source_records.id"],
            name=op.f("fk_interview_experiences_record_id_raw_source_records"),
        ),
        sa.ForeignKeyConstraint(
            ["source_id"],
            ["interview_sources.id"],
            name=op.f("fk_interview_experiences_source_id_interview_sources"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_interview_experiences")),
    )
    op.create_index(
        op.f("ix_interview_experiences_company"), "interview_experiences", ["company"], unique=False
    )
    op.create_index(
        op.f("ix_interview_experiences_job_id"), "interview_experiences", ["job_id"], unique=False
    )
    op.create_index(
        op.f("ix_interview_experiences_record_id"),
        "interview_experiences",
        ["record_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_interview_experiences_role"), "interview_experiences", ["role"], unique=False
    )
    op.create_index(
        op.f("ix_interview_experiences_source_id"),
        "interview_experiences",
        ["source_id"],
        unique=False,
    )
    op.create_table(
        "record_extractions",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), nullable=False),
        sa.Column("record_id", sa.BigInteger(), nullable=False),
        sa.Column("source_id", sa.Uuid(), nullable=False),
        sa.Column("job_id", sa.Uuid(), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "extracted",
                "not_interview",
                "failed",
                name="extraction_status",
                native_enum=False,
                create_constraint=True,
                length=32,
            ),
            nullable=False,
        ),
        sa.Column("model", sa.String(length=200), nullable=True),
        sa.Column("questions_found", sa.Integer(), nullable=False),
        sa.Column("error", sa.String(length=500), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["job_id"], ["jobs.id"], name=op.f("fk_record_extractions_job_id_jobs")
        ),
        sa.ForeignKeyConstraint(
            ["record_id"],
            ["raw_source_records.id"],
            name=op.f("fk_record_extractions_record_id_raw_source_records"),
        ),
        sa.ForeignKeyConstraint(
            ["source_id"],
            ["interview_sources.id"],
            name=op.f("fk_record_extractions_source_id_interview_sources"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_record_extractions")),
    )
    op.create_index(
        op.f("ix_record_extractions_job_id"), "record_extractions", ["job_id"], unique=False
    )
    op.create_index(
        op.f("ix_record_extractions_record_id"), "record_extractions", ["record_id"], unique=False
    )
    op.create_index(
        op.f("ix_record_extractions_source_id"), "record_extractions", ["source_id"], unique=False
    )
    op.create_table(
        "research_findings",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), nullable=False),
        sa.Column("report_id", sa.Uuid(), nullable=False),
        sa.Column("topic_id", sa.Uuid(), nullable=True),
        sa.Column("topic_label", sa.String(length=200), nullable=False),
        sa.Column("roles", postgresql.ARRAY(sa.String(length=120)), nullable=False),
        sa.Column("skills", postgresql.ARRAY(sa.String(length=120)), nullable=False),
        sa.Column("observation", sa.Text(), nullable=False),
        sa.Column(
            "trend",
            sa.Enum(
                "emerging",
                "rising",
                "stable",
                "declining",
                "unclear",
                name="trend",
                native_enum=False,
                create_constraint=True,
                length=32,
            ),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["report_id"],
            ["research_reports.id"],
            name=op.f("fk_research_findings_report_id_research_reports"),
        ),
        sa.ForeignKeyConstraint(
            ["topic_id"], ["topics.id"], name=op.f("fk_research_findings_topic_id_topics")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_research_findings")),
    )
    op.create_index(
        op.f("ix_research_findings_report_id"), "research_findings", ["report_id"], unique=False
    )
    op.create_index(
        op.f("ix_research_findings_topic_id"), "research_findings", ["topic_id"], unique=False
    )
    op.create_table(
        "research_questions",
        sa.Column("report_id", sa.Uuid(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("topic_id", sa.Uuid(), nullable=True),
        sa.Column("topic_label", sa.String(length=200), nullable=False),
        sa.Column("role", sa.String(length=120), nullable=True),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("finding_ids", postgresql.ARRAY(sa.BigInteger()), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "pending_review",
                "approved",
                "rejected",
                name="review_status",
                native_enum=False,
                create_constraint=True,
                length=32,
            ),
            nullable=False,
        ),
        sa.Column("reviewed_by_admin_id", sa.Uuid(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["report_id"],
            ["research_reports.id"],
            name=op.f("fk_research_questions_report_id_research_reports"),
        ),
        sa.ForeignKeyConstraint(
            ["reviewed_by_admin_id"],
            ["admin_users.id"],
            name=op.f("fk_research_questions_reviewed_by_admin_id_admin_users"),
        ),
        sa.ForeignKeyConstraint(
            ["topic_id"], ["topics.id"], name=op.f("fk_research_questions_topic_id_topics")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_research_questions")),
    )
    op.create_index(
        op.f("ix_research_questions_report_id"), "research_questions", ["report_id"], unique=False
    )
    op.create_index(
        op.f("ix_research_questions_status"), "research_questions", ["status"], unique=False
    )
    op.create_index(
        op.f("ix_research_questions_topic_id"), "research_questions", ["topic_id"], unique=False
    )
    op.create_table(
        "research_sources",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), nullable=False),
        sa.Column("report_id", sa.Uuid(), nullable=False),
        sa.Column("url", sa.String(length=2048), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("site", sa.String(length=255), nullable=False),
        sa.Column("excerpt", sa.Text(), nullable=False),
        sa.Column(
            "accessed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["report_id"],
            ["research_reports.id"],
            name=op.f("fk_research_sources_report_id_research_reports"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_research_sources")),
    )
    op.create_index(
        op.f("ix_research_sources_report_id"), "research_sources", ["report_id"], unique=False
    )
    op.create_table(
        "finding_evidence",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), nullable=False),
        sa.Column("finding_id", sa.BigInteger(), nullable=False),
        sa.Column("source_id", sa.BigInteger(), nullable=False),
        sa.Column("quote", sa.Text(), nullable=True),
        sa.Column("quote_verified", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(
            ["finding_id"],
            ["research_findings.id"],
            name=op.f("fk_finding_evidence_finding_id_research_findings"),
        ),
        sa.ForeignKeyConstraint(
            ["source_id"],
            ["research_sources.id"],
            name=op.f("fk_finding_evidence_source_id_research_sources"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_finding_evidence")),
    )
    op.create_index(
        op.f("ix_finding_evidence_finding_id"), "finding_evidence", ["finding_id"], unique=False
    )
    op.create_index(
        op.f("ix_finding_evidence_source_id"), "finding_evidence", ["source_id"], unique=False
    )
    op.create_table(
        "interview_questions",
        sa.Column("experience_id", sa.Uuid(), nullable=False),
        sa.Column("source_id", sa.Uuid(), nullable=False),
        sa.Column("record_id", sa.BigInteger(), nullable=False),
        sa.Column("job_id", sa.Uuid(), nullable=False),
        sa.Column("original_text", sa.Text(), nullable=False),
        sa.Column("normalized_hash", sa.String(length=64), nullable=False),
        sa.Column("round", sa.String(length=120), nullable=True),
        sa.Column(
            "question_type",
            sa.Enum(
                "conceptual",
                "coding",
                "math",
                "ml_system_design",
                "case_study",
                "project",
                "behavioral",
                "other",
                name="question_type",
                native_enum=False,
                create_constraint=True,
                length=32,
            ),
            nullable=False,
        ),
        sa.Column(
            "difficulty",
            sa.Enum(
                "easy",
                "medium",
                "hard",
                name="difficulty",
                native_enum=False,
                create_constraint=True,
                length=32,
            ),
            nullable=True,
        ),
        sa.Column("topic_id", sa.Uuid(), nullable=True),
        sa.Column("suggested_topic", sa.String(length=200), nullable=True),
        sa.Column("technologies", postgresql.ARRAY(sa.String(length=100)), nullable=False),
        sa.Column("grounded", sa.Boolean(), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "pending_review",
                "approved",
                "rejected",
                name="review_status",
                native_enum=False,
                create_constraint=True,
                length=32,
            ),
            nullable=False,
        ),
        sa.Column("duplicate_of_id", sa.Uuid(), nullable=True),
        sa.Column("reviewed_by_admin_id", sa.Uuid(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("review_note", sa.String(length=500), nullable=True),
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
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["duplicate_of_id"],
            ["interview_questions.id"],
            name=op.f("fk_interview_questions_duplicate_of_id_interview_questions"),
        ),
        sa.ForeignKeyConstraint(
            ["experience_id"],
            ["interview_experiences.id"],
            name=op.f("fk_interview_questions_experience_id_interview_experiences"),
        ),
        sa.ForeignKeyConstraint(
            ["job_id"], ["jobs.id"], name=op.f("fk_interview_questions_job_id_jobs")
        ),
        sa.ForeignKeyConstraint(
            ["record_id"],
            ["raw_source_records.id"],
            name=op.f("fk_interview_questions_record_id_raw_source_records"),
        ),
        sa.ForeignKeyConstraint(
            ["reviewed_by_admin_id"],
            ["admin_users.id"],
            name=op.f("fk_interview_questions_reviewed_by_admin_id_admin_users"),
        ),
        sa.ForeignKeyConstraint(
            ["source_id"],
            ["interview_sources.id"],
            name=op.f("fk_interview_questions_source_id_interview_sources"),
        ),
        sa.ForeignKeyConstraint(
            ["topic_id"], ["topics.id"], name=op.f("fk_interview_questions_topic_id_topics")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_interview_questions")),
    )
    op.create_index(
        op.f("ix_interview_questions_created_at"),
        "interview_questions",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_interview_questions_duplicate_of_id"),
        "interview_questions",
        ["duplicate_of_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_interview_questions_experience_id"),
        "interview_questions",
        ["experience_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_interview_questions_job_id"), "interview_questions", ["job_id"], unique=False
    )
    op.create_index(
        op.f("ix_interview_questions_normalized_hash"),
        "interview_questions",
        ["normalized_hash"],
        unique=False,
    )
    op.create_index(
        op.f("ix_interview_questions_record_id"), "interview_questions", ["record_id"], unique=False
    )
    op.create_index(
        op.f("ix_interview_questions_source_id"), "interview_questions", ["source_id"], unique=False
    )
    op.create_index(
        op.f("ix_interview_questions_status"), "interview_questions", ["status"], unique=False
    )
    op.create_index(
        op.f("ix_interview_questions_topic_id"), "interview_questions", ["topic_id"], unique=False
    )
    op.add_column("ai_usage_events", sa.Column("job_id", sa.Uuid(), nullable=True))
    op.create_index(op.f("ix_ai_usage_events_job_id"), "ai_usage_events", ["job_id"], unique=False)
    op.create_foreign_key(
        op.f("fk_ai_usage_events_job_id_jobs"), "ai_usage_events", "jobs", ["job_id"], ["id"]
    )
    op.drop_index(
        op.f("uq_jobs_one_active_fetch_per_source"),
        table_name="jobs",
        postgresql_where="(((kind)::text = 'source_fetch'::text) AND ((status)::text = ANY ((ARRAY['queued'::character varying, 'running'::character varying])::text[])))",
    )
    op.create_index(
        "uq_jobs_one_active_run_per_source",
        "jobs",
        ["source_id"],
        unique=True,
        postgresql_where=sa.text(
            "kind IN ('source_fetch', 'exploration') AND status IN ('queued', 'running')"
        ),
    )

    _job_kinds(NEW_JOB_KINDS)
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
    _job_kinds(OLD_JOB_KINDS)
    op.drop_index(
        "uq_jobs_one_active_run_per_source",
        table_name="jobs",
        postgresql_where=sa.text(
            "kind IN ('source_fetch', 'exploration') AND status IN ('queued', 'running')"
        ),
    )
    op.create_index(
        op.f("uq_jobs_one_active_fetch_per_source"),
        "jobs",
        ["source_id"],
        unique=True,
        postgresql_where="(((kind)::text = 'source_fetch'::text) AND ((status)::text = ANY ((ARRAY['queued'::character varying, 'running'::character varying])::text[])))",
    )
    op.drop_constraint(
        op.f("fk_ai_usage_events_job_id_jobs"), "ai_usage_events", type_="foreignkey"
    )
    op.drop_index(op.f("ix_ai_usage_events_job_id"), table_name="ai_usage_events")
    op.drop_column("ai_usage_events", "job_id")
    op.drop_index(op.f("ix_interview_questions_topic_id"), table_name="interview_questions")
    op.drop_index(op.f("ix_interview_questions_status"), table_name="interview_questions")
    op.drop_index(op.f("ix_interview_questions_source_id"), table_name="interview_questions")
    op.drop_index(op.f("ix_interview_questions_record_id"), table_name="interview_questions")
    op.drop_index(op.f("ix_interview_questions_normalized_hash"), table_name="interview_questions")
    op.drop_index(op.f("ix_interview_questions_job_id"), table_name="interview_questions")
    op.drop_index(op.f("ix_interview_questions_experience_id"), table_name="interview_questions")
    op.drop_index(op.f("ix_interview_questions_duplicate_of_id"), table_name="interview_questions")
    op.drop_index(op.f("ix_interview_questions_created_at"), table_name="interview_questions")
    op.drop_table("interview_questions")
    op.drop_index(op.f("ix_finding_evidence_source_id"), table_name="finding_evidence")
    op.drop_index(op.f("ix_finding_evidence_finding_id"), table_name="finding_evidence")
    op.drop_table("finding_evidence")
    op.drop_index(op.f("ix_research_sources_report_id"), table_name="research_sources")
    op.drop_table("research_sources")
    op.drop_index(op.f("ix_research_questions_topic_id"), table_name="research_questions")
    op.drop_index(op.f("ix_research_questions_status"), table_name="research_questions")
    op.drop_index(op.f("ix_research_questions_report_id"), table_name="research_questions")
    op.drop_table("research_questions")
    op.drop_index(op.f("ix_research_findings_topic_id"), table_name="research_findings")
    op.drop_index(op.f("ix_research_findings_report_id"), table_name="research_findings")
    op.drop_table("research_findings")
    op.drop_index(op.f("ix_record_extractions_source_id"), table_name="record_extractions")
    op.drop_index(op.f("ix_record_extractions_record_id"), table_name="record_extractions")
    op.drop_index(op.f("ix_record_extractions_job_id"), table_name="record_extractions")
    op.drop_table("record_extractions")
    op.drop_index(op.f("ix_interview_experiences_source_id"), table_name="interview_experiences")
    op.drop_index(op.f("ix_interview_experiences_role"), table_name="interview_experiences")
    op.drop_index(op.f("ix_interview_experiences_record_id"), table_name="interview_experiences")
    op.drop_index(op.f("ix_interview_experiences_job_id"), table_name="interview_experiences")
    op.drop_index(op.f("ix_interview_experiences_company"), table_name="interview_experiences")
    op.drop_table("interview_experiences")
    op.drop_index(
        op.f("ix_curriculum_recommendations_status"), table_name="curriculum_recommendations"
    )
    op.drop_index(
        op.f("ix_curriculum_recommendations_report_id"), table_name="curriculum_recommendations"
    )
    op.drop_table("curriculum_recommendations")
    op.drop_index(op.f("ix_research_reports_created_at"), table_name="research_reports")
    op.drop_table("research_reports")
    op.drop_index(op.f("ix_topics_parent_id"), table_name="topics")
    op.drop_index(op.f("ix_topics_domain_id"), table_name="topics")
    op.drop_table("topics")
    op.drop_table("domains")
