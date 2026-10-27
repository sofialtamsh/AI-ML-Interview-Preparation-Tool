"""Reading HTML pages: readable text, links, and signs that a site is blocking automation."""

import re

import httpx2 as httpx
import soupsieve
from bs4 import BeautifulSoup, Tag

from app.sources.http import Fetched

_NOISE_TAGS = ["script", "style", "noscript", "template", "svg", "iframe", "canvas", "head"]
_LAYOUT_TAGS = ["nav", "header", "footer", "aside"]
_SKIPPED_HREFS = ("javascript:", "mailto:", "tel:", "#", "data:")

# Markers that only appear on bot-check interstitials.
_STRONG_CHALLENGE_MARKERS = {
    "/cdn-cgi/challenge-platform": "a Cloudflare bot check",
    "cf-chl-": "a Cloudflare bot check",
    "captcha-delivery.com": "a DataDome bot check",
    "px-captcha": "a PerimeterX bot check",
}
# Markers that also appear on ordinary pages (a comment form with a CAPTCHA, say). They only
# count when the page has almost no other text, i.e. it is a CAPTCHA wall.
_WEAK_CHALLENGE_MARKERS = {
    "g-recaptcha": "a CAPTCHA",
    "recaptcha/api.js": "a CAPTCHA",
    "h-captcha": "a CAPTCHA",
    "hcaptcha.com": "a CAPTCHA",
    "cf-turnstile": "a CAPTCHA",
    "arkoselabs": "a CAPTCHA",
    "funcaptcha": "a CAPTCHA",
}
_CAPTCHA_WALL_MAX_TEXT = 1500
_ONE_TIME_CODE_MARKERS = (
    "one-time-code",
    "otp",
    "totp",
    "2fa",
    "mfa",
    "two_factor",
    "two-factor",
    "twofactor",
    "verification_code",
    "verification-code",
    "auth_code",
    "authcode",
)


def parse_html(markup: str) -> BeautifulSoup:
    return BeautifulSoup(markup, "html.parser")


def validate_selector(selector: str) -> str:
    """A CSS selector, checked so a typo is reported when the source is saved, not mid-fetch."""
    if selector:
        try:
            soupsieve.compile(selector)
        except Exception:  # soupsieve raises several error types for bad selectors
            raise ValueError(f'"{selector}" is not a valid CSS selector') from None
    return selector


def page_title(soup: BeautifulSoup) -> str | None:
    for candidate in (soup.find("h1"), soup.find("title")):
        if isinstance(candidate, Tag):
            text = " ".join(candidate.get_text(" ", strip=True).split())
            if text:
                return text[:500]
    return None


def page_text(soup: BeautifulSoup, selector: str = "") -> str:
    """The readable text of a page: the selected element(s), else <main>/<article>, else the body
    without navigation chrome. The soup is modified."""
    for tag in soup(_NOISE_TAGS):
        tag.decompose()
    if selector:
        nodes = soup.select(selector)
    else:
        main = soup.select_one("main, article, [role=main]")
        if main is not None:
            nodes = [main]
        else:
            body = soup.body or soup
            for tag in body(_LAYOUT_TAGS):
                tag.decompose()
            nodes = [body]
    return tidy_text("\n".join(node.get_text("\n", strip=True) for node in nodes))


def html_to_text(markup: str) -> str:
    return page_text(parse_html(markup))


def tidy_text(text: str) -> str:
    lines = (" ".join(line.split()) for line in text.splitlines())
    return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()


def links(soup: BeautifulSoup, selector: str, base: httpx.URL) -> list[httpx.URL]:
    """Absolute link targets of the selected elements (or the first link inside each)."""
    found: list[httpx.URL] = []
    for element in soup.select(selector):
        anchor = element if element.name == "a" else element.find("a", href=True)
        href = anchor.get("href") if isinstance(anchor, Tag) else None
        if not isinstance(href, str) or href.strip().lower().startswith(_SKIPPED_HREFS):
            continue
        try:
            url = base.join(href.strip()).copy_with(fragment=None)
        except Exception:  # noqa: S112 (a malformed href on someone else's page is just skipped)
            continue
        if url not in found:
            found.append(url)
    return found


def detect_challenge(fetched: Fetched, *, strict: bool = False) -> str | None:
    """What kind of bot check the response is, if any. `strict` treats any CAPTCHA as blocking
    (used for sign-in pages, where a CAPTCHA always stands between us and the account)."""
    if fetched.headers.get("cf-mitigated", "").lower() == "challenge":
        return "a Cloudflare bot check"
    if not fetched.is_html:
        return None
    lowered = fetched.text[:500_000].lower()
    for marker, kind in _STRONG_CHALLENGE_MARKERS.items():
        if marker in lowered:
            return kind
    for marker, kind in _WEAK_CHALLENGE_MARKERS.items():
        if marker in lowered and (
            strict
            or fetched.status_code >= 400
            or len(html_to_text(fetched.text)) < _CAPTCHA_WALL_MAX_TEXT
        ):
            return kind
    return None


def asks_for_one_time_code(soup: BeautifulSoup) -> bool:
    for field in soup.find_all("input"):
        described = " ".join(
            str(field.get(attribute, "")) for attribute in ("name", "id", "autocomplete")
        ).lower()
        if any(marker in described for marker in _ONE_TIME_CODE_MARKERS):
            return True
    return False


def has_password_field(soup: BeautifulSoup) -> bool:
    return soup.select_one("input[type=password]") is not None
