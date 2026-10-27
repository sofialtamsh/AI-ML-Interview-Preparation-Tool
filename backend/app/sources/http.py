"""Outbound HTTP for interview sources, hardened for admin-supplied URLs.

- Only http(s), and never private or internal addresses (localhost, the LAN, cloud metadata). This
  is checked on every request and every redirect hop.
- Credentials are attached only to requests for the source's own origin, so followed links and
  redirects to other sites never receive them.
- Response size and time are capped, requests to a source are spaced out, and robots.txt is
  honoured when crawling pages (RFC 9309).
- GETs that fail transiently (timeouts, dropped connections, 429/502/503/504) are retried a few
  times with backoff, so one network blip doesn't fail a whole run.
- Error messages never contain credentials or query strings.
"""

import base64
import ipaddress
import socket
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from urllib.robotparser import RobotFileParser

import httpx2 as httpx

from app.core.errors import UserFacingError

USER_AGENT = "IPPInterviewBot/1.0 (interview-prep platform; admin-configured source fetcher)"
MAX_RESPONSE_BYTES = 5 * 1024 * 1024
MAX_REDIRECTS = 5
REDIRECT_STATUSES = {301, 302, 303, 307, 308}
RETRY_STATUSES = {429, 502, 503, 504}
RETRY_DELAYS = (2.0, 6.0)  # seconds before each retry
MAX_RETRY_AFTER = 30.0

Resolver = Callable[[str, int], list[str]]


class SourceError(UserFacingError):
    """The source could not be read. The message is shown to admins."""


class _Transient(SourceError):
    """A failure worth retrying: the request may well succeed a moment later."""


class AccessBlocked(SourceError):
    """The source does not allow automated access (robots.txt, CAPTCHA, two-factor sign-in).
    It is never bypassed: the admin imports files instead."""


def system_resolver(host: str, port: int) -> list[str]:
    return [str(info[4][0]) for info in socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)]


def describe(url: httpx.URL | str) -> str:
    """A URL safe for messages: no credentials, query string or fragment."""
    return str(httpx.URL(str(url)).copy_with(query=None, fragment=None, userinfo=b""))


def origin_of(url: httpx.URL | str) -> str:
    parsed = httpx.URL(str(url))
    return f"{parsed.scheme}://{parsed.netloc.decode('ascii')}"


@dataclass
class RequestAuth:
    """Credentials for one origin. Applied only to requests for that origin."""

    origin: str
    headers: dict[str, str] = field(default_factory=dict)
    params: dict[str, str] = field(default_factory=dict)

    @classmethod
    def basic(cls, origin: str, username: str, password: str) -> "RequestAuth":
        token = base64.b64encode(f"{username}:{password}".encode()).decode()
        return cls(origin, headers={"Authorization": f"Basic {token}"})


@dataclass
class Fetched:
    url: httpx.URL
    status_code: int
    headers: httpx.Headers
    body: bytes
    encoding: str | None

    @property
    def media_type(self) -> str:
        return self.headers.get("content-type", "").split(";")[0].strip().lower()

    @property
    def text(self) -> str:
        try:
            return self.body.decode(self.encoding or "utf-8", errors="replace")
        except LookupError:  # an unknown charset name
            return self.body.decode("utf-8", errors="replace")

    @property
    def is_html(self) -> bool:
        return self.media_type in ("text/html", "application/xhtml+xml")


_ROBOTS_ALLOW_ALL = "allow-all"
_ROBOTS_DISALLOW_ALL = "disallow-all"


