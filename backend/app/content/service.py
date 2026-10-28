"""The content lifecycle: draft → under review → approved → published → archived.

Versions are immutable (a database trigger enforces it), so edits and restores create new
versions. Publishing a version makes it the one students see and archives the previous one.
A Python lab can only be published after a passing code check of exactly its program.
"""

import hashlib
import uuid
from dataclasses import dataclass
from typing import Any

from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.content.schemas import SCHEMAS, PythonLab
from app.core.errors import UserFacingError
from app.core.security import utcnow
from app.models import (
    EXPANSION_APPROVED,
    CodeCheck,
    Component,
    ContentItem,
    ContentVersion,
    PlatformSetting,
    Topic,
    VersionOrigin,
    VersionStatus,
)


class ContentError(UserFacingError):
    pass


class InvalidBody(ContentError):
    def __init__(self, exc: ValidationError) -> None:
        problems = [
            f"{'.'.join(str(part) for part in error['loc']) or 'body'}: {error['msg']}"
            for error in exc.errors(include_input=False, include_url=False)[:8]
        ]
        super().__init__("The content doesn't match its format. " + "; ".join(problems))
        self.problems = problems


def validate_body(component: Component, body: dict[str, Any]) -> dict[str, Any]:
    """The body in canonical form, or InvalidBody."""
    try:
        return SCHEMAS[component].model_validate(body).model_dump(mode="json")
    except ValidationError as exc:
        raise InvalidBody(exc) from None


# --- Items and versions ---------------------------------------------------------------------


def get_item(db: Session, topic: Topic, component: Component) -> ContentItem:
    item = db.scalar(
        select(ContentItem).where(
            ContentItem.topic_id == topic.id, ContentItem.component == component
        )
    )
    if item is None:
        item = ContentItem(topic_id=topic.id, component=component)
        db.add(item)
        db.flush()
    return item


def create_version(
    db: Session,
    item: ContentItem,
    body: dict[str, Any],
    *,
    origin: VersionOrigin,
    admin_id: uuid.UUID | None = None,
    note: str | None = None,
    model: str | None = None,
    job_id: uuid.UUID | None = None,
    based_on: ContentVersion | None = None,
) -> ContentVersion:
    canonical = validate_body(item.component, body)
    number = (
        db.scalar(select(func.max(ContentVersion.number)).where(ContentVersion.item_id == item.id))
        or 0
    ) + 1
    version = ContentVersion(
        item_id=item.id,
        number=number,
        body=canonical,
        status=VersionStatus.DRAFT,
        origin=origin,
        based_on_id=based_on.id if based_on else None,
        model=model,
        job_id=job_id,
        note=(note or "")[:500] or None,
        created_by_admin_id=admin_id,
    )
    db.add(version)
    db.flush()
    item.updated_at = utcnow()
    return version


def program_hash(body: dict[str, Any]) -> str:
    return hashlib.sha256(PythonLab.model_validate(body).program.encode()).hexdigest()


def normalise_output(text: str) -> str:
    return "\n".join(line.rstrip() for line in text.strip().splitlines())


def has_passing_check(db: Session, version: ContentVersion) -> bool:
    return bool(
        db.scalar(
            select(func.count()).where(
                CodeCheck.version_id == version.id,
                CodeCheck.code_hash == program_hash(version.body),
                CodeCheck.passed.is_(True),
            )
        )
    )


def record_code_check(
    db: Session,
    version: ContentVersion,
    *,
    output: str,
    error: str | None,
    duration_ms: int,
    runtime: str,
    admin_id: uuid.UUID,
) -> CodeCheck:
    """Store a run of the lab (made in a reviewer's browser sandbox). The server, not the
    client, decides whether it passed: no error, and output matching the expected output."""
    if version.item.component is not Component.PYTHON:
        raise ContentError("Only Python labs have code checks.")
    expected = PythonLab.model_validate(version.body).expected_output
    passed = error is None and normalise_output(output) == normalise_output(expected)
    check = CodeCheck(
        version_id=version.id,
        code_hash=program_hash(version.body),
        passed=passed,
        output=output[:20_000],
        error=(error or None) and error[:5000],
        runtime=runtime[:100],
        duration_ms=max(0, duration_ms),
        ran_by_admin_id=admin_id,
    )
    db.add(check)
    db.flush()
    return check


