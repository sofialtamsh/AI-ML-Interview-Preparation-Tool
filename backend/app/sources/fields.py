"""Shared validation and form descriptions for source settings.

Each connector and sign-in method validates its settings with a strict Pydantic model. The console
renders the matching form from `FieldSpec`s, whose defaults, required flags and bounds are read
from the model, so the form and the validation cannot drift apart.
"""

import re
from typing import Annotated, Any, Literal

import httpx2 as httpx
from annotated_types import Ge, Gt, Le, Lt
from pydantic import AfterValidator, BaseModel, ConfigDict, StringConstraints

from app.sources.html import validate_selector


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


def _web_url(value: str) -> str:
    try:
        url = httpx.URL(value)
    except Exception:
        raise ValueError("Enter a full URL, e.g. https://example.com/interviews") from None
    if url.scheme not in ("http", "https") or not url.host:
        raise ValueError("Enter a full http:// or https:// URL")
    if url.userinfo:
        raise ValueError("Don't put a username or password in the URL; use credentials instead")
    return str(url)


WebUrl = Annotated[str, StringConstraints(max_length=2048), AfterValidator(_web_url)]
CssSelector = Annotated[str, StringConstraints(max_length=500), AfterValidator(validate_selector)]
ShortValue = Annotated[str, StringConstraints(max_length=200)]
# A JSON path such as "data.items" or "results.0.id".
DotPath = Annotated[str, StringConstraints(max_length=200, pattern=r"^[\w\-]*(\.[\w\-]+)*$")]
ParamName = Annotated[str, StringConstraints(max_length=100, pattern=r"^[\w\-\.\[\]]+$")]

_FORBIDDEN_HEADERS = {
    "host",
    "content-length",
    "transfer-encoding",
    "connection",
    "upgrade",
    "te",
    "trailer",
    "keep-alive",
}


def _header_name(value: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9-]{1,64}", value):
        raise ValueError("Use letters, digits and hyphens only, e.g. X-API-Key")
    if value.lower() in _FORBIDDEN_HEADERS or value.lower().startswith("proxy-"):
        raise ValueError(f"{value} can't be used for credentials")
    return value


HeaderName = Annotated[str, AfterValidator(_header_name)]

FieldKind = Literal["text", "password", "url", "number", "textarea", "lines", "select", "checkbox"]


class FieldOption(BaseModel):
    value: str
    label: str


class FieldSpec(BaseModel):
    key: str
    label: str
    kind: FieldKind = "text"
    help: str = ""
    placeholder: str = ""
    options: list[FieldOption] | None = None
    required: bool = False
    default: Any = None
    min: float | None = None
    max: float | None = None
    # Only shown when another field has one of these values, e.g. {"pagination": ["cursor"]}.
    # "*" means any non-empty value; checkboxes compare as "true"/"false".
    visible_when: dict[str, list[str]] | None = None


def ui_fields(model: type[BaseModel], specs: list[FieldSpec]) -> list[FieldSpec]:
    """Complete the specs from the model. Fails at import time if they don't match the model."""
    if [s.key for s in specs] != list(model.model_fields):
        raise RuntimeError(f"{model.__name__}: form fields must match the model fields in order")
    completed = []
    for spec in specs:
        info = model.model_fields[spec.key]
        bounds: dict[str, float | None] = {"min": None, "max": None}
        for rule in info.metadata:
            if isinstance(rule, Ge | Gt):
                bounds["min"] = float(rule.ge if isinstance(rule, Ge) else rule.gt)
            if isinstance(rule, Le | Lt):
                bounds["max"] = float(rule.le if isinstance(rule, Le) else rule.lt)
        required = info.is_required()
        completed.append(
            spec.model_copy(
                update={
                    "required": required,
                    "default": None if required else info.get_default(call_default_factory=True),
                    **bounds,
                }
            )
        )
    return completed