class SafeHttp:
    def __init__(
        self,
        *,
        transport: httpx.BaseTransport | None = None,
        resolver: Resolver = system_resolver,
        allow_private: bool = False,
        min_interval: float = 0.0,
        max_bytes: int = MAX_RESPONSE_BYTES,
        timeout: float = 30.0,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._client = httpx.Client(
            transport=transport,
            follow_redirects=False,
            timeout=httpx.Timeout(timeout, connect=10.0),
            headers={"User-Agent": USER_AGENT},
        )
        self._resolver = resolver
        self._allow_private = allow_private
        self._max_bytes = max_bytes
        self._deadline = timeout * 2
        self._sleep = sleep
        self.min_interval = min_interval
        self._last_request_at: float | None = None
        self._auth: RequestAuth | None = None
        self._robots: dict[str, RobotFileParser | str] = {}

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "SafeHttp":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def set_auth(self, auth: RequestAuth | None) -> None:
        self._auth = auth

    # --- Public API -----------------------------------------------------------------------

    def get(
        self, url: httpx.URL | str, *, params: dict[str, str] | None = None, crawl: bool = False
    ) -> Fetched:
        """GET with redirects followed safely. `crawl=True` honours robots.txt."""
        return self.request("GET", url, params=params, crawl=crawl)

    def request(
        self,
        method: str,
        url: httpx.URL | str,
        *,
        params: dict[str, str] | None = None,
        data: dict[str, str] | None = None,
        crawl: bool = False,
    ) -> Fetched:
        current = httpx.URL(str(url))
        if params:
            current = current.copy_merge_params(params)
        for _ in range(MAX_REDIRECTS + 1):
            if crawl:
                # Refuse internal addresses first, so the reason given is the real one.
                self.check_destination(current)
                self._check_robots(current)
            fetched = self._send_with_retries(method, current, data)
            location = fetched.headers.get("location")
            if fetched.status_code not in REDIRECT_STATUSES or not location:
                return fetched
            current = fetched.url.join(location)
            if fetched.status_code == 303 or (
                fetched.status_code in (301, 302) and method == "POST"
            ):
                method, data = "GET", None
        raise SourceError(f"Too many redirects starting at {describe(url)}.")

    # --- Internals ------------------------------------------------------------------------

    def check_destination(self, url: httpx.URL) -> None:
        if url.scheme not in ("http", "https"):
            raise SourceError("Only http:// and https:// URLs are supported.")
        host = url.host
        if not host:
            raise SourceError("The URL has no host name.")
        if self._allow_private:
            return
        port = url.port or (443 if url.scheme == "https" else 80)
        try:
            candidates = [host] if _is_ip_literal(host) else self._resolver(host, port)
        except OSError:
            raise SourceError(f"Could not find the site {host} (DNS lookup failed).") from None
        addresses = [_normalise(ipaddress.ip_address(a.split("%")[0])) for a in candidates]
        if not addresses or not all(a.is_global for a in addresses):
            raise SourceError(
                f"{host} points to a private or internal network address. Sources must be "
                "public websites."
            )

    def _wait_turn(self) -> None:
        if self._last_request_at is not None and self.min_interval > 0:
            remaining = self.min_interval - (time.monotonic() - self._last_request_at)
            if remaining > 0:
                self._sleep(remaining)
        self._last_request_at = time.monotonic()

    def _send_with_retries(
        self, method: str, url: httpx.URL, data: dict[str, str] | None
    ) -> Fetched:
        # Only GETs are retried: repeating a POST (e.g. a sign-in) could have side effects.
        retries = RETRY_DELAYS if method == "GET" else ()
        for delay in (*retries, None):
            try:
                fetched = self._send_once(method, url, data)
            except _Transient:
                if delay is None:
                    raise
                self._sleep(delay)
                continue
            if fetched.status_code not in RETRY_STATUSES or delay is None:
                return fetched
            retry_after = fetched.headers.get("retry-after", "")
            self._sleep(
                min(float(retry_after), MAX_RETRY_AFTER) if retry_after.isdigit() else delay
            )
        raise AssertionError("unreachable")  # the last attempt always returns or raises

    def _send_once(self, method: str, url: httpx.URL, data: dict[str, str] | None) -> Fetched:
        self.check_destination(url)
        headers: dict[str, str] = {}
        if self._auth and origin_of(url) == self._auth.origin:
            headers.update(self._auth.headers)
            if self._auth.params:
                url = url.copy_merge_params(self._auth.params)
        self._wait_turn()
        request = self._client.build_request(method, url, headers=headers, data=data)
        started = time.monotonic()
        try:
            response = self._client.send(request, stream=True)
        except httpx.TimeoutException:
            raise _Transient(f"{describe(url)} took too long to respond.") from None
        except httpx.NetworkError as exc:
            raise _Transient(f"Could not reach {describe(url)} ({type(exc).__name__}).") from None
        except httpx.HTTPError as exc:
            raise SourceError(f"Could not reach {describe(url)} ({type(exc).__name__}).") from None
        try:
            declared = response.headers.get("content-length", "")
            if declared.isdigit() and int(declared) > self._max_bytes:
                raise SourceError(f"{describe(url)} is larger than the {self._limit_label} limit.")
            chunks: list[bytes] = []
            size = 0
            for chunk in response.iter_bytes():
                size += len(chunk)
                if size > self._max_bytes:
                    raise SourceError(
                        f"{describe(url)} is larger than the {self._limit_label} limit."
                    )
                if time.monotonic() - started > self._deadline:
                    raise SourceError(f"{describe(url)} took too long to download.")
                chunks.append(chunk)
        except (httpx.TimeoutException, httpx.NetworkError) as exc:
            raise _Transient(
                f"The connection to {describe(url)} failed ({type(exc).__name__})."
            ) from None
        except httpx.HTTPError as exc:
            raise SourceError(
                f"The connection to {describe(url)} failed ({type(exc).__name__})."
            ) from None
        finally:
            response.close()
        return Fetched(
            url=response.url,
            status_code=response.status_code,
            headers=response.headers,
            body=b"".join(chunks),
            encoding=response.charset_encoding,
        )

    @property
    def _limit_label(self) -> str:
        return f"{self._max_bytes // (1024 * 1024)} MB"

    def _check_robots(self, url: httpx.URL) -> None:
        origin = origin_of(url)
        policy = self._robots.get(origin)
        if policy is None:
            policy = self._load_robots(origin)
            self._robots[origin] = policy
        if policy == _ROBOTS_ALLOW_ALL:
            return
        if not isinstance(policy, RobotFileParser):  # disallow-all
            raise AccessBlocked(
                f"Could not read {origin}/robots.txt, so automated access is not assumed to be "
                "allowed. Try again later, or import the pages as files."
            )
        if not policy.can_fetch(USER_AGENT, str(url)):
            raise AccessBlocked(
                f"The site's robots.txt does not allow automated access to {describe(url)}. "
                "Export the pages and import them as files instead."
            )

    def _load_robots(self, origin: str) -> RobotFileParser | str:
        try:
            fetched = self.request("GET", f"{origin}/robots.txt")
        except AccessBlocked:
            raise
        except SourceError:
            return _ROBOTS_DISALLOW_ALL
        # RFC 9309: a missing robots.txt (4xx) allows everything; a server error disallows all.
        if 400 <= fetched.status_code < 500:
            return _ROBOTS_ALLOW_ALL
        if fetched.status_code != 200:
            return _ROBOTS_DISALLOW_ALL
        parser = RobotFileParser()
        parser.parse(fetched.text.splitlines())
        return parser


def _is_ip_literal(host: str) -> bool:
    try:
        ipaddress.ip_address(host.split("%")[0])
    except ValueError:
        return False
    return True


def _normalise(
    address: ipaddress.IPv4Address | ipaddress.IPv6Address,
) -> ipaddress.IPv4Address | ipaddress.IPv6Address:
    if isinstance(address, ipaddress.IPv6Address) and address.ipv4_mapped:
        return address.ipv4_mapped
    return address


def ensure_ok(fetched: Fetched, what: str) -> None:
    """Turn an HTTP error status into a message an admin can act on."""
    status = fetched.status_code
    if status < 400:
        return
    where = describe(fetched.url)
    if status in (401, 403):
        raise SourceError(
            f"{what} refused access (HTTP {status}) at {where}. Check the credentials."
        )
    if status == 404:
        raise SourceError(f"{what} was not found (HTTP 404) at {where}. Check the URL.")
    if status == 429:
        raise SourceError(f"{what} is rate-limiting requests (HTTP 429). Try again later.")
    if status >= 500:
        raise SourceError(f"{what} had a server error (HTTP {status}). Try again later.")
    raise SourceError(f"{what} returned HTTP {status} at {where}.")
