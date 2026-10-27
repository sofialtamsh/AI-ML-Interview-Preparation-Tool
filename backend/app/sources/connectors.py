"""Connectors: how each kind of source is read. A new URL is configuration; a new *kind* of
source is a new class registered in CONNECTORS."""

import email.utils
import hashlib
import json
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Annotated, Any, ClassVar, Literal, Protocol

import httpx2 as httpx
from defusedxml import ElementTree
from pydantic import Field, StringConstraints, ValidationInfo, field_validator

from app.models import AuthMethod, ConnectorType
from app.sources.fields import (
    CssSelector,
    DotPath,
    FieldOption,
    FieldSpec,
    ParamName,
    StrictModel,
    WebUrl,
    ui_fields,
)
from app.sources.html import detect_challenge, links, page_text, page_title, parse_html, tidy_text
from app.sources.http import (
    AccessBlocked,
    Fetched,
    SafeHttp,
    SourceError,
    describe,
    ensure_ok,
    origin_of,
)

MAX_RECORD_CHARS = 1_000_000


@dataclass
class FetchedRecord:
    external_id: str
    content: str
    content_type: str
    url: str | None = None
    title: str | None = None
    published_at: datetime | None = None
    meta: dict[str, Any] = field(default_factory=dict)


class FetchRun(Protocol):
    """What a connector can see and report while it fetches."""

    state: dict[str, Any]

    def info(self, message: str) -> None: ...

    def warn(self, message: str) -> None: ...

    def is_known(self, external_id: str) -> bool: ...

    def skipped_known(self) -> None: ...


def _same_origin_urls(urls: list[str], info: ValidationInfo) -> list[str]:
    """Configured URLs must be on the base URL's site: credentials are only ever sent there."""
    base = (info.context or {}).get("base_url")
    if base:
        for url in urls:
            if origin_of(url) != origin_of(base):
                raise ValueError(
                    f"{describe(url)} is not on the same site as the base URL ({origin_of(base)})"
                )
    return urls


class Connector:
    type: ClassVar[ConnectorType]
    label: ClassVar[str]
    description: ClassVar[str]
    settings_model: ClassVar[type[StrictModel]]
    settings_fields: ClassVar[list[FieldSpec]]
    auth_methods: ClassVar[tuple[AuthMethod, ...]]
    uses_url: ClassVar[bool] = True

    def __init__(self, base_url: str, settings: Any, http: SafeHttp) -> None:
        self.base_url = httpx.URL(base_url)
        self.settings = settings
        self.http = http

    def test_connection(self) -> str:
        raise NotImplementedError

    def fetch(self, run: FetchRun) -> Iterator[FetchedRecord]:
        raise NotImplementedError

    # Shared helpers --------------------------------------------------------------------------

    def _page(self, url: httpx.URL | str, *, crawl: bool) -> Fetched:
        fetched = self.http.get(url, crawl=crawl)
        if challenge := detect_challenge(fetched):
            raise AccessBlocked(
                f"{describe(fetched.url)} shows {challenge}. The platform never bypasses bot "
                "checks: export the pages and import them as files instead."
            )
        ensure_ok(fetched, "The page")
        return fetched

    def _page_record(self, fetched: Fetched, content_selector: str) -> FetchedRecord | None:
        url = str(fetched.url.copy_with(fragment=None))
        if fetched.is_html:
            soup = parse_html(fetched.text)
            title = page_title(soup)
            text = page_text(soup, content_selector)
        elif fetched.media_type.startswith("text/"):
            title, text = None, tidy_text(fetched.text)
        else:
            return None
        return make_record(
            external_id=url,
            content=text,
            content_type=fetched.media_type or "text/html",
            url=url,
            title=title,
            meta={"http_status": fetched.status_code},
        )


def make_record(**values: Any) -> FetchedRecord:
    content: str = values.pop("content")
    meta: dict[str, Any] = values.pop("meta", {})
    if len(content) > MAX_RECORD_CHARS:
        content = content[:MAX_RECORD_CHARS]
        meta = {**meta, "truncated": True}
    return FetchedRecord(content=content, meta=meta, **values)


# --- Website pages ------------------------------------------------------------------------------


