"""Turning an uploaded file into source records: the authorised alternative for sources that
can't (or mustn't) be fetched automatically."""

import csv
import hashlib
import io
import json
import zipfile
from pathlib import PurePosixPath
from typing import Any

from defusedxml import ElementTree
from pypdf import PdfReader
from pypdf.errors import PdfReadError

from app.sources.connectors import FetchedRecord, dig, make_record
from app.sources.html import page_text, page_title, parse_html, tidy_text
from app.sources.http import SourceError

MAX_UPLOAD_BYTES = 10 * 1024 * 1024
MAX_ROWS = 20_000
MAX_PDF_PAGES = 1000
MAX_DOCX_XML_BYTES = 50 * 1024 * 1024
SUPPORTED_EXTENSIONS = {
    ".csv": "text/csv",
    ".json": "application/json",
    ".jsonl": "application/x-ndjson",
    ".ndjson": "application/x-ndjson",
    ".txt": "text/plain",
    ".md": "text/markdown",
    ".markdown": "text/markdown",
    ".html": "text/html",
    ".htm": "text/html",
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}
_WORD_NS = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


class UnsupportedFile(SourceError):
    pass


def safe_filename(name: str | None) -> str:
    base = PurePosixPath((name or "upload").replace("\\", "/")).name.strip()
    return base[:200] or "upload"


def parse_upload(
    filename: str, data: bytes, *, id_field: str = "", title_field: str = ""
) -> list[FetchedRecord]:
    """Records from one uploaded file. Tables and JSON lists give one record per row/item;
    documents give one record."""
    extension = PurePosixPath(filename.lower()).suffix
    content_type = SUPPORTED_EXTENSIONS.get(extension)
    if content_type is None:
        hint = " Save it as .docx first." if extension == ".doc" else ""
        raise UnsupportedFile(
            "Unsupported file type. Use CSV, JSON, JSONL, TXT, Markdown, HTML, PDF or Word "
            f"(.docx).{hint}"
        )
    digest = hashlib.sha256(data).hexdigest()
    meta = {"file_name": filename, "file_sha256": digest, "file_size": len(data)}

    if extension == ".csv":
        return _csv_records(filename, _decode(data), meta, id_field, title_field)
    if extension == ".json":
        return _json_records(filename, _load_json(_decode(data)), meta, id_field, title_field)
    if extension in (".jsonl", ".ndjson"):
        items = []
        for number, line in enumerate(_decode(data).splitlines(), start=1):
            if line.strip():
                try:
                    items.append(json.loads(line))
                except ValueError:
                    raise SourceError(f"Line {number} is not valid JSON.") from None
        return _item_records(filename, items, meta, id_field, title_field)

    if extension in (".html", ".htm"):
        soup = parse_html(_decode(data))
        title = page_title(soup)
        text = page_text(soup)
    elif extension == ".pdf":
        title, text = None, _pdf_text(data)
    elif extension == ".docx":
        title, text = None, _docx_text(data)
    else:
        title, text = None, tidy_text(_decode(data))
    if not text:
        raise SourceError("The file contains no readable text.")
    return [
        make_record(
            external_id=f"file:{filename}",
            content=text,
            content_type=content_type,
            title=title or filename,
            meta=meta,
        )
    ]


def _decode(data: bytes) -> str:
    try:
        return data.decode("utf-8-sig")
    except UnicodeDecodeError:
        return data.decode("cp1252", errors="replace")


def _load_json(text: str) -> Any:
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise SourceError(f"The file is not valid JSON (line {exc.lineno}).") from None


def _row_id(filename: str, id_value: Any, content: str) -> str:
    if id_value not in (None, ""):
        return f"{filename}#id={id_value}"
    return f"{filename}#{hashlib.sha256(content.encode()).hexdigest()[:24]}"


