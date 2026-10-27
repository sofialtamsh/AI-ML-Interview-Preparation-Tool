from collections.abc import Callable
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

import httpx2 as httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from app.ai.openrouter import AiProviderError, OpenRouterClient, get_ai_client
from app.api.admin import ai_usage as ai_usage_api
from app.core.config import get_settings
from app.main import app
from app.models import AiUsageEvent, AuditLog
from tests.helpers import create_admin, login_admin

API_KEY = "sk-or-v1-test-secret"
Handler = Callable[[httpx.Request], httpx.Response]


def openrouter(handler: Handler) -> OpenRouterClient:
    return OpenRouterClient(
        API_KEY, "https://openrouter.test/api/v1", transport=httpx.MockTransport(handler)
    )


def completion(**usage: Any) -> dict[str, Any]:
    return {
        "id": "gen-123",
        "model": "openai/gpt-test",
        "choices": [{"message": {"role": "assistant", "content": "Hello"}}],
        "usage": {"prompt_tokens": 12, "completion_tokens": 3, **usage},
    }


# --- Recording spend --------------------------------------------------------------------------


def test_chat_records_its_cost_in_the_ledger(db: Session) -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json=completion(cost=0.00042))

    admin = create_admin()
    result = openrouter(handler).chat(
        feature="content_generation",
        model="openai/gpt-test",
        messages=[{"role": "user", "content": "Hi"}],
        admin_id=admin.id,
    )

    assert result.text == "Hello"
    assert result.cost_usd == Decimal("0.00042")
    assert seen[0].url.path == "/api/v1/chat/completions"
    assert seen[0].headers["Authorization"] == f"Bearer {API_KEY}"

    event = db.scalars(select(AiUsageEvent)).one()
    assert event.provider == "openrouter"
    assert event.feature == "content_generation"
    assert event.model == "openai/gpt-test"
    assert event.generation_id == "gen-123"
    assert (event.input_tokens, event.output_tokens) == (12, 3)
    assert event.cost_usd == Decimal("0.00042")
    assert event.triggered_by_admin_id == admin.id


def test_cost_is_looked_up_when_the_response_omits_it(db: Session) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/generation"):
            assert request.url.params["id"] == "gen-123"
            return httpx.Response(200, json={"data": {"total_cost": 0.0031}})
        return httpx.Response(200, json=completion())

    openrouter(handler).chat(feature="tts", model="m", messages=[])
    assert db.scalars(select(AiUsageEvent.cost_usd)).one() == Decimal("0.0031")


def test_spend_is_recorded_even_when_the_response_is_unusable(db: Session) -> None:
    body = completion(cost=0.01)
    body["choices"] = []
    client = openrouter(lambda _: httpx.Response(200, json=body))
    with pytest.raises(AiProviderError):
        client.chat(feature="content_generation", model="m", messages=[])
    assert db.scalars(select(AiUsageEvent.cost_usd)).one() == Decimal("0.01")


@pytest.mark.parametrize(
    ("handler", "expected"),
    [
        (
            lambda _: httpx.Response(401, json={"error": {"code": 401, "message": "No auth"}}),
            "OpenRouter returned HTTP 401: No auth",
        ),
        (lambda _: httpx.Response(502, text="Bad gateway"), "OpenRouter returned HTTP 502."),
        (
            lambda request: (_ for _ in ()).throw(httpx.ConnectError("down", request=request)),
            "Could not reach OpenRouter (ConnectError).",
        ),
    ],
)
def test_provider_failures_are_reported_without_the_key(
    db: Session, handler: Handler, expected: str
) -> None:
    with pytest.raises(AiProviderError) as excinfo:
        openrouter(handler).chat(feature="x", model="m", messages=[])
    assert str(excinfo.value) == expected
    assert API_KEY not in str(excinfo.value)
    assert db.scalars(select(AiUsageEvent)).all() == []


# --- Permanent records ------------------------------------------------------------------------


@pytest.mark.parametrize("table", ["audit_logs", "login_events", "ai_usage_events"])
def test_activity_logs_cannot_be_changed_or_deleted(
    client: TestClient, db: Session, table: str
) -> None:
    client.post("/api/student/auth/login", json={"email": "x@example.com", "password": "nope"})
    db.add(AuditLog(action="test.action", entity_type="test"))
    db.add(AiUsageEvent(provider="openrouter", feature="f", model="m", cost_usd=Decimal(1)))
    db.commit()

    for statement in (f"UPDATE {table} SET id = id", f"DELETE FROM {table}"):  # noqa: S608
        with pytest.raises(DBAPIError, match="append-only"):
            db.execute(text(statement))
        db.rollback()
    assert db.scalar(text(f"SELECT count(*) FROM {table}")) == 1  # noqa: S608