class WebPagesSettings(StrictModel):
    start_urls: list[WebUrl] = Field(default_factory=list, max_length=50)
    link_selector: CssSelector = ""
    next_page_selector: CssSelector = ""
    max_listing_pages: int = Field(default=5, ge=1, le=50)
    content_selector: CssSelector = ""
    skip_known_pages: bool = True
    max_records: int = Field(default=50, ge=1, le=1000)
    delay_seconds: float = Field(default=1.0, ge=0.5, le=30)

    @field_validator("start_urls")
    @classmethod
    def _same_site(cls, value: list[str], info: ValidationInfo) -> list[str]:
        return _same_origin_urls(value, info)


class WebPagesConnector(Connector):
    type = ConnectorType.WEB_PAGES
    label = "Website pages"
    description = (
        "Reads pages of a website, e.g. a list of interview experiences and the articles it "
        "links to. Honours the site's robots.txt."
    )
    settings_model = WebPagesSettings
    settings_fields = ui_fields(
        WebPagesSettings,
        [
            FieldSpec(
                key="start_urls",
                label="Pages to start from",
                kind="lines",
                help="One URL per line, on the same site as the base URL. Leave empty to start "
                "from the base URL.",
            ),
            FieldSpec(
                key="link_selector",
                label="Links to follow (CSS selector)",
                placeholder="a.experience-title",
                help="Leave empty to read the start pages themselves. Set it to read every "
                "article the start pages link to instead (same site only).",
            ),
            FieldSpec(
                key="next_page_selector",
                label='"Next page" link (CSS selector)',
                placeholder="a[rel=next]",
                help="Optional. Follows the listing's pagination.",
                visible_when={"link_selector": ["*"]},
            ),
            FieldSpec(
                key="max_listing_pages",
                label="Listing pages per start page",
                kind="number",
                visible_when={"link_selector": ["*"]},
            ),
            FieldSpec(
                key="content_selector",
                label="Main content (CSS selector)",
                placeholder="article .post-body",
                help="Optional. By default the page's main text is used, without menus.",
            ),
            FieldSpec(
                key="skip_known_pages",
                label="Skip pages already fetched",
                kind="checkbox",
                help="Faster repeat runs. Turn off to re-read every page and catch edits.",
            ),
            FieldSpec(key="max_records", label="Most pages per run", kind="number"),
            FieldSpec(
                key="delay_seconds",
                label="Seconds between requests",
                kind="number",
                help="Keeps the load on the site polite.",
            ),
        ],
    )
    auth_methods = (
        AuthMethod.NONE,
        AuthMethod.HTTP_BASIC,
        AuthMethod.BEARER_TOKEN,
        AuthMethod.API_KEY_HEADER,
        AuthMethod.FORM_LOGIN,
    )
    settings: WebPagesSettings

    def _start_urls(self) -> list[httpx.URL]:
        return [httpx.URL(u) for u in self.settings.start_urls] or [self.base_url]

    def test_connection(self) -> str:
        first = self._page(self._start_urls()[0], crawl=True)
        if not first.is_html:
            raise SourceError(f"{describe(first.url)} is not an HTML page ({first.media_type}).")
        if self.settings.link_selector:
            found = links(parse_html(first.text), self.settings.link_selector, first.url)
            same_site = [u for u in found if origin_of(u) == origin_of(first.url)]
            if not same_site:
                return (
                    f"Connected, but no links on {describe(first.url)} match "
                    f'"{self.settings.link_selector}". Check the selector.'
                )
            return f"Connected. The first page links to {len(same_site)} matching pages."
        record = self._page_record(first, self.settings.content_selector)
        if record is None or not record.content:
            return "Connected, but no text was found on the page. Check the content selector."
        return f"Connected. The first page has {len(record.content):,} characters of text."

    def fetch(self, run: FetchRun) -> Iterator[FetchedRecord]:
        settings = self.settings
        produced = 0
        if not settings.link_selector:
            for url in self._start_urls():
                if produced >= settings.max_records:
                    return
                if settings.skip_known_pages and run.is_known(str(url)):
                    run.skipped_known()
                    continue
                if record := self._read(url, run):
                    produced += 1
                    yield record
            return

        seen: set[httpx.URL] = set()
        for start in self._start_urls():
            listing: httpx.URL | None = start
            visited: set[httpx.URL] = set()
            while listing is not None and len(visited) < settings.max_listing_pages:
                visited.add(listing)
                page = self._page(listing, crawl=True)
                soup = parse_html(page.text)
                targets = [
                    u
                    for u in links(soup, settings.link_selector, page.url)
                    if origin_of(u) == origin_of(page.url) and u not in seen
                ]
                run.info(f"{describe(page.url)} links to {len(targets)} new matching pages.")
                for url in targets:
                    if produced >= settings.max_records:
                        run.info(f"Stopped at the limit of {settings.max_records} pages per run.")
                        return
                    seen.add(url)
                    if settings.skip_known_pages and run.is_known(str(url)):
                        run.skipped_known()
                        continue
                    if record := self._read(url, run):
                        produced += 1
                        yield record
                listing = None
                if settings.next_page_selector:
                    following = links(soup, settings.next_page_selector, page.url)
                    nxt = following[0] if following else None
                    if nxt and origin_of(nxt) == origin_of(page.url) and nxt not in visited:
                        listing = nxt

    def _read(self, url: httpx.URL, run: FetchRun) -> FetchedRecord | None:
        try:
            fetched = self._page(url, crawl=True)
        except AccessBlocked:
            raise
        except SourceError as exc:
            run.warn(str(exc))
            return None
        record = self._page_record(fetched, self.settings.content_selector)
        if record is None:
            run.warn(f"Skipped {describe(url)}: not a web page ({fetched.media_type}).")
            return None
        if not record.content:
            run.warn(
                f"No text found on {describe(url)}. The page may need JavaScript, or the content "
                "selector doesn't match."
            )
            return None
        return record


