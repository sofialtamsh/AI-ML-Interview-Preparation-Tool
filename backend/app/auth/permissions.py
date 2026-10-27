"""Admin permission catalogue and system roles: the single source of truth for RBAC.

Permissions are synced into the database by `python -m app.cli sync-rbac` (run after every
migration). Every admin endpoint declares the permission it needs via `require_permission`.
"""

from dataclasses import dataclass
from enum import StrEnum


class Perm(StrEnum):
    ADMINS_MANAGE = "admins.manage"
    ROLES_MANAGE = "roles.manage"
    AUDIT_VIEW = "audit.view"
    SETTINGS_MANAGE = "settings.manage"
    AI_USAGE_VIEW = "ai_usage.view"
    SOURCES_VIEW = "sources.view"
    SOURCES_MANAGE = "sources.manage"
    SOURCE_CREDENTIALS_MANAGE = "sources.credentials.manage"
    AGENTS_VIEW = "agents.view"
    AGENTS_RUN = "agents.run"
    INTELLIGENCE_VIEW = "intelligence.view"
    INTELLIGENCE_REVIEW = "intelligence.review"
    TAXONOMY_MANAGE = "taxonomy.manage"
    CONTENT_GENERATE = "content.generate"
    CONTENT_REVIEW = "content.review"
    CONTENT_PUBLISH = "content.publish"
    STUDENTS_VIEW = "students.view"
    STUDENTS_MANAGE = "students.manage"
    ANALYTICS_VIEW = "analytics.view"
    ANALYTICS_EXPORT = "analytics.export"
    RANKINGS_VIEW = "rankings.view"


PERMISSION_DESCRIPTIONS: dict[Perm, str] = {
    Perm.ADMINS_MANAGE: "Create admin accounts, assign roles, disable admins",
    Perm.ROLES_MANAGE: "Create and edit custom admin roles",
    Perm.AUDIT_VIEW: "View the admin audit log",
    Perm.SETTINGS_MANAGE: "Change platform settings, including the content-expansion gate",
    Perm.AI_USAGE_VIEW: "View AI spend (USD) and the AI provider's credit status",
    Perm.SOURCES_VIEW: "View configured interview data sources (never their secrets)",
    Perm.SOURCES_MANAGE: "Add, edit, enable/disable and test interview data sources",
    Perm.SOURCE_CREDENTIALS_MANAGE: "Set or rotate interview-source credentials",
    Perm.AGENTS_VIEW: "View agent runs, reports and execution history",
    Perm.AGENTS_RUN: "Trigger the exploration and market-research agents",
    Perm.INTELLIGENCE_VIEW: "View raw interview records, including company and source details",
    Perm.INTELLIGENCE_REVIEW: "Approve, reject or merge extracted interview records",
    Perm.TAXONOMY_MANAGE: "Manage domains and topics; decide on curriculum recommendations",
    Perm.CONTENT_GENERATE: "Use the content generation studio",
    Perm.CONTENT_REVIEW: "Review, edit and reject generated content",
    Perm.CONTENT_PUBLISH: "Approve, publish, unpublish and archive content",
    Perm.STUDENTS_VIEW: "View the student directory, profiles and progress",
    Perm.STUDENTS_MANAGE: "Change student account status and cohorts",
    Perm.ANALYTICS_VIEW: "View platform and student performance analytics",
    Perm.ANALYTICS_EXPORT: "Export analytics and student reports",
    Perm.RANKINGS_VIEW: "View role-readiness rankings and AI performance reports",
}

if set(PERMISSION_DESCRIPTIONS) != set(Perm):
    raise RuntimeError("Every permission needs a description.")


@dataclass(frozen=True)
class RoleDefinition:
    name: str
    description: str
    permissions: frozenset[Perm]


SUPER_ADMIN = "super_admin"

SYSTEM_ROLES: dict[str, RoleDefinition] = {
    SUPER_ADMIN: RoleDefinition(
        "Super Admin", "Unrestricted access to every admin capability.", frozenset(Perm)
    ),
    "intelligence_operator": RoleDefinition(
        "Intelligence Operator",
        "Runs interview sources and agents, and reviews extracted intelligence.",
        frozenset(
            {
                Perm.SOURCES_VIEW,
                Perm.SOURCES_MANAGE,
                Perm.SOURCE_CREDENTIALS_MANAGE,
                Perm.AGENTS_VIEW,
                Perm.AGENTS_RUN,
                Perm.INTELLIGENCE_VIEW,
                Perm.INTELLIGENCE_REVIEW,
            }
        ),
    ),
    "content_manager": RoleDefinition(
        "Content Manager",
        "Curates the taxonomy and generates learning content for review.",
        frozenset(
            {
                Perm.AGENTS_VIEW,
                Perm.INTELLIGENCE_VIEW,
                Perm.TAXONOMY_MANAGE,
                Perm.CONTENT_GENERATE,
                Perm.CONTENT_REVIEW,
            }
        ),
    ),
    "content_publisher": RoleDefinition(
        "Content Reviewer & Publisher",
        "Reviews generated content and decides what students see.",
        frozenset({Perm.INTELLIGENCE_VIEW, Perm.CONTENT_REVIEW, Perm.CONTENT_PUBLISH}),
    ),
    "student_success": RoleDefinition(
        "Student Success",
        "Supports students: manages accounts and monitors performance.",
        frozenset(
            {
                Perm.STUDENTS_VIEW,
                Perm.STUDENTS_MANAGE,
                Perm.ANALYTICS_VIEW,
                Perm.RANKINGS_VIEW,
            }
        ),
    ),
    "analyst": RoleDefinition(
        "Analyst",
        "Read-only access to analytics, rankings and intelligence.",
        frozenset(
            {
                Perm.STUDENTS_VIEW,
                Perm.ANALYTICS_VIEW,
                Perm.ANALYTICS_EXPORT,
                Perm.RANKINGS_VIEW,
                Perm.INTELLIGENCE_VIEW,
                Perm.AGENTS_VIEW,
            }
        ),
    ),
}
