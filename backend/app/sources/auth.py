"""How the platform signs in to a source. Secrets arrive decrypted, in memory only, per run."""

from dataclasses import dataclass

from bs4 import Tag
from pydantic import BaseModel

from app.models import AuthMethod
from app.sources.fields import (
    FieldSpec,
    HeaderName,
    ParamName,
    ShortValue,
    StrictModel,
    WebUrl,
    ui_fields,
)
from app.sources.html import (
    asks_for_one_time_code,
    detect_challenge,
    has_password_field,
    parse_html,
)
from app.sources.http import AccessBlocked, RequestAuth, SafeHttp, SourceError, describe


class NoSettings(StrictModel):
    pass


class ApiKeyHeaderSettings(StrictModel):
    header_name: HeaderName = "X-API-Key"


class ApiKeyQuerySettings(StrictModel):
    param_name: ParamName = "api_key"


class FormLoginSettings(StrictModel):
    login_url: WebUrl
    username_field: ParamName = "username"
    password_field: ParamName = "password"  # noqa: S105 (a form field name)
    success_text: ShortValue = ""


@dataclass(frozen=True)
class AuthSpec:
    method: AuthMethod
    label: str
    description: str
    settings_model: type[StrictModel]
    settings_fields: list[FieldSpec]
    secret_fields: list[FieldSpec]


_USERNAME = FieldSpec(key="username", label="Username or email", kind="text")
_PASSWORD = FieldSpec(key="password", label="Password", kind="password")

AUTH_SPECS: dict[AuthMethod, AuthSpec] = {
    spec.method: spec
    for spec in (
        AuthSpec(
            AuthMethod.NONE,
            "No sign-in",
            "The source is public.",
            NoSettings,
            [],
            [],
        ),
        AuthSpec(
            AuthMethod.HTTP_BASIC,
            "Username & password (HTTP Basic)",
            "The site's own browser pop-up sign-in, or an API that takes a username and password.",
            NoSettings,
            [],
            [_USERNAME, _PASSWORD],
        ),
        AuthSpec(
            AuthMethod.BEARER_TOKEN,
            "Access token (Bearer)",
            'Sent as "Authorization: Bearer <token>".',
            NoSettings,
            [],
            [FieldSpec(key="token", label="Access token", kind="password")],
        ),
        AuthSpec(
            AuthMethod.API_KEY_HEADER,
            "API key in a header",
            "Sent in a request header you name.",
            ApiKeyHeaderSettings,
            ui_fields(
                ApiKeyHeaderSettings,
                [FieldSpec(key="header_name", label="Header name", placeholder="X-API-Key")],
            ),
            [FieldSpec(key="api_key", label="API key", kind="password")],
        ),
        AuthSpec(
            AuthMethod.API_KEY_QUERY,
            "API key in the URL",
            "Added to each request URL as a query parameter.",
            ApiKeyQuerySettings,
            ui_fields(
                ApiKeyQuerySettings,
                [FieldSpec(key="param_name", label="Parameter name", placeholder="api_key")],
            ),
            [FieldSpec(key="api_key", label="API key", kind="password")],
        ),
        AuthSpec(
            AuthMethod.FORM_LOGIN,
            "Website sign-in form",
            "Signs in through the site's login page, like a person would. Sites that ask for a "
            "CAPTCHA or a one-time code can't be signed in to automatically.",
            FormLoginSettings,
            ui_fields(
                FormLoginSettings,
                [
                    FieldSpec(
                        key="login_url",
                        label="Login page URL",
                        kind="url",
                        placeholder="https://example.com/login",
                    ),
                    FieldSpec(
                        key="username_field",
                        label="Username field name",
                        help='The name="…" of the username input on the login form.',
                    ),
                    FieldSpec(
                        key="password_field",
                        label="Password field name",
                        help='The name="…" of the password input on the login form.',
                    ),
                    FieldSpec(
                        key="success_text",
                        label="Text shown only when signed in (optional)",
                        placeholder="Log out",
                        help="Confirms the sign-in worked, e.g. the words on a logout link.",
                    ),
                ],
            ),
            [_USERNAME, _PASSWORD],
        ),
    )
}


def required_secret_fields(method: AuthMethod) -> list[str]:
    return [field.key for field in AUTH_SPECS[method].secret_fields]


