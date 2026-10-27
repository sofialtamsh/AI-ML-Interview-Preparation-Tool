"""OpenRouter: the single gateway the platform uses to call AI models.

Every billed call is written to `ai_usage_events` in its own transaction, so spend is recorded even
when the job that made the call fails afterwards. Errors never include the API key.
"""

import logging
import uuid
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any

import httpx2 as httpx
from pydantic import BaseModel, ConfigDict, ValidationError

from app.core.config import get_settings
from app.core.db import SessionLocal
from app.models import AiUsageEvent

PROVIDER = "openrouter"

log = logging.getLogger(__name__)


class AiProviderError(RuntimeError):
    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


@dataclass(frozen=True)
class ChatResult:
    text: str
    model: str
    generation_id: str | None
    cost_usd: Decimal
    input_tokens: int | None
    output_tokens: int | None


class KeyBudget(BaseModel):
    model_config = ConfigDict(extra="ignore")

    limit_usd: Decimal
    spend_usd: Decimal
    remaining_usd: Decimal
    reset_interval: str | None = None
    resets_at: datetime | None = None


class KeyInfo(BaseModel):
    """The part of OpenRouter's `GET /key` response the admin console uses."""

    model_config = ConfigDict(extra="ignore")

    usage: Decimal
    limit: Decimal | None = None
    limit_remaining: Decimal | None = None
    limit_reset: str | None = None
    is_free_tier: bool = False
    effective_budget: KeyBudget | None = None


def record_usage(
    *,
    feature: str,
    model: str,
    cost_usd: Decimal,
    generation_id: str | None = None,
    input_tokens: int | None = None,
    output_tokens: int | None = None,
    admin_id: uuid.UUID | None = None,
) -> None:
    """Writes one ledger row in its own transaction: money spent stays recorded."""
    with SessionLocal() as db:
        db.add(
            AiUsageEvent(
                provider=PROVIDER,
                feature=feature,
                model=model,
                generation_id=generation_id,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cost_usd=cost_usd,
                triggered_by_admin_id=admin_id,
            )
        )
        db.commit()


def _error_message(response: httpx.Response) -> str:
    try:
        detail = response.json()["error"]["message"]
    except (ValueError, KeyError, TypeError):
        detail = None
    message = f"OpenRouter returned HTTP {response.status_code}"
    return f"{message}: {detail}"[:300] if detail else f"{message}."


class OpenRouterClient:
    def __init__(
        self,
        api_key: str,
        base_url: str,
        *,
        transport: httpx.BaseTransport | None = None,
        timeout: float = 120.0,
    ) -> None:
        self._http = httpx.Client(
            base_url=base_url,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=timeout,
            transport=transport,
        )

    def close(self) -> None:
        self._http.close()

    def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        try:
            response = self._http.request(method, path, **kwargs)
        except httpx.HTTPError as exc:
            raise AiProviderError(f"Could not reach OpenRouter ({type(exc).__name__}).") from exc
        if response.status_code >= 400:
            raise AiProviderError(_error_message(response), response.status_code)
        try:
            return response.json()
        except ValueError as exc:
            raise AiProviderError("OpenRouter returned a response that is not JSON.") from exc

    def chat(
        self,
        *,
        feature: str,
        model: str,
        messages: list[dict[str, Any]],
        admin_id: uuid.UUID | None = None,
        **options: Any,
    ) -> ChatResult:
        """One chat completion. `feature` names what the platform was doing, for spend reports."""
        body = self._request(
            "POST", "/chat/completions", json={"model": model, "messages": messages, **options}
        )
        usage = body.get("usage") or {}
        generation_id = body.get("id")
        cost = usage.get("cost")
        if cost is None and generation_id:
            cost = self._generation_cost(generation_id)
        if cost is None:
            log.warning("OpenRouter reported no cost for generation %s", generation_id)

        result_model = body.get("model") or model
        record_usage(
            feature=feature,
            model=result_model,
            cost_usd=Decimal(str(cost or 0)),
            generation_id=generation_id,
            input_tokens=usage.get("prompt_tokens"),
            output_tokens=usage.get("completion_tokens"),
            admin_id=admin_id,
        )
        try:
            text = body["choices"][0]["message"].get("content") or ""
        except (KeyError, IndexError, TypeError) as exc:
            raise AiProviderError("OpenRouter returned a completion without a message.") from exc
        return ChatResult(
            text=text,
            model=result_model,
            generation_id=generation_id,
            cost_usd=Decimal(str(cost or 0)),
            input_tokens=usage.get("prompt_tokens"),
            output_tokens=usage.get("completion_tokens"),
        )

    def _generation_cost(self, generation_id: str) -> Any:
        try:
            return self._request("GET", "/generation", params={"id": generation_id})["data"].get(
                "total_cost"
            )
        except (AiProviderError, KeyError, TypeError, AttributeError):
            return None

    def key_info(self) -> KeyInfo:
        """Spend and limits of the configured key, as OpenRouter reports them. Costs nothing."""
        try:
            return KeyInfo.model_validate(self._request("GET", "/key")["data"])
        except (KeyError, TypeError, ValidationError) as exc:
            raise AiProviderError("OpenRouter returned an unexpected key response.") from exc


def get_ai_client() -> Iterator[OpenRouterClient | None]:
    """FastAPI dependency: the configured client, or None when no API key is set."""
    settings = get_settings()
    if settings.openrouter_api_key is None:
        yield None
        return
    client = OpenRouterClient(
        settings.openrouter_api_key.get_secret_value(), settings.openrouter_base_url
    )
    try:
        yield client
    finally:
        client.close()
