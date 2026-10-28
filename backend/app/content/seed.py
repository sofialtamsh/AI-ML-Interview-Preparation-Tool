"""Import the starter content for the pilot topics as drafts."""

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.content.service import ContentError, create_version, get_item, validate_body
from app.content.starter import STARTER_MODEL, STARTER_NOTE, TOPICS
from app.models import Component, ContentVersion, Topic, VersionOrigin

PILOT_TOPICS = [module.TOPIC for module in TOPICS]


def starter_fixture() -> dict[str, dict[str, Any]]:
    """Every starter component in canonical form, exactly as the API serves it. The frontend's
    render tests use this (src/test/fixtures/starter-content.json)."""
    return {
        module.TOPIC: {
            key: validate_body(Component(key), body) for key, body in module.CONTENT.items()
        }
        for module in TOPICS
    }


def seed_starter_content(db: Session, *, refresh: bool = False) -> dict[str, int]:
    """Mark the pilot topics and add a starter draft for every component that has no versions
    yet. Never touches components that already have content, so it is safe to re-run.

    With `refresh`, a component whose newest starter version differs from the current starter
    content gets a new starter draft. Earlier versions, and anything published, stay as they are;
    the new draft goes through review like any other."""
    created = present = refreshed = 0
    for module in TOPICS:
        topic = db.scalar(select(Topic).where(Topic.slug == module.TOPIC))
        if topic is None:
            raise ContentError(
                f'Topic "{module.TOPIC}" is missing. Run `python -m app.cli seed-taxonomy` first.'
            )
        topic.is_pilot = True
        for key, body in module.CONTENT.items():
            item = get_item(db, topic, Component(key))
            if db.scalar(select(func.count()).where(ContentVersion.item_id == item.id)):
                present += 1
                if refresh:
                    last_starter = db.scalar(
                        select(ContentVersion)
                        .where(
                            ContentVersion.item_id == item.id,
                            ContentVersion.origin == VersionOrigin.STARTER,
                        )
                        .order_by(ContentVersion.number.desc())
                        .limit(1)
                    )
                    if last_starter and last_starter.body != validate_body(item.component, body):
                        create_version(
                            db,
                            item,
                            body,
                            origin=VersionOrigin.STARTER,
                            note="Updated starter content",
                            model=STARTER_MODEL,
                            based_on=last_starter,
                        )
                        refreshed += 1
                continue
            create_version(
                db,
                item,
                body,
                origin=VersionOrigin.STARTER,
                note=STARTER_NOTE,
                model=STARTER_MODEL,
            )
            created += 1
    db.commit()
    return {
        "pilot_topics": len(TOPICS),
        "drafts_created": created,
        "already_present": present,
        "refreshed": refreshed,
    }
