"""Domains and topics: the admin-editable AI/ML taxonomy. Archived, never deleted.

Changing which topics are pilot topics needs `settings.manage`, because the pilot set is what
keeps content generation from expanding without an explicit decision."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth.deps import AdminContext, require_any_permission, require_permission
from app.auth.permissions import Perm
from app.core.audit import record_audit
from app.core.db import get_db
from app.core.security import utcnow
from app.intelligence.taxonomy import slugify, topic_slug
from app.models import ContentItem, Domain, Topic
from app.schemas.content import (
    DomainAdmin,
    DomainCreate,
    DomainUpdate,
    TopicAdmin,
    TopicCreate,
    TopicUpdate,
)

router = APIRouter(prefix="/taxonomy", tags=["admin-taxonomy"])

can_read = require_any_permission(
    Perm.TAXONOMY_MANAGE, Perm.CONTENT_GENERATE, Perm.CONTENT_REVIEW, Perm.CONTENT_PUBLISH
)
can_manage = require_permission(Perm.TAXONOMY_MANAGE)


def _domains(db: Session) -> list[DomainAdmin]:
    published = dict(
        db.execute(
            select(ContentItem.topic_id, func.count())
            .where(ContentItem.published_version_id.is_not(None))
            .group_by(ContentItem.topic_id)
        ).all()
    )
    # Query topics directly: a domain's cached `topics` collection can be stale after an edit.
    by_domain: dict[uuid.UUID, list[Topic]] = {}
    for topic in db.scalars(select(Topic).order_by(Topic.position, Topic.name)).unique():
        by_domain.setdefault(topic.domain_id, []).append(topic)
    domains = db.scalars(select(Domain).order_by(Domain.position, Domain.name)).unique()
    return [
        DomainAdmin(
            id=d.id,
            slug=d.slug,
            name=d.name,
            description=d.description,
            archived=d.archived_at is not None,
            topics=[
                TopicAdmin(
                    id=t.id,
                    slug=t.slug,
                    name=t.name,
                    description=t.description,
                    parent_id=t.parent_id,
                    is_pilot=t.is_pilot,
                    archived=t.archived_at is not None,
                    published_components=published.get(t.id, 0),
                )
                for t in by_domain.get(d.id, [])
            ],
        )
        for d in domains
    ]


@router.get("", response_model=list[DomainAdmin], dependencies=[Depends(can_read)])
def list_taxonomy(db: Session = Depends(get_db)) -> list[DomainAdmin]:
    return _domains(db)


@router.post("/domains", response_model=list[DomainAdmin], status_code=status.HTTP_201_CREATED)
def create_domain(
    body: DomainCreate,
    request: Request,
    ctx: AdminContext = Depends(can_manage),
    db: Session = Depends(get_db),
) -> list[DomainAdmin]:
    slug = slugify(body.name)
    if db.scalar(select(Domain.id).where(Domain.slug == slug)):
        raise HTTPException(status.HTTP_409_CONFLICT, "A domain with this name already exists.")
    position = (db.scalar(select(func.max(Domain.position))) or 0) + 1
    domain = Domain(slug=slug, name=body.name, description=body.description, position=position)
    db.add(domain)
    db.flush()
    record_audit(
        db, request, ctx, "taxonomy.domain_created", "domain", domain.id, {"name": body.name}
    )
    db.commit()
    return _domains(db)


@router.patch("/domains/{domain_id}", response_model=list[DomainAdmin])
def update_domain(
    domain_id: uuid.UUID,
    body: DomainUpdate,
    request: Request,
    ctx: AdminContext = Depends(can_manage),
    db: Session = Depends(get_db),
) -> list[DomainAdmin]:
    domain = db.get(Domain, domain_id)
    if domain is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Domain not found.")
    changes: dict[str, object] = {}
    if body.name is not None and body.name != domain.name:
        changes["name"] = {"from": domain.name, "to": body.name}
        domain.name = body.name  # the slug stays stable so links keep working
    if body.description is not None and body.description != domain.description:
        changes["description"] = "changed"
        domain.description = body.description
    if body.archived is not None and body.archived != (domain.archived_at is not None):
        changes["archived"] = body.archived
        domain.archived_at = utcnow() if body.archived else None
    if changes:
        record_audit(db, request, ctx, "taxonomy.domain_updated", "domain", domain.id, changes)
        db.commit()
    return _domains(db)


@router.post("/topics", response_model=list[DomainAdmin], status_code=status.HTTP_201_CREATED)
def create_topic(
    body: TopicCreate,
    request: Request,
    ctx: AdminContext = Depends(can_manage),
    db: Session = Depends(get_db),
) -> list[DomainAdmin]:
    domain = db.get(Domain, body.domain_id)
    if domain is None or domain.archived_at is not None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Choose an active domain.")
    if body.parent_id:
        parent = db.get(Topic, body.parent_id)
        if parent is None or parent.domain_id != domain.id:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_CONTENT,
                "The parent topic must be in the same domain.",
            )
    slug = topic_slug(domain.slug, body.name)
    if db.scalar(select(Topic.id).where(Topic.slug == slug)):
        raise HTTPException(status.HTTP_409_CONFLICT, "A topic with this name already exists.")
    position = (
        db.scalar(select(func.max(Topic.position)).where(Topic.domain_id == domain.id)) or 0
    ) + 1
    topic = Topic(
        domain_id=domain.id,
        parent_id=body.parent_id,
        slug=slug,
        name=body.name,
        description=body.description,
        position=position,
        created_by_admin_id=ctx.admin.id,
    )
    db.add(topic)
    db.flush()
    record_audit(
        db,
        request,
        ctx,
        "taxonomy.topic_created",
        "topic",
        topic.id,
        {"name": body.name, "domain": domain.name},
    )
    db.commit()
    return _domains(db)


@router.patch("/topics/{topic_id}", response_model=list[DomainAdmin])
def update_topic(
    topic_id: uuid.UUID,
    body: TopicUpdate,
    request: Request,
    ctx: AdminContext = Depends(can_manage),
    db: Session = Depends(get_db),
) -> list[DomainAdmin]:
    topic = db.get(Topic, topic_id)
    if topic is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Topic not found.")
    changing_pilot = body.is_pilot is not None and body.is_pilot != topic.is_pilot
    if changing_pilot and Perm.SETTINGS_MANAGE.value not in ctx.permissions:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Changing the pilot topics needs the platform-settings permission.",
        )
    changes: dict[str, object] = {}
    if body.name is not None and body.name != topic.name:
        changes["name"] = {"from": topic.name, "to": body.name}
        topic.name = body.name
    if body.description is not None and body.description != topic.description:
        changes["description"] = "changed"
        topic.description = body.description
    if body.archived is not None and body.archived != (topic.archived_at is not None):
        changes["archived"] = body.archived
        topic.archived_at = utcnow() if body.archived else None
    if body.is_pilot is not None and body.is_pilot != topic.is_pilot:
        changes["is_pilot"] = {"from": topic.is_pilot, "to": body.is_pilot}
        topic.is_pilot = body.is_pilot
    if changes:
        record_audit(db, request, ctx, "taxonomy.topic_updated", "topic", topic.id, changes)
        db.commit()
    return _domains(db)