def _csv_records(
    filename: str, text: str, meta: dict[str, Any], id_field: str, title_field: str
) -> list[FetchedRecord]:
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise SourceError("The CSV file has no header row.")
    for wanted in (id_field, title_field):
        if wanted and wanted not in reader.fieldnames:
            raise SourceError(
                f'The CSV has no "{wanted}" column. Columns: {", ".join(reader.fieldnames)}.'
            )
    records = []
    for number, row in enumerate(reader, start=2):
        if number - 1 > MAX_ROWS:
            raise SourceError(f"The file has more than {MAX_ROWS:,} rows; split it into parts.")
        lines = [f"{key}: {value.strip()}" for key, value in row.items() if key and value]
        if not lines:
            continue
        content = "\n".join(lines)
        records.append(
            make_record(
                external_id=_row_id(filename, row.get(id_field) if id_field else None, content),
                content=content,
                content_type="text/csv",
                title=(row.get(title_field) or "")[:500] or None,
                meta={**meta, "row": number},
            )
        )
    if not records:
        raise SourceError("The CSV file has no data rows.")
    return records


def _json_records(
    filename: str, document: Any, meta: dict[str, Any], id_field: str, title_field: str
) -> list[FetchedRecord]:
    if isinstance(document, list):
        return _item_records(filename, document, meta, id_field, title_field)
    if isinstance(document, dict):
        for value in document.values():
            if isinstance(value, list) and value and all(isinstance(v, dict) for v in value):
                return _item_records(filename, value, meta, id_field, title_field)
    content = json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True)
    return [
        make_record(
            external_id=f"file:{filename}",
            content=content,
            content_type="application/json",
            title=filename,
            meta=meta,
        )
    ]


def _item_records(
    filename: str, items: list[Any], meta: dict[str, Any], id_field: str, title_field: str
) -> list[FetchedRecord]:
    if len(items) > MAX_ROWS:
        raise SourceError(f"The file has more than {MAX_ROWS:,} items; split it into parts.")
    records = []
    for index, item in enumerate(items):
        content = json.dumps(item, ensure_ascii=False, indent=2, sort_keys=True)
        title = dig(item, title_field) if title_field else None
        records.append(
            make_record(
                external_id=_row_id(filename, dig(item, id_field) if id_field else None, content),
                content=content,
                content_type="application/json",
                title=str(title)[:500] if title not in (None, "") else None,
                meta={**meta, "item": index},
            )
        )
    if not records:
        raise SourceError("The file has no items.")
    return records


def _pdf_text(data: bytes) -> str:
    try:
        reader = PdfReader(io.BytesIO(data))
        if reader.is_encrypted and not reader.decrypt(""):
            raise SourceError("The PDF is password-protected. Remove the password and try again.")
        if len(reader.pages) > MAX_PDF_PAGES:
            raise SourceError(f"The PDF has more than {MAX_PDF_PAGES} pages; split it into parts.")
        pages = [
            f"[Page {number}]\n{text}"
            for number, page in enumerate(reader.pages, start=1)
            if (text := tidy_text(page.extract_text() or ""))
        ]
    except SourceError:
        raise
    except (PdfReadError, ValueError, KeyError, TypeError):
        raise SourceError("The PDF could not be read. It may be damaged.") from None
    if not pages:
        raise SourceError(
            "The PDF has no selectable text (it may be scanned images). Scanned documents "
            "aren't supported yet."
        )
    return "\n\n".join(pages)


def _docx_text(data: bytes) -> str:
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            info = archive.getinfo("word/document.xml")
            if info.file_size > MAX_DOCX_XML_BYTES:
                raise SourceError("The Word document is too large to read.")
            root = ElementTree.fromstring(archive.read(info))
    except SourceError:
        raise
    except (zipfile.BadZipFile, KeyError):
        raise SourceError("The file is not a valid Word (.docx) document.") from None
    except Exception:  # XML parse errors, or defusedxml refusing entities
        raise SourceError("The Word document could not be read. It may be damaged.") from None
    paragraphs = []
    for paragraph in root.iter(f"{_WORD_NS}p"):
        text = "".join(node.text or "" for node in paragraph.iter(f"{_WORD_NS}t"))
        if text.strip():
            paragraphs.append(text)
    return tidy_text("\n".join(paragraphs))