# --- Weekly report ----------------------------------------------------------------------------


@pytest.fixture
def report_clock(monkeypatch: pytest.MonkeyPatch) -> Callable[[datetime], None]:
    settings = get_settings()
    monkeypatch.setattr(settings, "usage_tracking_start", date(2026, 10, 27))  # a Tuesday
    monkeypatch.setattr(settings, "usage_timezone", "Asia/Kolkata")

    def set_now(now: datetime) -> None:
        monkeypatch.setattr(ai_usage_api, "utcnow", lambda: now)

    return set_now


def spend(db: Session, at: datetime, cost: str, feature: str = "f", model: str = "m") -> None:
    db.add(
        AiUsageEvent(
            occurred_at=at,
            provider="openrouter",
            feature=feature,
            model=model,
            input_tokens=100,
            output_tokens=10,
            cost_usd=Decimal(cost),
        )
    )
    db.commit()


def utc(*parts: int) -> datetime:
    return datetime(*parts, tzinfo=UTC)  # type: ignore[misc]


def test_weekly_report_buckets_spend_into_local_weeks(
    client: TestClient, db: Session, report_clock: Callable[[datetime], None]
) -> None:
    report_clock(utc(2026, 11, 12, 10))  # Thursday of the third tracked week
    spend(db, utc(2026, 10, 26, 18, 20), "9")  # 23:50 IST on 26 Oct: before tracking started
    spend(db, utc(2026, 10, 26, 18, 40), "1.5")  # 00:10 IST on Tue 27 Oct: first week
    spend(db, utc(2026, 11, 2, 18, 29), "0.25")  # 23:59 IST on Mon 2 Nov: still the first week
    spend(db, utc(2026, 11, 2, 18, 31), "2")  # 00:01 IST on Tue 3 Nov: second week
    spend(db, utc(2026, 11, 11, 9), "0.1", feature="exploration_agent", model="m1")
    spend(db, utc(2026, 11, 11, 9), "0.3", feature="content_generation", model="m2")
    spend(db, utc(2026, 11, 12, 9), "0.05", feature="content_generation", model="m1")

    create_admin()
    login_admin(client)
    report = client.get("/api/admin/ai-usage").json()

    assert report["tracking_start"] == "2026-10-27"
    assert report["timezone"] == "Asia/Kolkata"
    assert [(w["start"], w["end"], w["calls"]) for w in report["weeks"]] == [
        ("2026-11-10", "2026-11-16", 3),
        ("2026-11-03", "2026-11-09", 1),
        ("2026-10-27", "2026-11-02", 2),
    ]
    assert [Decimal(w["cost_usd"]) for w in report["weeks"]] == [
        Decimal("0.45"),
        Decimal("2"),
        Decimal("1.75"),
    ]
    assert report["weeks"][0]["input_tokens"] == 300
    assert report["all_time"]["calls"] == 6
    assert Decimal(report["all_time"]["cost_usd"]) == Decimal("4.2")

    selected = report["selected"]
    assert (selected["start"], selected["end"]) == ("2026-11-10", "2026-11-16")
    assert [(s["key"], s["calls"], Decimal(s["cost_usd"])) for s in selected["by_feature"]] == [
        ("content_generation", 2, Decimal("0.35")),
        ("exploration_agent", 1, Decimal("0.1")),
    ]
    assert [(s["key"], Decimal(s["cost_usd"])) for s in selected["by_model"]] == [
        ("m2", Decimal("0.3")),
        ("m1", Decimal("0.15")),
    ]

    earlier = client.get("/api/admin/ai-usage", params={"week": "2026-10-27"}).json()
    assert earlier["selected"]["start"] == "2026-10-27"
    assert [s["calls"] for s in earlier["selected"]["by_feature"]] == [2]


