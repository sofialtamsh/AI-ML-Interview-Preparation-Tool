"""The source integration layer on its own: safe HTTP, sign-in, connectors and file parsing."""

import io
from typing import Any

import httpx2 as httpx
import pytest
from pypdf import PdfWriter

from app.sources.auth import FormLoginSettings, form_login
from app.sources.connectors import (
    JsonApiConnector,
    JsonApiSettings,
    RssFeedConnector,
    RssFeedSettings,
    WebPagesConnector,
    WebPagesSettings,
)
from app.sources.files import parse_upload
from app.sources.http import AccessBlocked, RequestAuth, SourceError
from tests.fakeweb import FakeWeb, docx, page, pdf

SITE = "https://interviews.example.com"


class Run:
    """A stand-in for the job's FetchRun."""

    def __init__(self, known: set[str] | None = None) -> None:
        self.state: dict[str, Any] = {}
        self.messages: list[str] = []
        self.warnings: list[str] = []
        self.known = known or set()
        self.skipped = 0

    def info(self, message: str) -> None:
        self.messages.append(message)

    def warn(self, message: str) -> None:
        self.warnings.append(message)

    def is_known(self, external_id: str) -> bool:
        return external_id in self.known

    def skipped_known(self) -> None:
        self.skipped += 1


@pytest.fixture
def web() -> FakeWeb:
    return FakeWeb()


# --- Safe HTTP ------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("address", "url"),
    [
        ("127.0.0.1", "https://internal.example.com/"),
        ("10.0.0.5", "https://internal.example.com/"),
        ("169.254.169.254", "https://internal.example.com/"),  # cloud metadata
        ("::1", "https://internal.example.com/"),
        ("::ffff:192.168.1.1", "https://internal.example.com/"),
        (None, "http://127.0.0.1:8010/api/health"),
        (None, "http://[::1]/"),
    ],
)
def test_private_and_internal_addresses_are_refused(web, address, url):
    if address:
        web.dns["internal.example.com"] = [address]
    with pytest.raises(SourceError, match="private or internal"), web.http() as http:
        http.get(url)
    assert web.requests == []


def test_crawling_an_internal_address_names_the_real_reason(web):
    web.dns["intranet.example.com"] = ["10.1.2.3"]
    connector = WebPagesConnector("https://intranet.example.com", WebPagesSettings(), web.http())
    with pytest.raises(SourceError, match="private or internal") as caught:
        connector.test_connection()
    assert not isinstance(caught.value, AccessBlocked)
    assert web.requests == []


def test_a_redirect_into_the_private_network_is_refused(web):
    web.route(
        f"{SITE}/go",
        lambda _: httpx.Response(302, headers={"location": "http://169.254.169.254/latest/"}),
    )
    with pytest.raises(SourceError, match="private or internal"), web.http() as http:
        http.get(f"{SITE}/go")
    assert web.paths() == ["/go"]


def test_only_http_urls_are_fetched(web):
    with pytest.raises(SourceError, match="Only http"), web.http() as http:
        http.get("file:///etc/passwd")


def test_credentials_only_go_to_the_sources_own_site(web):
    web.route(
        f"{SITE}/start",
        lambda _: httpx.Response(302, headers={"location": "https://cdn.other.com/file"}),
    )
    web.page("https://cdn.other.com/file", "ok")
    with web.http() as http:
        http.set_auth(
            RequestAuth(SITE, headers={"Authorization": "Bearer s3cret"}, params={"key": "k1"})
        )
        http.get(f"{SITE}/start")
    first, second = web.requests
    assert first.headers["authorization"] == "Bearer s3cret"
    assert first.url.params["key"] == "k1"
    assert "authorization" not in second.headers
    assert "key" not in second.url.params


def test_oversized_responses_are_cut_off(web):
    web.page(f"{SITE}/huge", "x" * 5000)
    with pytest.raises(SourceError, match="larger than"), web.http(max_bytes=1024) as http:
        http.get(f"{SITE}/huge")


def test_requests_are_spaced_out(web):
    web.page(f"{SITE}/a", "a")
    pauses: list[float] = []
    http = web.http(min_interval=2.0)
    http._sleep = pauses.append
    http.get(f"{SITE}/a")
    http.get(f"{SITE}/a")
    assert len(pauses) == 1 and 1.5 < pauses[0] <= 2.0