# --- Lifecycle ------------------------------------------------------------------------------


@dataclass(frozen=True)
class Transition:
    to: VersionStatus
    sources: frozenset[VersionStatus]
    needs: frozenset[str]  # any one of these permissions
    done: str  # past tense, for messages


_EDITABLE = frozenset({VersionStatus.DRAFT, VersionStatus.UNDER_REVIEW, VersionStatus.APPROVED})
_REVIEW = frozenset({"content.review"})
_PUBLISH = frozenset({"content.publish"})

TRANSITIONS: dict[str, Transition] = {
    "submit": Transition(
        VersionStatus.UNDER_REVIEW,
        frozenset({VersionStatus.DRAFT}),
        frozenset({"content.generate", "content.review"}),
        "submitted for review",
    ),
    "send_back": Transition(
        VersionStatus.DRAFT,
        frozenset({VersionStatus.UNDER_REVIEW, VersionStatus.APPROVED}),
        _REVIEW,
        "sent back to draft",
    ),
    "reject": Transition(VersionStatus.REJECTED, _EDITABLE, _REVIEW, "rejected"),
    "approve": Transition(
        VersionStatus.APPROVED, frozenset({VersionStatus.UNDER_REVIEW}), _PUBLISH, "approved"
    ),
    "publish": Transition(
        VersionStatus.PUBLISHED, frozenset({VersionStatus.APPROVED}), _PUBLISH, "published"
    ),
    "unpublish": Transition(
        VersionStatus.APPROVED, frozenset({VersionStatus.PUBLISHED}), _PUBLISH, "unpublished"
    ),
    "archive": Transition(
        VersionStatus.ARCHIVED, _EDITABLE | {VersionStatus.REJECTED}, _PUBLISH, "archived"
    ),
}


def apply_transition(
    db: Session,
    version: ContentVersion,
    action: str,
    *,
    admin_id: uuid.UUID,
    permissions: set[str],
    note: str | None = None,
) -> VersionStatus:
    """Move a version along the lifecycle. Returns the previous status. Raises PermissionError
    when the admin lacks the permission the step needs."""
    rule = TRANSITIONS.get(action)
    if rule is None:
        raise ContentError(f"Unknown action: {action}.")
    if not rule.needs & permissions:
        raise PermissionError(action)
    if version.status not in rule.sources:
        raise ContentError(
            f"This version is {version.status.value.replace('_', ' ')}, so it can't be {rule.done}."
        )
    item = version.item
    previous = version.status
    now = utcnow()

    if action == "publish":
        if item.component is Component.PYTHON and not has_passing_check(db, version):
            raise ContentError(
                "Run the code check first: a Python lab can only be published after its exact "
                "code has run and produced the expected output."
            )
        if item.published_version_id and item.published_version_id != version.id:
            current = db.get(ContentVersion, item.published_version_id)
            if current is not None:
                current.status = VersionStatus.ARCHIVED
        item.published_version_id = version.id
        version.published_at = now
    elif action == "unpublish":
        item.published_version_id = None

    version.status = rule.to
    if action in ("approve", "reject", "send_back", "publish", "unpublish", "archive"):
        version.reviewed_by_admin_id = admin_id
        version.reviewed_at = now
    if note is not None:
        version.review_note = note[:1000] or None
    item.updated_at = now
    return previous


def restore(db: Session, version: ContentVersion, admin_id: uuid.UUID) -> ContentVersion:
    """A new draft with the same content as an earlier version."""
    return create_version(
        db,
        version.item,
        version.body,
        origin=VersionOrigin.EDITED,
        admin_id=admin_id,
        note=f"Restored from version {version.number}",
        based_on=version,
    )


# --- The pilot gate -------------------------------------------------------------------------


def expansion_approved(db: Session) -> bool:
    setting = db.get(PlatformSetting, EXPANSION_APPROVED)
    return bool(setting and setting.value is True)


def may_generate(db: Session, topic: Topic) -> bool:
    """Content generation is limited to pilot topics until an admin approves expansion."""
    return topic.is_pilot or expansion_approved(db)
