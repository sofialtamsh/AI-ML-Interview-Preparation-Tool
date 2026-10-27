"""AI spend, reported in weeks that start on the tracking start date's weekday (local timezone)."""

from collections import defaultdict
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import Date, cast, func, select
from sqlalchemy.orm import InstrumentedAttribute, Session

from app.ai.openrouter import AiProviderError, OpenRouterClient, get_ai_client
from app.auth.deps import require_permission
from app.auth.permissions import Perm
from app.core.config import get_settings
from app.core.db import get_db
from app.core.security import utcnow
from app.models import AiUsageEvent
from app.schemas.admin import (
    AiProviderStatus,
    AiUsageReport,
    SpendCap,
    UsageSlice,
    UsageTotals,
    UsageWeek,
    UsageWeekDetail,
)

router = APIRouter(
    prefix="/ai-usage",
    tags=["admin-ai-usage"],
    dependencies=[Depends(require_permission(Perm.AI_USAGE_VIEW))],
)

WEEK = timedelta(days=7)


def _midnight(day: date, tz: ZoneInfo) -> datetime:
    return datetime.combine(day, time.min, tz)


def _breakdown(
    db: Session, column: InstrumentedAttribute[str], start: datetime, end: datetime
) -> list[UsageSlice]:
    cost = func.sum(AiUsageEvent.cost_usd)
    rows = db.execute(
        select(column, func.count(), cost)
        .where(AiUsageEvent.occurred_at >= start, AiUsageEvent.occurred_at < end)
        .group_by(column)
        .order_by(cost.desc(), column)
    )
    return [UsageSlice(key=key, calls=calls, cost_usd=total) for key, calls, total in rows]


@router.get("", response_model=AiUsageReport)
def usage_report(
    week: date | None = Query(default=None, description="Start date of the week to break down"),
    db: Session = Depends(get_db),
) -> AiUsageReport:
    settings = get_settings()
    tz, first = ZoneInfo(settings.usage_timezone), settings.usage_tracking_start
    today = utcnow().astimezone(tz).date()
    if today < first:
        return AiUsageReport(
            tracking_start=first,
            timezone=settings.usage_timezone,
            weeks=[],
            selected=None,
            all_time=UsageTotals(),
        )

    current = first + WEEK * ((today - first).days // 7)
    selected = week or current
    if not first <= selected <= current or (selected - first).days % 7:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Choose a tracked week.")

    # Daily sums in local time, folded into weeks here (a few hundred rows a year at most).
    local_day = cast(func.timezone(settings.usage_timezone, AiUsageEvent.occurred_at), Date)
    daily = db.execute(
        select(
            local_day,
            func.count(),
            func.coalesce(func.sum(AiUsageEvent.input_tokens), 0),
            func.coalesce(func.sum(AiUsageEvent.output_tokens), 0),
            func.sum(AiUsageEvent.cost_usd),
        )
        .where(AiUsageEvent.occurred_at >= _midnight(first, tz))
        .group_by(local_day)
    ).all()
    by_week: dict[date, UsageTotals] = defaultdict(UsageTotals)
    for day, calls, input_tokens, output_tokens, cost in daily:
        totals = by_week[first + WEEK * ((day - first).days // 7)]
        totals.calls += calls
        totals.input_tokens += input_tokens
        totals.output_tokens += output_tokens
        totals.cost_usd += cost

    starts = [current - WEEK * i for i in range((current - first).days // 7 + 1)]
    weeks = [
        UsageWeek(start=s, end=s + timedelta(days=6), **by_week[s].model_dump()) for s in starts
    ]
    lo, hi = _midnight(selected, tz), _midnight(selected + WEEK, tz)
    return AiUsageReport(
        tracking_start=first,
        timezone=settings.usage_timezone,
        weeks=weeks,
        selected=UsageWeekDetail(
            start=selected,
            end=selected + timedelta(days=6),
            by_feature=_breakdown(db, AiUsageEvent.feature, lo, hi),
            by_model=_breakdown(db, AiUsageEvent.model, lo, hi),
        ),
        all_time=UsageTotals(
            calls=sum(w.calls for w in weeks),
            input_tokens=sum(w.input_tokens for w in weeks),
            output_tokens=sum(w.output_tokens for w in weeks),
            cost_usd=sum((w.cost_usd for w in weeks), Decimal(0)),
        ),
    )


@router.get("/provider", response_model=AiProviderStatus)
def provider_status(client: OpenRouterClient | None = Depends(get_ai_client)) -> AiProviderStatus:
    """Live spend and limits of the platform's OpenRouter key (the key itself is never sent)."""
    if client is None:
        return AiProviderStatus(configured=False)
    try:
        info = client.key_info()
    except AiProviderError as exc:
        return AiProviderStatus(configured=True, error=str(exc))

    if budget := info.effective_budget:
        cap = SpendCap(
            limit_usd=budget.limit_usd,
            remaining_usd=budget.remaining_usd,
            reset_interval=budget.reset_interval,
            resets_at=budget.resets_at,
        )
    elif info.limit is not None:
        cap = SpendCap(
            limit_usd=info.limit,
            remaining_usd=info.limit_remaining,
            reset_interval=info.limit_reset,
        )
    else:
        cap = None
    return AiProviderStatus(
        configured=True,
        ok=True,
        key_usage_usd=info.usage,
        cap=cap,
        is_free_tier=info.is_free_tier,
    )
