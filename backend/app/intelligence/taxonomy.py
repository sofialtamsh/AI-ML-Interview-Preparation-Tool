"""The AI/ML taxonomy: the starting set of domains and topics, and lookups for the agents."""

import re
import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Domain, Topic

# The starting taxonomy, exactly as listed in the requirements (docs/MASTER_PROMPT.md §9).
# Admins extend it later; seeding only happens on an empty taxonomy.
DEFAULT_TAXONOMY: list[tuple[str, list[str]]] = [
    (
        "Mathematics and Statistics",
        ["Linear Algebra", "Probability", "Statistics", "Calculus", "Optimization"],
    ),
    (
        "Machine Learning",
        [
            "Supervised Learning",
            "Unsupervised Learning",
            "Regression",
            "Classification",
            "Clustering",
            "Dimensionality Reduction",
            "Ensemble Learning",
            "Model Evaluation",
        ],
    ),
    (
        "Deep Learning",
        [
            "Neural Network Fundamentals",
            "Activation Functions",
            "Backpropagation",
            "Optimizers",
            "CNNs",
            "RNNs",
            "Transformers",
        ],
    ),
    (
        "Computer Vision",
        [
            "Image Processing",
            "Object Detection",
            "Image Classification",
            "Image Segmentation",
            "Transfer Learning",
        ],
    ),
    (
        "Natural Language Processing",
        [
            "Text Preprocessing",
            "TF-IDF",
            "Word Embeddings",
            "Sequence Models",
            "Attention",
            "Transformers",
        ],
    ),
    (
        "Generative AI and LLMs",
        [
            "LLM Fundamentals",
            "Tokenization",
            "Embeddings",
            "Fine-tuning",
            "LoRA",
            "RAG",
            "Vector Databases",
            "LLM Evaluation",
        ],
    ),
    (
        "Agentic AI",
        [
            "AI Agents",
            "Tool Calling",
            "Planning",
            "Multi-Agent Systems",
            "LangGraph",
            "Agent Evaluation",
        ],
    ),
    (
        "MLOps",
        [
            "Model Deployment",
            "Model Monitoring",
            "Experiment Tracking",
            "CI/CD",
            "Model Serving",
        ],
    ),
]


def slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:80] or "item"


def topic_slug(domain_slug: str, name: str) -> str:
    return f"{domain_slug}/{slugify(name)}"


def seed_default_taxonomy(db: Session) -> bool:
    """Create the starting taxonomy if there is none yet. Returns whether it seeded."""
    if db.scalar(select(Domain.id).limit(1)) is not None:
        return False
    for position, (domain_name, topics) in enumerate(DEFAULT_TAXONOMY):
        domain = Domain(slug=slugify(domain_name), name=domain_name, position=position)
        db.add(domain)
        db.flush()
        for index, name in enumerate(topics):
            db.add(
                Topic(
                    domain_id=domain.id,
                    slug=topic_slug(domain.slug, name),
                    name=name,
                    position=index,
                )
            )
    db.commit()
    return True


@dataclass(frozen=True)
class TopicCatalog:
    """Active topics, as the agents see them: slugs to classify into, ids to store."""

    ids: dict[str, uuid.UUID]
    lines: list[str]  # "machine-learning/regression: Regression (Machine Learning)"

    def resolve(self, slug: str | None) -> uuid.UUID | None:
        return self.ids.get(slug.strip().lower()) if slug else None

    @property
    def prompt(self) -> str:
        return "\n".join(self.lines)


def topic_catalog(db: Session) -> TopicCatalog:
    topics = db.scalars(
        select(Topic)
        .join(Domain, Topic.domain_id == Domain.id)
        .where(Topic.archived_at.is_(None), Domain.archived_at.is_(None))
        .order_by(Domain.position, Topic.position)
    ).all()
    return TopicCatalog(
        ids={t.slug: t.id for t in topics},
        lines=[f"{t.slug}: {t.name} ({t.domain.name})" for t in topics],
    )


def domain_ids(db: Session) -> dict[str, uuid.UUID]:
    return {d.slug: d.id for d in db.scalars(select(Domain).where(Domain.archived_at.is_(None)))}