# --- JSON API -------------------------------------------------------------------------------------

Pagination = Literal["none", "page_number", "offset", "next_url", "cursor"]
QueryLine = Annotated[str, StringConstraints(max_length=300, pattern=r"^[^=\s]+=.*$")]


def dig(value: Any, path: str) -> Any:
    """Follow a dot path such as "data.items" or "results.0.id"; None if it doesn't exist."""
    if not path:
        return value
    for part in path.split("."):
        if isinstance(value, dict):
            value = value.get(part)
        elif isinstance(value, list) and part.isdigit() and int(part) < len(value):
            value = value[int(part)]
        else:
            return None
    return value


def _parse_datetime(value: Any) -> datetime | None:
    if isinstance(value, int | float) and not isinstance(value, bool):
        try:
            return datetime.fromtimestamp(value / 1000 if value > 10**11 else value, UTC)
        except (OverflowError, OSError, ValueError):
            return None
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip()
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        try:
            parsed = email.utils.parsedate_to_datetime(text)
        except (TypeError, ValueError, IndexError):
            return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


class JsonApiSettings(StrictModel):
    endpoint: Annotated[str, StringConstraints(max_length=2048)] = ""
    items_path: DotPath = ""
    id_field: DotPath = "id"
    title_field: DotPath = ""
    url_field: DotPath = ""
    date_field: DotPath = ""
    pagination: Pagination = "none"
    page_param: ParamName = "page"
    offset_param: ParamName = "offset"
    page_size_param: ParamName | Literal[""] = ""
    page_size: int = Field(default=50, ge=1, le=1000)
    next_path: DotPath = Field(default="", validate_default=True)
    cursor_param: ParamName = "cursor"
    since_param: ParamName | Literal[""] = ""
    query_params: list[QueryLine] = Field(default_factory=list, max_length=30)
    max_pages: int = Field(default=10, ge=1, le=500)
    delay_seconds: float = Field(default=0.5, ge=0, le=30)

    @field_validator("endpoint")
    @classmethod
    def _endpoint_on_same_site(cls, value: str, info: ValidationInfo) -> str:
        base = (info.context or {}).get("base_url")
        if value and base:
            try:
                target = httpx.URL(base).join(value)
            except Exception:
                raise ValueError("Enter a path such as /api/v1/posts, or a full URL") from None
            _same_origin_urls([str(target)], info)
        return value

    @field_validator("next_path")
    @classmethod
    def _next_path_needed(cls, value: str, info: ValidationInfo) -> str:
        if not value and info.data.get("pagination") in ("next_url", "cursor"):
            raise ValueError("Required for this kind of pagination")
        return value