def test_transient_failures_are_retried_with_backoff(web):
    attempts: list[int] = []

    def flaky(_: httpx.Request) -> httpx.Response:
        attempts.append(1)
        if len(attempts) == 1:
            raise httpx.ConnectTimeout("slow")
        if len(attempts) == 2:
            return httpx.Response(503, headers={"retry-after": "4"})
        return httpx.Response(200, text="ok")

    web.route(f"{SITE}/flaky", flaky)
    pauses: list[float] = []
    http = web.http()
    http._sleep = pauses.append
    assert http.get(f"{SITE}/flaky").text == "ok"
    assert pauses == [2.0, 4.0]  # the second wait honours Retry-After


def test_retries_give_up_and_never_repeat_a_post(web):
    web.route(f"{SITE}/down", lambda _: httpx.Response(503))
    with web.http() as http:
        assert http.get(f"{SITE}/down").status_code == 503
    assert web.paths() == ["/down"] * 3

    web.requests.clear()
    web.route(f"{SITE}/login", lambda _: httpx.Response(503), method="POST")
    with web.http() as http:
        assert http.request("POST", f"{SITE}/login", data={"a": "b"}).status_code == 503
    assert len(web.requests) == 1


def test_error_messages_never_include_query_strings(web):
    web.route(f"{SITE}/api", lambda _: (_ for _ in ()).throw(httpx.ConnectError("boom")))
    with pytest.raises(SourceError) as caught, web.http() as http:
        http.set_auth(RequestAuth(SITE, params={"api_key": "top-secret-key"}))
        http.get(f"{SITE}/api")
    assert "top-secret-key" not in str(caught.value)
    assert "ConnectError" in str(caught.value)


# --- robots.txt and bot checks ------------------------------------------------------------


def _web_pages(web: FakeWeb, **settings: Any) -> WebPagesConnector:
    return WebPagesConnector(SITE, WebPagesSettings(**settings), web.http())


def test_robots_txt_disallow_is_honoured(web):
    web.route(
        f"{SITE}/robots.txt",
        lambda _: httpx.Response(200, text="User-agent: *\nDisallow: /private/\n"),
    )
    web.page(f"{SITE}/private/list", page("x", "secret"))
    connector = _web_pages(web, start_urls=[f"{SITE}/private/list"])
    with pytest.raises(AccessBlocked, match="robots.txt"):
        connector.test_connection()
    assert "/private/list" not in web.paths()


def test_robots_txt_server_error_means_no_access(web):
    web.route(f"{SITE}/robots.txt", lambda _: httpx.Response(503))
    with pytest.raises(AccessBlocked):
        _web_pages(web).test_connection()


def test_a_captcha_wall_is_reported_never_bypassed(web):
    web.page(SITE, '<html><body><div class="g-recaptcha"></div>Verify you are human</body></html>')
    with pytest.raises(AccessBlocked, match="CAPTCHA"):
        _web_pages(web).test_connection()


def test_a_page_with_a_captcha_comment_form_is_still_readable(web):
    article = "Interview round 1 covered gradient boosting in depth. " * 60
    web.page(SITE, page("Experience", f"<p>{article}</p><div class='g-recaptcha'></div>"))
    assert _web_pages(web).test_connection().startswith("Connected.")


def test_cloudflare_challenges_are_detected(web):
    web.page(SITE, "Just a moment...", status=403, **{"cf-mitigated": "challenge"})
    with pytest.raises(AccessBlocked, match="Cloudflare"):
        _web_pages(web).test_connection()


# --- Website sign-in form -----------------------------------------------------------------

LOGIN_PAGE = """
<html><body><form action="/session" method="post">
  <input type="hidden" name="csrf" value="tok-123">
  <input name="email"><input type="password" name="pass">
  <input type="checkbox" name="remember" checked value="1">
  <button type="submit">Sign in</button>
</form></body></html>"""


def _login_settings(**overrides: Any) -> FormLoginSettings:
    fields = {"login_url": f"{SITE}/login", "username_field": "email", "password_field": "pass"}
    return FormLoginSettings(**{**fields, **overrides})


