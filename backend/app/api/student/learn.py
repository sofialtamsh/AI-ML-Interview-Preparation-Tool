"""The student learning experience: only published content, shaped by student-facing schemas.

No endpoint here exposes drafts, review data, models, sources, companies or other students.
A topic appears once its lesson is published."""

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.deps import get_student_context
from app.content.schemas import COMPONENT_ORDER
from app.core.db import get_db
from app.models import Component, ContentItem, ContentVersion, Domain, MediaAsset, Topic
from app.schemas.learn import (
    LearnDomain,
    LearnTopic,
    LearnTopicCard,
    StudentScene,
    StudentVideo,
    student_interview,
)

router = APIRouter(
    prefix="/learn", tags=["student-learn"], dependencies=[Depends(get_student_context)]
)


def _published(
    db: Session, topic_ids: list[uuid.UUID]
) -> dict[uuid.UUID, dict[Component, ContentVersion]]:
    rows = db.execute(
        select(ContentItem.topic_id, ContentItem.component, ContentVersion)
        .join(ContentVersion, ContentItem.published_version_id == ContentVersion.id)
        .where(ContentItem.topic_id.in_(topic_ids))
    ).unique()
    published: dict[uuid.UUID, dict[Component, ContentVersion]] = {}
    for topic_id, component, version in rows:
        published.setdefault(topic_id, {})[component] = version
    return published


def _visible_topics(db: Session) -> list[Topic]:
    return list(
        db.scalars(
            select(Topic)
            .join(Domain, Topic.domain_id == Domain.id)
            .where(Topic.archived_at.is_(None), Domain.archived_at.is_(None))
            .order_by(Domain.position, Topic.position)
        ).unique()
    )


@router.get("", response_model=list[LearnDomain])
def domains(db: Session = Depends(get_db)) -> list[LearnDomain]:
    topics = _visible_topics(db)
    published = _published(db, [t.id for t in topics])
    grouped: dict[uuid.UUID, LearnDomain] = {}
    for topic in topics:
        parts = published.get(topic.id, {})
        lesson = parts.get(Component.LESSON)
        if lesson is None:
            continue
        domain = grouped.setdefault(
            topic.domain_id, LearnDomain(slug=topic.domain.slug, name=topic.domain.name, topics=[])
        )
        domain.topics.append(
            LearnTopicCard(
                slug=topic.slug,
                name=topic.name,
                tagline=lesson.body["tagline"],
                minutes=lesson.body["minutes"],
                level=lesson.body["level"],
                sections=[c.value for c in COMPONENT_ORDER if c in parts],
            )
        )
    return list(grouped.values())


def _video(db: Session, version: ContentVersion) -> StudentVideo:
    audio = dict(
        db.execute(
            select(MediaAsset.position, MediaAsset.id).where(
                MediaAsset.version_id == version.id, MediaAsset.kind == "narration"
            )
        ).all()
    )
    body = version.body
    return StudentVideo(
        title=body["title"],
        scenes=[
            StudentScene(**scene, audio_id=audio.get(index))
            for index, scene in enumerate(body["scenes"])
        ],
    )


@router.get("/topics/{slug:path}", response_model=LearnTopic)
def topic(slug: str, db: Session = Depends(get_db)) -> LearnTopic:
    found = db.scalar(
        select(Topic)
        .join(Domain, Topic.domain_id == Domain.id)
        .where(Topic.slug == slug, Topic.archived_at.is_(None), Domain.archived_at.is_(None))
    )
    parts = _published(db, [found.id]).get(found.id, {}) if found else {}
    lesson = parts.get(Component.LESSON)
    if found is None or lesson is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Topic not found.")

    def body(component: Component) -> dict[str, Any] | None:
        version = parts.get(component)
        return version.body if version else None

    interview = body(Component.INTERVIEW)
    video = parts.get(Component.VIDEO)
    return LearnTopic(
        slug=found.slug,
        name=found.name,
        domain={"slug": found.domain.slug, "name": found.domain.name},
        tagline=lesson.body["tagline"],
        minutes=lesson.body["minutes"],
        level=lesson.body["level"],
        lesson=lesson.body,
        playground=body(Component.PLAYGROUND),
        video=_video(db, video) if video else None,
        python=body(Component.PYTHON),
        interview=student_interview(interview) if interview else None,
        quiz=body(Component.QUIZ),
        revision=body(Component.REVISION),
    )


@router.get("/media/{media_id}")
def media(media_id: uuid.UUID, db: Session = Depends(get_db)) -> Response:
    """Narration audio, only for the currently published version of a video."""
    asset = db.get(MediaAsset, media_id)
    live = asset and db.scalar(
        select(ContentItem.id).where(ContentItem.published_version_id == asset.version_id)
    )
    if not asset or not live:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Not found.")
    return Response(
        asset.data,
        media_type=asset.content_type,
        headers={"Cache-Control": "private, max-age=86400"},
    )