class JsonApiConnector(Connector):
    type = ConnectorType.JSON_API
    label = "JSON API"
    description = "Reads items from an API that returns JSON, page by page."
    settings_model = JsonApiSettings
    _paged = ["page_number", "offset"]
    settings_fields = ui_fields(
        JsonApiSettings,
        [
            FieldSpec(
                key="endpoint",
                label="Endpoint",
                placeholder="/api/v1/interviews",
                help="A path on the base URL's site (or a full URL on it). Empty = the base URL.",
            ),
            FieldSpec(
                key="items_path",
                label="Where the items are",
                placeholder="data.items",
                help="Dot path to the list in each response. Empty if the response is the list.",
            ),
            FieldSpec(
                key="id_field",
                label="Item ID field",
                help="A field that uniquely identifies each item. Used to skip items seen before.",
            ),
            FieldSpec(key="title_field", label="Title field (optional)", placeholder="title"),
            FieldSpec(key="url_field", label="Link field (optional)", placeholder="url"),
            FieldSpec(key="date_field", label="Date field (optional)", placeholder="created_at"),
            FieldSpec(
                key="pagination",
                label="Pagination",
                kind="select",
                options=[
                    FieldOption(value="none", label="None (one request)"),
                    FieldOption(value="page_number", label="Page number (?page=1, 2, …)"),
                    FieldOption(value="offset", label="Offset (?offset=0, 50, …)"),
                    FieldOption(value="next_url", label="Next-page URL in the response"),
                    FieldOption(value="cursor", label="Cursor in the response"),
                ],
            ),
            FieldSpec(
                key="page_param",
                label="Page parameter",
                visible_when={"pagination": ["page_number"]},
            ),
            FieldSpec(
                key="offset_param",
                label="Offset parameter",
                visible_when={"pagination": ["offset"]},
            ),
            FieldSpec(
                key="page_size_param",
                label="Page-size parameter (optional)",
                placeholder="limit",
                visible_when={"pagination": _paged},
            ),
            FieldSpec(
                key="page_size",
                label="Items per page",
                kind="number",
                visible_when={"pagination": _paged},
            ),
            FieldSpec(
                key="next_path",
                label="Where the next page is",
                placeholder="links.next",
                help="Dot path to the next-page URL or cursor in each response.",
                visible_when={"pagination": ["next_url", "cursor"]},
            ),
            FieldSpec(
                key="cursor_param",
                label="Cursor parameter",
                visible_when={"pagination": ["cursor"]},
            ),
            FieldSpec(
                key="since_param",
                label='"Changed since" parameter (optional)',
                placeholder="updated_since",
                help="If the API supports it, later runs only ask for items changed since the "
                "last successful run.",
            ),
            FieldSpec(
                key="query_params",
                label="Extra query parameters",
                kind="lines",
                placeholder="category=machine-learning",
                help="One key=value per line. Not for secrets; use credentials for keys.",
            ),
            FieldSpec(key="max_pages", label="Most pages per run", kind="number"),
            FieldSpec(key="delay_seconds", label="Seconds between requests", kind="number"),
        ],
    )
    auth_methods = (
        AuthMethod.NONE,
        AuthMethod.HTTP_BASIC,
        AuthMethod.BEARER_TOKEN,
        AuthMethod.API_KEY_HEADER,
        AuthMethod.API_KEY_QUERY,
    )
    settings: JsonApiSettings

    def _first_url(self) -> httpx.URL:
        endpoint = self.settings.endpoint
        return self.base_url.join(endpoint) if endpoint else self.base_url

    def _base_params(self) -> dict[str, str]:
        params = dict(line.split("=", 1) for line in self.settings.query_params)
        return {k.strip(): v.strip() for k, v in params.items()}

    def _get_json(self, url: httpx.URL, params: dict[str, str]) -> Any:
        fetched = self.http.get(url, params=params)
        ensure_ok(fetched, "The API")
        try:
            return json.loads(fetched.text)
        except ValueError:
            raise SourceError(
                f"{describe(fetched.url)} did not return JSON "
                f"(it returned {fetched.media_type or 'an unknown type'})."
            ) from None

    def _items(self, body: Any) -> list[Any]:
        items = dig(body, self.settings.items_path)
        if not isinstance(items, list):
            if not self.settings.items_path:
                raise SourceError(
                    'The API response is not a list. Set "Where the items are" to the path of '
                    "the list inside it."
                )
            raise SourceError(
                f'"{self.settings.items_path}" is not a list in the API response. Check '
                '"Where the items are".'
            )
        return items

    def _pages(self, params: dict[str, str], run: FetchRun | None) -> Iterator[list[Any]]:
        s = self.settings
        url = self._first_url()
        page_number, offset, cursor = 1, 0, None
        for page_index in range(s.max_pages):
            query = dict(params)
            if s.pagination == "page_number":
                query[s.page_param] = str(page_number)
            if s.pagination == "offset":
                query[s.offset_param] = str(offset)
            if s.pagination in ("page_number", "offset") and s.page_size_param:
                query[s.page_size_param] = str(s.page_size)
            if s.pagination == "cursor" and cursor:
                query[s.cursor_param] = cursor
            body = self._get_json(url, query)
            items = self._items(body)
            yield items

            if s.pagination == "none" or not items:
                return
            if s.pagination in ("page_number", "offset"):
                if s.page_size_param and len(items) < s.page_size:
                    return
                page_number += 1
                offset += len(items)
            elif s.pagination == "next_url":
                nxt = dig(body, s.next_path)
                if not isinstance(nxt, str) or not nxt:
                    return
                url = url.join(nxt)
                if origin_of(url) != origin_of(self.base_url):
                    if run:
                        run.warn("The next-page link points to another site; stopped there.")
                    return
                params = {}  # the next URL carries its own query
            elif s.pagination == "cursor":
                nxt = dig(body, s.next_path)
                if nxt in (None, "") or str(nxt) == cursor:
                    return
                cursor = str(nxt)
            if page_index == s.max_pages - 1 and run:
                run.info(f"Stopped at the limit of {s.max_pages} pages per run.")

    def test_connection(self) -> str:
        items = next(self._pages(self._base_params(), None))
        if not items:
            return "Connected, but the first page has no items. Check the items path."
        first = items[0]
        if dig(first, self.settings.id_field) is None:
            fields = ", ".join(sorted(first)[:15]) if isinstance(first, dict) else "none"
            raise SourceError(
                f'Items have no "{self.settings.id_field}" field. Fields found: {fields}.'
            )
        return f"Connected. The first page has {len(items)} items."

    def fetch(self, run: FetchRun) -> Iterator[FetchedRecord]:
        s = self.settings
        params = self._base_params()
        since = run.state.get("last_success_started_at")
        if s.since_param and since:
            params[s.since_param] = since
            run.info(f"Asking only for items changed since {since}.")
        run.state["run_started_at"] = datetime.now(UTC).isoformat()
        for items in self._pages(params, run):
            for item in items:
                item_id = dig(item, s.id_field)
                if item_id is None or isinstance(item_id, dict | list):
                    run.warn(f'Skipped an item without a usable "{s.id_field}" value.')
                    continue
                title = dig(item, s.title_field) if s.title_field else None
                link = dig(item, s.url_field) if s.url_field else None
                yield make_record(
                    external_id=str(item_id),
                    content=json.dumps(item, ensure_ascii=False, indent=2, sort_keys=True),
                    content_type="application/json",
                    url=str(self.base_url.join(link)) if isinstance(link, str) and link else None,
                    title=str(title)[:500] if title not in (None, "") else None,
                    published_at=_parse_datetime(dig(item, s.date_field)) if s.date_field else None,
                )