def test_weeks_without_spend_are_still_listed(
    client: TestClient, report_clock: Callable[[datetime], None]
) -> None:
    report_clock(utc(2026, 10, 27, 6))
    create_admin()
    login_admin(client)
    report = client.get("/api/admin/ai-usage").json()
    assert [(w["start"], w["calls"], Decimal(w["cost_usd"])) for w in report["weeks"]] == [
        ("2026-10-27", 0, Decimal(0))
    ]
    assert report["selected"] == {
        "start": "2026-10-27",
        "end": "2026-11-02",
        "by_feature": [],
        "by_model": [],
    }


@pytest.mark.parametrize("week", ["2026-11-04", "2026-11-17", "2026-10-20"])
def test_only_tracked_weeks_can_be_selected(
    client: TestClient, report_clock: Callable[[datetime], None], week: str
) -> None:
    report_clock(utc(2026, 11, 12, 10))
    create_admin()
    login_admin(client)
    assert client.get("/api/admin/ai-usage", params={"week": week}).status_code == 422


def test_report_is_empty_before_tracking_starts(
    client: TestClient, report_clock: Callable[[datetime], None]
) -> None:
    report_clock(utc(2026, 10, 26, 12))
    create_admin()
    login_admin(client)
    report = client.get("/api/admin/ai-usage").json()
    assert report["weeks"] == []
    assert report["selected"] is None


def test_ai_usage_needs_its_permission(client: TestClient) -> None:
    create_admin(roles=("analyst", "content_manager", "student_success"))
    login_admin(client)
    assert client.get("/api/admin/ai-usage").status_code == 403
    assert client.get("/api/admin/ai-usage/provider").status_code == 403


# --- Provider status --------------------------------------------------------------------------


def use_provider(handler: Handler) -> None:
    def dependency():
        client = openrouter(handler)
        yield client
        client.close()

    app.dependency_overrides[get_ai_client] = dependency


def key_response(**overrides: Any) -> dict[str, Any]:
    data = {
        "label": "sk-or-v1-abc...xyz",
        "limit": None,
        "limit_remaining": None,
        "limit_reset": None,
        "usage": 3.21,
        "usage_daily": 0.1,
        "usage_weekly": 1.0,
        "usage_monthly": 3.21,
        "is_free_tier": False,
        "budgets": [],
        "effective_budget": None,
        **overrides,
    }
    return {"data": data}


def test_provider_status_without_a_key(client: TestClient) -> None:
    create_admin()
    login_admin(client)
    status = client.get("/api/admin/ai-usage/provider").json()
    assert status["configured"] is False
    assert status["ok"] is False


def test_provider_status_reports_key_spend_and_cap(client: TestClient) -> None:
    budget = {
        "scope": "api_key",
        "guardrail_id": None,
        "budget_id": "b1",
        "limit_usd": 20,
        "spend_usd": 5.5,
        "remaining_usd": 14.5,
        "reset_interval": "weekly",
        "resets_at": "2026-11-02T00:00:00Z",
        "include_byok": False,
    }
    use_provider(lambda _: httpx.Response(200, json=key_response(effective_budget=budget)))
    create_admin()
    login_admin(client)

    response = client.get("/api/admin/ai-usage/provider")
    status = response.json()
    assert status["configured"] is True
    assert status["ok"] is True
    assert Decimal(status["key_usage_usd"]) == Decimal("3.21")
    assert Decimal(status["cap"]["limit_usd"]) == 20
    assert Decimal(status["cap"]["remaining_usd"]) == Decimal("14.5")
    assert status["cap"]["reset_interval"] == "weekly"
    assert API_KEY not in response.text
    assert "label" not in response.text


def test_provider_status_falls_back_to_the_key_limit(client: TestClient) -> None:
    use_provider(
        lambda _: httpx.Response(
            200, json=key_response(limit=50, limit_remaining=46.79, limit_reset="monthly")
        )
    )
    create_admin()
    login_admin(client)
    cap = client.get("/api/admin/ai-usage/provider").json()["cap"]
    assert (Decimal(cap["limit_usd"]), cap["reset_interval"]) == (50, "monthly")


def test_provider_status_reports_a_rejected_key(client: TestClient) -> None:
    use_provider(
        lambda _: httpx.Response(401, json={"error": {"code": 401, "message": "User not found."}})
    )
    create_admin()
    login_admin(client)
    status = client.get("/api/admin/ai-usage/provider").json()
    assert status["configured"] is True
    assert status["ok"] is False
    assert status["error"] == "OpenRouter returned HTTP 401: User not found."
