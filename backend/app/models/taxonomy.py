import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, Timestamps, UUIDPrimaryKey


class Domain(UUIDPrimaryKey, Timestamps, Base):
    """A top-level AI/ML area, e.g. Machine Learning. Archived, never deleted."""

    __tablename__ = "domains"

    slug: Mapped[str] = mapped_column(String(80), unique=True)
    name: Mapped[str] = mapped_column(String(120))
    description: Mapped[str] = mapped_column(Text, default="")
    position: Mapped[int] = mapped_column(default=0)
    archived_at: Mapped[datetime | None]

    topics: Mapped[list["Topic"]] = relationship(
        back_populates="domain", order_by="Topic.position", lazy="selectin"
    )


class Topic(UUIDPrimaryKey, Timestamps, Base):
    """A topic in a domain; `parent_id` makes it a subtopic. Slugs are global, e.g.
    "machine-learning/regression", because names repeat across domains (Transformers)."""

    __tablename__ = "topics"

    domain_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("domains.id"), index=True)
    parent_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("topics.id"), index=True)
    slug: Mapped[str] = mapped_column(String(200), unique=True)
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default="")
    position: Mapped[int] = mapped_column(default=0)
    # Content generation is limited to pilot topics until an admin approves expansion (Phase 4).
    is_pilot: Mapped[bool] = mapped_column(default=False)
    archived_at: Mapped[datetime | None]
    created_by_admin_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("admin_users.id"))

    domain: Mapped[Domain] = relationship(back_populates="topics", lazy="joined")