def test_form_login_submits_the_form_and_keeps_the_session(web):
    posted: dict[str, str] = {}

    def session(request: httpx.Request) -> httpx.Response:
        posted.update(dict(httpx.QueryParams(request.content.decode())))
        return httpx.Response(
            303, headers={"location": "/home", "set-cookie": "sid=abc; Path=/; HttpOnly"}
        )

    web.page(f"{SITE}/login", LOGIN_PAGE)
    web.route(f"{SITE}/session", session, method="POST")
    web.page(f"{SITE}/home", page("Home", "<a href='/logout'>Log out</a>"))
    web.page(f"{SITE}/members", page("Members", "member content"))

    with web.http() as http:
        form_login(
            http,
            _login_settings(success_text="Log out"),
            {"username": "ops@example.com", "password": "pw-1"},
        )
        http.get(f"{SITE}/members")

    assert posted == {
        "csrf": "tok-123",
        "email": "ops@example.com",
        "pass": "pw-1",
        "remember": "1",
    }
    assert web.requests[-1].headers["cookie"] == "sid=abc"


def test_form_login_with_a_wrong_password_fails_clearly(web):
    web.page(f"{SITE}/login", LOGIN_PAGE)
    web.route(f"{SITE}/session", lambda _: httpx.Response(200, text=LOGIN_PAGE), method="POST")
    with pytest.raises(SourceError, match="sign-in form again"), web.http() as http:
        form_login(http, _login_settings(), {"username": "a", "password": "wrong"})


def test_form_login_stops_at_two_factor_codes(web):
    web.page(f"{SITE}/login", LOGIN_PAGE)
    web.route(
        f"{SITE}/session",
        lambda _: httpx.Response(
            200, text='<form><input name="otp_code" autocomplete="one-time-code"></form>'
        ),
        method="POST",
    )
    with pytest.raises(AccessBlocked, match="one-time code"), web.http() as http:
        form_login(http, _login_settings(), {"username": "a", "password": "b"})


def test_form_login_stops_at_a_captcha(web):
    web.page(f"{SITE}/login", LOGIN_PAGE.replace("</form>", '<div class="h-captcha"></div></form>'))
    with pytest.raises(AccessBlocked, match="CAPTCHA"), web.http() as http:
        form_login(http, _login_settings(), {"username": "a", "password": "b"})
    assert all(r.method == "GET" for r in web.requests)  # the password was never posted


def test_form_login_explains_a_wrong_field_name(web):
    web.page(f"{SITE}/login", LOGIN_PAGE)
    with pytest.raises(SourceError, match='no "username" field'), web.http() as http:
        form_login(
            http,
            _login_settings(username_field="username"),
            {"username": "a", "password": "b"},
        )


# --- Connectors -----------------------------------------------------------------------------


def test_web_pages_follow_listing_links_and_pagination(web):
    web.route(
        f"{SITE}/list",
        lambda r: httpx.Response(
            200,
            text=page("List", "<a class='post' href='/p/3'>Three</a>")
            if r.url.params.get("page") == "2"
            else page(
                "List",
                "<a class='post' href='/p/1'>One</a><a class='post' href='/p/2#top'>Two</a>"
                "<a class='post' href='https://elsewhere.com/p/3'>Off-site</a>"
                "<a rel='next' href='/list?page=2'>Next</a>",
            ),
            headers={"content-type": "text/html"},
        ),
    )
    for n in (1, 2, 3):
        web.page(f"{SITE}/p/{n}", page(f"Post {n}", f"<h1>Post {n}</h1><p>Question {n}</p>"))

    connector = _web_pages(
        web,
        start_urls=[f"{SITE}/list"],
        link_selector="a.post",
        next_page_selector="a[rel=next]",
    )
    run = Run(known={f"{SITE}/p/2"})
    records = list(connector.fetch(run))

    assert [r.external_id for r in records] == [f"{SITE}/p/1", f"{SITE}/p/3"]
    assert records[0].title == "Post 1"
    assert "Question 1" in records[0].content
    assert run.skipped == 1  # /p/2 was fetched before
    assert "elsewhere.com" not in " ".join(str(r.url) for r in web.requests)


