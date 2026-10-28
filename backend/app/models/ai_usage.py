import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import BigInteger, ForeignKey, Identity, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class AiUsageEvent(Base):
    """One billed call to an AI provider. Append-only (enforced by a DB trigger), kept permanently.

    Weekly spend reports are aggregated from these rows, so they never need a separate snapshot.
    """

    __tablename__ = "ai_usage_events"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    occurred_at: Mapped[datetime] = mapped_column(server_default=func.now(), index=True)
    provider: Mapped[str] = mapped_column(String(32))
    # What the platform was doing, e.g. "content_generation" or "exploration_agent".
    feature: Mapped[str] = mapped_column(String(64), index=True)
    model: Mapped[str] = mapped_column(String(200))
    generation_id: Mapped[str | None] = mapped_column(String(128), unique=True)
    input_tokens: Mapped[int | None]
    output_tokens: Mapped[int | None]
    cost_usd: Mapped[Decimal] = mapped_column(Numeric(16, 8))
    triggered_by_admin_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("admin_users.id"), index=True
    )
    # The agent run that made the call, so each run's cost can be reported.
    job_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("jobs.id"), index=True)
