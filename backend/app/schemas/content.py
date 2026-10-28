import uuid
from datetime import datetime
from decimal import Decimal
from typing import Annotated, Any, Literal

from pydantic import Field, StringConstraints

from app.models import Component, ContentVersion, VersionOrigin, VersionStatus
from app.schemas.common import ApiModel
from app.schemas.intelligence import AgentJob
from app.schemas.sources import JobEventOut

Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=200)]
Note = Annotated[str, StringConstraints(strip_whitespace=True, max_length=1000)]


class VersionSummary(ApiModel):
    id: uuid.UUID
    number: int
    status: VersionStatus
    origin: VersionOrigin
    model: str | None
    note: str | None
    created_at: datetime
    created_by: str | None
    reviewed_by: str | None
    reviewed_at: datetime | None
    review_note: str | None
    published_at: datetime | None
    job_id: uuid.UUID | None
    based_on_id: uuid.UUID | None

    @classmethod
    def of(cls, v: ContentVersion) -> "VersionSummary":
        return cls(
            id=v.id,
            number=v.number,
            status=v.status,
            origin=v.origin,
            model=v.model,
            note=v.note,
            created_at=v.created_at,
            created_by=v.created_by.full_name if v.created_by else None,
            reviewed_by=v.reviewed_by.full_name if v.reviewed_by else None,
            reviewed_at=v.reviewed_at,
            review_note=v.review_note,
            published_at=v.published_at,
            job_id=v.job_id,
            based_on_id=v.based_on_id,
        )


class TopicRefOut(ApiModel):
    id: uuid.UUID
    slug: str
    name: str
    domain_name: str
    is_pilot: bool


class ComponentState(ApiModel):
    component: Component
    item_id: uuid.UUID | None
    published_number: int | None
    latest: VersionSummary | None
    versions: list[VersionSummary]


class TopicContent(ApiModel):
    topic: TopicRefOut
    may_generate: bool
    has_playground: bool
    components: list[ComponentState]


class TopicContentSummary(ApiModel):
    topic: TopicRefOut
    statuses: dict[str, str | None]  # component -> latest version status
    live: list[str]  # components with a published version (students see these)
    published: int
    may_generate: bool


class ContentOverview(ApiModel):
    expansion_approved: bool
    ai_configured: bool
    content_model: str
    narration_model: str
    narration_voices: list[str]
    topics: list[TopicContentSummary]


class CodeCheckOut(ApiModel):
    id: int
    passed: bool
    output: str
    error: str | None
    runtime: str
    duration_ms: int
    created_at: datetime
    current: bool  # it ran this version's exact code


class MediaOut(ApiModel):
    id: uuid.UUID
    position: int
    size: int
    voice: str | None


class VersionDetail(VersionSummary):
    component: Component
    topic: TopicRefOut
    body: dict[str, Any]
    published: bool
    code_checks: list[CodeCheckOut]
    narration: list[MediaOut]


class VersionEdit(ApiModel):
    body: dict[str, Any]
    based_on_id: uuid.UUID | None = None
    note: Annotated[str, StringConstraints(strip_whitespace=True, max_length=500)] = ""


class TransitionIn(ApiModel):
    action: Literal["submit", "send_back", "reject", "approve", "publish", "unpublish", "archive"]
    note: Note | None = None


class BulkTransitionIn(ApiModel):
    action: Literal["submit", "approve", "publish"]


class BulkTransitionResult(ApiModel):
    changed: list[str]
    skipped: dict[str, str]


class CodeCheckIn(ApiModel):
    output: Annotated[str, StringConstraints(max_length=50_000)]
    error: Annotated[str, StringConstraints(max_length=10_000)] | None = None
    duration_ms: int = Field(ge=0, le=600_000)
    runtime: Annotated[str, StringConstraints(max_length=100)]


class GenerateIn(ApiModel):
    topic_ids: list[uuid.UUID] = Field(min_length=1, max_length=20)
    components: list[Component] = Field(min_length=1)
    use_intelligence: bool = True
    max_cost_usd: Decimal = Field(default=Decimal("2"), gt=0, le=100)


class GenerateSkipped(ApiModel):
    topic_id: uuid.UUID
    name: str | None
    reason: str


class ContentJob(AgentJob):
    topic: TopicRefOut | None


class ContentJobDetail(ContentJob):
    payload: dict[str, Any]
    events: list[JobEventOut]


class NarrateIn(ApiModel):
    voice: Annotated[str, StringConstraints(max_length=100)]


class ExpansionIn(ApiModel):
    approved: bool


# --- Taxonomy (admin) ----------------------------------------------------------------------------


class TopicAdmin(ApiModel):
    id: uuid.UUID
    slug: str
    name: str
    description: str
    parent_id: uuid.UUID | None
    is_pilot: bool
    archived: bool
    published_components: int


class DomainAdmin(ApiModel):
    id: uuid.UUID
    slug: str
    name: str
    description: str
    archived: bool
    topics: list[TopicAdmin]


class DomainCreate(ApiModel):
    name: Name
    description: Note = ""


class DomainUpdate(ApiModel):
    name: Name | None = None
    description: Note | None = None
    archived: bool | None = None


class TopicCreate(ApiModel):
    domain_id: uuid.UUID
    name: Name
    description: Note = ""
    parent_id: uuid.UUID | None = None


class TopicUpdate(ApiModel):
    name: Name | None = None
    description: Note | None = None
    archived: bool | None = None
    is_pilot: bool | None = None