# --- RSS / Atom ---------------------------------------------------------------------------------


class RssFeedSettings(StrictModel):
    feed_url: WebUrl | Literal[""] = ""
    fetch_full_page: bool = False
    content_selector: CssSelector = ""
    skip_known_pages: bool = True
    max_records: int = Field(default=50, ge=1, le=1000)
    delay_seconds: float = Field(default=1.0, ge=0.5, le=30)

    @field_validator("feed_url")
    @classmethod
    def _feed_on_same_site(cls, value: str, info: ValidationInfo) -> str:
        return _same_origin_urls([value], info)[0] if value else value


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1].lower()


def _child_text(element: Any, *names: str) -> str:
    """The text of the first child with one of these names, in order of preference."""
    texts = {
        _local(c.tag): c.text.strip() for c in reversed(list(element)) if (c.text or "").strip()
    }
    return next((texts[name] for name in names if name in texts), "")


def _entry_link(element: Any) -> str:
    for child in element:
        if _local(child.tag) != "link":
            continue
        href = child.get("href")
        if href and child.get("rel", "alternate") == "alternate":
            return href.strip()
        if not href and (child.text or "").strip():
            return child.text.strip()
    return ""


class RssFeedConnector(Connector):
    type = ConnectorType.RSS_FEED
    label = "RSS / Atom feed"
    description = "Reads a site's feed of new posts, and optionally each post's full page."
    settings_model = RssFeedSettings
    settings_fields = ui_fields(
        RssFeedSettings,
        [
            FieldSpec(
                key="feed_url",
                label="Feed URL",
                kind="url",
                placeholder="https://example.com/feed.xml",
                help="Empty = the base URL is the feed.",
            ),
            FieldSpec(
                key="fetch_full_page",
                label="Read each post's full page",
                kind="checkbox",
                help="Feeds often carry only a summary. Honours the site's robots.txt.",
            ),
            FieldSpec(
                key="content_selector",
                label="Main content (CSS selector)",
                placeholder="article",
                visible_when={"fetch_full_page": ["true"]},
            ),
            FieldSpec(
                key="skip_known_pages",
                label="Skip posts already fetched",
                kind="checkbox",
                visible_when={"fetch_full_page": ["true"]},
            ),
            FieldSpec(key="max_records", label="Most posts per run", kind="number"),
            FieldSpec(key="delay_seconds", label="Seconds between requests", kind="number"),
        ],
    )
    auth_methods = (
        AuthMethod.NONE,
        AuthMethod.HTTP_BASIC,
        AuthMethod.BEARER_TOKEN,
        AuthMethod.API_KEY_HEADER,
        AuthMethod.API_KEY_QUERY,
    )
    settings: RssFeedSettings

    def _entries(self) -> tuple[httpx.URL, list[Any]]:
        url = httpx.URL(self.settings.feed_url) if self.settings.feed_url else self.base_url
        fetched = self.http.get(url)
        ensure_ok(fetched, "The feed")
        try:
            root = ElementTree.fromstring(fetched.body)
        except Exception:  # ParseError, or defusedxml refusing entities/DTDs
            raise SourceError(f"{describe(fetched.url)} is not a valid RSS or Atom feed.") from None
        entries = [el for el in root.iter() if _local(el.tag) in ("item", "entry")]
        if _local(root.tag) not in ("rss", "feed", "rdf"):
            raise SourceError(f"{describe(fetched.url)} is XML, but not an RSS or Atom feed.")
        return fetched.url, entries

    def test_connection(self) -> str:
        _, entries = self._entries()
        return f"Connected. The feed has {len(entries)} posts."

    def fetch(self, run: FetchRun) -> Iterator[FetchedRecord]:
        s = self.settings
        feed_url, entries = self._entries()
        produced = 0
        for entry in entries:
            if produced >= s.max_records:
                run.info(f"Stopped at the limit of {s.max_records} posts per run.")
                return
            link = _entry_link(entry)
            url = str(feed_url.join(link)) if link else None
            title = _child_text(entry, "title")
            summary = _child_text(entry, "encoded", "content", "description", "summary")
            external_id = (
                _child_text(entry, "guid", "id")
                or url
                or hashlib.sha256(f"{title}\n{summary}".encode()).hexdigest()
            )
            published = _parse_datetime(
                _child_text(entry, "pubdate", "published", "updated", "date")
            )
            content = tidy_text(page_text(parse_html(summary))) if summary else ""
            meta: dict[str, Any] = {"from": "feed"}

            if s.fetch_full_page and url:
                if s.skip_known_pages and run.is_known(external_id):
                    run.skipped_known()
                    continue
                try:
                    page = self._page(url, crawl=True)
                    full = self._page_record(page, s.content_selector)
                    if full and full.content:
                        content, meta = full.content, {"from": "page", **full.meta}
                except SourceError as exc:  # including AccessBlocked: never bypassed
                    run.warn(f"{exc} Kept the feed summary instead.")
            if not content and not title:
                run.warn("Skipped a feed entry with no title or text.")
                continue
            produced += 1
            yield make_record(
                external_id=external_id[:1024],
                content=content or title,
                content_type="text/plain",
                url=url,
                title=title[:500] or None,
                published_at=published,
                meta=meta,
            )


# --- Manual file import ------------------------------------------------------------------------


class FileImportSettings(StrictModel):
    pass


class FileImportConnector(Connector):
    """Files an admin uploads: for documents, exports, and sites that block automation."""

    type = ConnectorType.FILE_UPLOAD
    label = "File import"
    description = (
        "You upload files (CSV, JSON, PDF, Word, text or saved web pages) instead of the "
        "platform fetching them."
    )
    settings_model = FileImportSettings
    settings_fields: ClassVar[list[FieldSpec]] = []
    auth_methods = (AuthMethod.NONE,)
    uses_url = False


CONNECTORS: dict[ConnectorType, type[Connector]] = {
    c.type: c for c in (WebPagesConnector, JsonApiConnector, RssFeedConnector, FileImportConnector)
}
