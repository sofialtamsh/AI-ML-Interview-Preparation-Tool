"""A fake internet for source tests: routes by URL, records every request, never touches the
network. DNS answers with a public address unless told otherwise."""

import io
import json
import zipfile
from collections.abc import Callable
from typing import Any

import httpx2 as httpx

from app.sources.http import SafeHttp

PUBLIC_IP = "93.184.216.34"
Handler = Callable[[httpx.Request], httpx.Response]


class FakeWeb:
    def __init__(self) -> None:
        self.routes: dict[tuple[str, str], Handler] = {}
        self.requests: list[httpx.Request] = []
        self.dns: dict[str, list[str]] = {}

    def route(self, url: str, handler: Handler, method: str = "GET") -> None:
        self.routes[(method, url)] = handler

    def page(self, url: str, body: str, *, status: int = 200, **headers: str) -> None:
        response_headers = {"content-type": "text/html; charset=utf-8", **headers}
        self.route(url, lambda _: httpx.Response(status, text=body, headers=response_headers))

    def json(self, url: str, body: Any, *, status: int = 200) -> None:
        self.route(url, lambda _: httpx.Response(status, json=body))

    def xml(self, url: str, body: str) -> None:
        self.route(
            url, lambda _: httpx.Response(200, text=body, headers={"content-type": "text/xml"})
        )

    def handle(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        key = (request.method, str(request.url.copy_with(query=None)))
        handler = self.routes.get(key)
        return handler(request) if handler else httpx.Response(404, text="Not found")

    def resolve(self, host: str, _port: int) -> list[str]:
        return self.dns.get(host, [PUBLIC_IP])

    def http(self, *, min_interval: float = 0.0, max_bytes: int | None = None) -> SafeHttp:
        options: dict[str, Any] = {"max_bytes": max_bytes} if max_bytes else {}
        return SafeHttp(
            transport=httpx.MockTransport(self.handle),
            resolver=self.resolve,
            min_interval=min_interval,
            sleep=lambda _: None,
            **options,
        )

    def paths(self) -> list[str]:
        return [request.url.path for request in self.requests]


def page(title: str, body: str) -> str:
    return f"<html><head><title>{title}</title></head><body><main>{body}</main></body></html>"


def docx(*paragraphs: str) -> bytes:
    ns = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
    body = "".join(f"<w:p><w:r><w:t>{text}</w:t></w:r></w:p>" for text in paragraphs)
    xml = f'<?xml version="1.0"?><w:document xmlns:w="{ns}"><w:body>{body}</w:body></w:document>'
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("[Content_Types].xml", "<Types/>")
        archive.writestr("word/document.xml", xml)
    return buffer.getvalue()


def pdf(text: str) -> bytes:
    """A minimal one-page PDF whose page shows `text`."""
    stream = f"BT /F1 18 Tf 20 100 Td ({text}) Tj ET".encode()
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 600 200] /Contents 4 0 R "
        b"/Resources << /Font << /F1 5 0 R >> >> >>",
        b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    out = io.BytesIO()
    out.write(b"%PDF-1.4\n")
    offsets = []
    for number, body in enumerate(objects, start=1):
        offsets.append(out.tell())
        out.write(b"%d 0 obj\n" % number + body + b"\nendobj\n")
    xref = out.tell()
    out.write(b"xref\n0 %d\n0000000000 65535 f \n" % (len(objects) + 1))
    for offset in offsets:
        out.write(b"%010d 00000 n \n" % offset)
    out.write(
        b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (len(objects) + 1, xref)
    )
    return out.getvalue()


def dumps(value: Any) -> bytes:
    return json.dumps(value).encode()