def test_web_pages_respect_the_per_run_limit(web):
    links = "".join(f"<a class='post' href='/p/{n}'>{n}</a>" for n in range(10))
    web.page(SITE, page("List", links))
    for n in range(10):
        web.page(f"{SITE}/p/{n}", page(str(n), f"text {n}"))
    records = list(_web_pages(web, link_selector="a.post", max_records=3).fetch(Run()))
    assert len(records) == 3


def _json_api(web: FakeWeb, **settings: Any) -> JsonApiConnector:
    return JsonApiConnector(
        f"{SITE}/", JsonApiSettings.model_validate(settings, context={"base_url": SITE}), web.http()
    )


def test_json_api_page_number_pagination(web):
    pages = {"1": [{"id": 1, "q": "a"}, {"id": 2, "q": "b"}], "2": [{"id": 3, "q": "c"}]}
    web.route(
        f"{SITE}/api/questions",
        lambda r: httpx.Response(200, json={"data": pages.get(r.url.params["page"], [])}),
    )
    connector = _json_api(
        web,
        endpoint="/api/questions",
        items_path="data",
        pagination="page_number",
        page_size_param="per_page",
        page_size=2,
        title_field="q",
    )
    records = list(connector.fetch(Run()))
    assert [r.external_id for r in records] == ["1", "2", "3"]
    assert records[0].title == "a"
    assert [r.url.params["per_page"] for r in web.requests] == ["2", "2"]


def test_json_api_cursor_and_next_url_pagination(web):
    web.route(
        f"{SITE}/api/c",
        lambda r: httpx.Response(
            200,
            json={"items": [{"id": "x"}], "next": "c2"}
            if "cursor" not in r.url.params
            else {"items": [{"id": "y"}], "next": None},
        ),
    )
    cursor = _json_api(
        web, endpoint="/api/c", items_path="items", pagination="cursor", next_path="next"
    )
    assert [r.external_id for r in cursor.fetch(Run())] == ["x", "y"]

    web.json(f"{SITE}/api/n", {"items": [{"id": 1}], "links": {"next": "/api/n2"}})
    web.json(f"{SITE}/api/n2", {"items": [{"id": 2}], "links": {"next": "https://evil.com/x"}})
    run = Run()
    linked = _json_api(
        web, endpoint="/api/n", items_path="items", pagination="next_url", next_path="links.next"
    )
    assert [r.external_id for r in linked.fetch(run)] == ["1", "2"]
    assert any("another site" in w for w in run.warnings)


def test_json_api_explains_a_wrong_items_path_or_id_field(web):
    web.json(f"{SITE}/", {"results": [{"uuid": "a", "text": "t"}]})
    with pytest.raises(SourceError, match='"data" is not a list'):
        _json_api(web, items_path="data").test_connection()
    web.json(f"{SITE}/obj", {"authenticated": True})
    with pytest.raises(SourceError, match="The API response is not a list"):
        _json_api(web, endpoint="/obj").test_connection()
    with pytest.raises(SourceError, match='no "id" field. Fields found: text, uuid'):
        _json_api(web, items_path="results").test_connection()


def test_json_api_asks_only_for_changes_since_the_last_success(web):
    web.json(f"{SITE}/", [])
    run = Run()
    run.state["last_success_started_at"] = "2026-10-27T10:00:00+00:00"
    list(_json_api(web, since_param="updated_since").fetch(run))
    assert web.requests[0].url.params["updated_since"] == "2026-10-27T10:00:00+00:00"
    assert "run_started_at" in run.state


RSS = """<?xml version="1.0"?>
<rss version="2.0" xmlns:content="http://purl.org/rss/1.0/modules/content/"><channel>
<item><title>ML engineer loop</title><link>https://interviews.example.com/p/1</link>
<guid>post-1</guid><pubDate>Tue, 27 Oct 2026 09:00:00 GMT</pubDate>
<description>&lt;p&gt;Asked about &lt;b&gt;bias&lt;/b&gt; and variance&lt;/p&gt;</description>
</item>
</channel></rss>"""

ATOM = """<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom">
<entry><id>urn:1</id><title>Data scientist onsite</title>
<link rel="alternate" href="https://interviews.example.com/a/1"/>
<updated>2026-10-26T08:00:00Z</updated><summary>SQL window functions</summary></entry></feed>"""


