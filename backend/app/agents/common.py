"""What both agents share: the AI client, validated structured output, and run budgets."""

import json
import re
import uuid
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ValidationError
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.ai import openrouter
from app.ai.openrouter import AiProviderError, ChatResult, OpenRouterClient
from app.core.errors import UserFacingError
from app.models import AiUsageEvent

# Billing or key problems: every further call would fail the same way, so the run stops.
FATAL_PROVIDER_STATUSES = {401, 402, 403}


class AgentError(UserFacingError):
    pass


def ai_client_or_fail() -> OpenRouterClient:
    client = openrouter.make_ai_client()
    if client is None:
        raise AgentError(
            "The AI provider isn't connected. Set IPP_OPENROUTER_API_KEY on the server and "
            "restart it."
        )
    return client


def is_fatal(error: AiProviderError) -> bool:
    return error.status_code in FATAL_PROVIDER_STATUSES


def run_spend(db: Session, job_id: uuid.UUID) -> Decimal:
    spent = db.scalar(
        select(func.coalesce(func.sum(AiUsageEvent.cost_usd), 0)).where(
            AiUsageEvent.job_id == job_id
        )
    )
    return Decimal(spent or 0)


_ANNOTATIONS = {"title", "default"}
# Not every provider's strict mode accepts these keywords, so they become plain-language hints;
# the Pydantic model still enforces them when the reply is validated.
_LIMITS = {
    "minLength",
    "maxLength",
    "minItems",
    "maxItems",
    "minimum",
    "maximum",
    "exclusiveMinimum",
    "exclusiveMaximum",
    "pattern",
}


def _limit_hint(node: dict[str, Any]) -> str:
    hints = []
    if "maxLength" in node:
        hints.append(f"at most {node['maxLength']} characters")
    if "minItems" in node or "maxItems" in node:
        low, high = node.get("minItems", 0), node.get("maxItems")
        hints.append(f"{low}-{high} items" if high is not None else f"at least {low} items")
    if "minimum" in node or "maximum" in node:
        hints.append(f"between {node.get('minimum', '…')} and {node.get('maximum', '…')}")
    return "; ".join(hints)


def strict_schema(model: type[BaseModel]) -> dict[str, Any]:
    """The model's JSON Schema in the form strict structured-output modes accept: every
    property required (nullable ones allow null), no extra properties, and limits expressed as
    hints. Field names are never touched, even a field called "title"."""

    def tighten(node: Any) -> Any:
        if isinstance(node, list):
            return [tighten(item) for item in node]
        if not isinstance(node, dict):
            return node
        out: dict[str, Any] = {}
        for key, value in node.items():
            if key in _ANNOTATIONS or key in _LIMITS:
                continue
            if key in ("properties", "$defs"):
                out[key] = {name: tighten(schema) for name, schema in value.items()}
            else:
                out[key] = tighten(value)
        if hint := _limit_hint(node):
            out["description"] = f"{out['description']} ({hint})" if "description" in out else hint
        if out.get("type") == "object" and "properties" in out:
            out["required"] = list(out["properties"])
            out["additionalProperties"] = False
        return out

    return tighten(model.model_json_schema())


_FENCE = re.compile(r"^```(?:json)?\s*|\s*```$")


def structured_chat[T: BaseModel](
    client: OpenRouterClient,
    output: type[T],
    *,
    feature: str,
    model: str,
    messages: list[dict[str, Any]],
    job_id: uuid.UUID | None,
    admin_id: uuid.UUID | None,
) -> T:
    """A chat call whose reply must match `output`. One repair attempt if it doesn't."""
    response_format = {
        "type": "json_schema",
        "json_schema": {"name": output.__name__, "strict": True, "schema": strict_schema(output)},
    }
    conversation = list(messages)
    for attempt in range(2):
        result: ChatResult = client.chat(
            feature=feature,
            model=model,
            messages=conversation,
            job_id=job_id,
            admin_id=admin_id,
            response_format=response_format,
            provider={"require_parameters": True},
            temperature=0,
        )
        try:
            return output.model_validate_json(_FENCE.sub("", result.text.strip()))
        except ValidationError as exc:
            if attempt:
                break
            problems = "; ".join(
                f"{'.'.join(str(p) for p in e['loc'])}: {e['msg']}"
                for e in exc.errors(include_input=False)[:5]
            )
            conversation += [
                {"role": "assistant", "content": result.text[:20_000]},
                {
                    "role": "user",
                    "content": "That reply didn't match the required JSON format "
                    f"({problems}). Reply again with only JSON that matches it exactly.",
                },
            ]
    raise AgentError("The model's reply didn't match the required format, even after a retry.")


def compact_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