def request_auth(
    method: AuthMethod, settings: BaseModel, secrets: dict[str, str], origin: str
) -> RequestAuth | None:
    """Credentials attached to every request for the source's origin (and no other)."""
    match method:
        case AuthMethod.HTTP_BASIC:
            return RequestAuth.basic(origin, secrets["username"], secrets["password"])
        case AuthMethod.BEARER_TOKEN:
            return RequestAuth(origin, headers={"Authorization": f"Bearer {secrets['token']}"})
        case AuthMethod.API_KEY_HEADER if isinstance(settings, ApiKeyHeaderSettings):
            return RequestAuth(origin, headers={settings.header_name: secrets["api_key"]})
        case AuthMethod.API_KEY_QUERY if isinstance(settings, ApiKeyQuerySettings):
            return RequestAuth(origin, params={settings.param_name: secrets["api_key"]})
        case _:
            return None


_IGNORED_INPUT_TYPES = {"submit", "button", "image", "reset", "file"}


def form_login(http: SafeHttp, settings: FormLoginSettings, secrets: dict[str, str]) -> None:
    """Sign in through the site's login form; the session cookie stays in `http`.

    CAPTCHAs and one-time codes are reported, never bypassed.
    """
    page = http.get(settings.login_url)
    if page.status_code >= 400:
        raise SourceError(
            f"The login page returned HTTP {page.status_code} at {describe(page.url)}."
        )
    if challenge := detect_challenge(page, strict=True):
        raise AccessBlocked(
            f"The login page shows {challenge}, so the platform can't sign in automatically. "
            "Export the pages yourself and import them as files instead."
        )
    soup = parse_html(page.text)
    form = next(
        (
            f
            for f in soup.find_all("form")
            if isinstance(f, Tag) and f.select_one(f'input[name="{settings.password_field}"]')
        ),
        None,
    )
    if form is None:
        names = sorted({str(i.get("name")) for i in soup.find_all("input") if i.get("name")})
        found = f" Inputs on the page: {', '.join(names[:12])}." if names else ""
        raise SourceError(
            f'No sign-in form with a "{settings.password_field}" field was found at '
            f"{describe(page.url)}.{found}"
        )

    values: dict[str, str] = {}
    for field in form.find_all(["input", "select", "textarea"]):
        name = field.get("name")
        kind = str(field.get("type", "text")).lower()
        if not name or kind in _IGNORED_INPUT_TYPES:
            continue
        if kind in ("checkbox", "radio") and not field.has_attr("checked"):
            continue
        if field.name == "select":
            option = field.find("option", selected=True) or field.find("option")
            values[str(name)] = (
                str(option.get("value", option.get_text())) if isinstance(option, Tag) else ""
            )
        elif field.name == "textarea":
            values[str(name)] = field.get_text()
        else:
            values[str(name)] = str(field.get("value", ""))
    if settings.username_field not in values:
        raise SourceError(
            f'The sign-in form has no "{settings.username_field}" field. Fields on the form: '
            f"{', '.join(sorted(values)) or 'none'}."
        )
    values[settings.username_field] = secrets["username"]
    values[settings.password_field] = secrets["password"]

    action = page.url.join(str(form.get("action") or ""))
    method = str(form.get("method") or "post").upper()
    if method not in ("GET", "POST"):
        method = "POST"
    result = (
        http.request("POST", action, data=values)
        if method == "POST"
        else http.request("GET", action, params=values)
    )

    if challenge := detect_challenge(result, strict=True):
        raise AccessBlocked(
            f"After signing in, the site showed {challenge}. Automated access isn't possible; "
            "import files instead."
        )
    if result.status_code >= 400:
        raise SourceError(
            f"Sign-in failed (HTTP {result.status_code}). Check the username and password."
        )
    landed = parse_html(result.text)
    if asks_for_one_time_code(landed):
        raise AccessBlocked(
            "The site asked for a one-time code (two-factor sign-in), which the platform never "
            "bypasses. Import files for this source instead."
        )
    if has_password_field(landed):
        raise SourceError(
            "Sign-in failed: the site showed the sign-in form again. Check the username and "
            "password."
        )
    if settings.success_text and settings.success_text.lower() not in result.text.lower():
        raise SourceError(
            f'Sign-in could not be confirmed: "{settings.success_text}" did not appear after '
            "signing in. Check the credentials and the confirmation text."
        )