def test_rss_and_atom_feeds_are_read(web):
    web.xml(f"{SITE}/feed", RSS)
    web.xml(f"{SITE}/atom", ATOM)
    rss = list(RssFeedConnector(f"{SITE}/feed", RssFeedSettings(), web.http()).fetch(Run()))
    assert rss[0].external_id == "post-1"
    assert rss[0].content == "Asked about\nbias\nand variance"
    assert rss[0].published_at.isoformat() == "2026-10-27T09:00:00+00:00"
    atom = list(RssFeedConnector(f"{SITE}/atom", RssFeedSettings(), web.http()).fetch(Run()))
    assert (atom[0].external_id, atom[0].url) == ("urn:1", "https://interviews.example.com/a/1")


def test_feeds_with_entity_tricks_are_rejected(web):
    bomb = (
        '<?xml version="1.0"?><!DOCTYPE r [<!ENTITY a "aaaaaaaaaa">'
        '<!ENTITY b "&a;&a;&a;&a;&a;&a;&a;&a;">]><rss><channel><item><title>&b;</title>'
        "</item></channel></rss>"
    )
    web.xml(f"{SITE}/feed", bomb)
    with pytest.raises(SourceError, match="not a valid RSS"):
        RssFeedConnector(f"{SITE}/feed", RssFeedSettings(), web.http()).test_connection()


def test_feed_full_pages_fall_back_to_the_summary_when_blocked(web):
    web.xml(f"{SITE}/feed", RSS)
    web.route(
        f"{SITE}/robots.txt", lambda _: httpx.Response(200, text="User-agent: *\nDisallow: /")
    )
    run = Run()
    records = list(
        RssFeedConnector(f"{SITE}/feed", RssFeedSettings(fetch_full_page=True), web.http()).fetch(
            run
        )
    )
    assert records[0].content.startswith("Asked about")
    assert any("robots.txt" in w for w in run.warnings)


# --- File imports ---------------------------------------------------------------------------


def test_csv_rows_become_records_with_stable_ids():
    data = b"id,company,question\n7,Acme,What is dropout?\n8,Beta,Explain ROC AUC\n"
    records = parse_upload("export.csv", data, id_field="id", title_field="question")
    assert [r.external_id for r in records] == ["export.csv#id=7", "export.csv#id=8"]
    assert records[0].content == "id: 7\ncompany: Acme\nquestion: What is dropout?"
    assert records[0].title == "What is dropout?"
    with pytest.raises(SourceError, match='no "uid" column'):
        parse_upload("export.csv", data, id_field="uid")


def test_json_and_jsonl_items_become_records():
    items = parse_upload(
        "q.json", b'{"items": [{"id": 1, "t": "a"}, {"id": 2, "t": "b"}]}', id_field="id"
    )
    assert [r.external_id for r in items] == ["q.json#id=1", "q.json#id=2"]
    lines = parse_upload("q.jsonl", b'{"t": "a"}\n\n{"t": "b"}\n')
    assert len(lines) == 2
    with pytest.raises(SourceError, match="Line 2 is not valid JSON"):
        parse_upload("q.jsonl", b'{"t": "a"}\n{oops\n')


def test_documents_become_one_record():
    (word,) = parse_upload("notes.docx", docx("Round 1", "Explain attention."))
    assert word.content == "Round 1\nExplain attention."
    (doc,) = parse_upload("paper.pdf", pdf("Explain the bias-variance tradeoff"))
    assert "bias-variance tradeoff" in doc.content and doc.content.startswith("[Page 1]")
    (html,) = parse_upload("saved.html", page("Saved", "<h1>Saved page</h1><p>Body</p>").encode())
    assert (html.title, html.external_id) == ("Saved page", "file:saved.html")


def test_unreadable_files_are_explained():
    with pytest.raises(SourceError, match=r"Save it as \.docx"):
        parse_upload("old.doc", b"binary")
    with pytest.raises(SourceError, match="not a valid Word"):
        parse_upload("broken.docx", b"not a zip")
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    writer.encrypt("open-sesame")
    locked = io.BytesIO()
    writer.write(locked)
    with pytest.raises(SourceError, match="password-protected"):
        parse_upload("locked.pdf", locked.getvalue())
    with pytest.raises(SourceError, match="no readable text"):
        parse_upload("empty.txt", b"   \n")
