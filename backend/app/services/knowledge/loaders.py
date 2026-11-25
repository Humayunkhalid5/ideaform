"""Turn uploaded files and fetched HTML into plain text."""

from __future__ import annotations

import io
import logging
import re
from dataclasses import dataclass
from datetime import date
from pathlib import PurePath

logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt", ".md"}


class UnsupportedDocument(ValueError):
    """The file type is not allowed or its text cannot be read."""


@dataclass
class LoadedText:
    title: str
    text: str
    published_at: date | None = None


_FRONT_TITLE = re.compile(r"^title:\s*[\"']?(.+?)[\"']?\s*$", re.I | re.M)


def _title_from_text(text: str, fallback: str) -> str:
    """First heading-like line, or ``title:`` from YAML front matter."""
    if text.lstrip().startswith("---"):
        front, _, rest = text.lstrip()[3:].partition("\n---")
        match = _FRONT_TITLE.search(front)
        if match:
            return match.group(1).strip()
        text = rest or text
    for line in text.splitlines():
        line = line.strip().lstrip("#").strip()
        if 3 <= len(line) <= 200 and any(ch.isalnum() for ch in line):
            return line
    return fallback


def load_file(data: bytes, filename: str) -> LoadedText:
    """Extract text from a PDF, DOCX, TXT or MD upload."""
    suffix = PurePath(filename).suffix.lower()
    stem = PurePath(filename).stem or "Document"
    if suffix not in ALLOWED_EXTENSIONS:
        raise UnsupportedDocument(
            f"Unsupported file type '{suffix or 'none'}'. Upload PDF, DOCX, TXT or MD."
        )

    try:
        if suffix == ".pdf":
            from pypdf import PdfReader

            reader = PdfReader(io.BytesIO(data))
            text = "\n\n".join((page.extract_text() or "") for page in reader.pages)
            meta_title = (reader.metadata.title if reader.metadata else None) or ""
            title = meta_title.strip() or _title_from_text(text, stem)
        elif suffix == ".docx":
            from docx import Document

            doc = Document(io.BytesIO(data))
            parts = []
            for para in doc.paragraphs:
                if not para.text.strip():
                    continue
                style = (para.style.name or "").lower() if para.style is not None else ""
                parts.append(f"# {para.text}" if style.startswith("heading") else para.text)
            text = "\n\n".join(parts)
            title = (doc.core_properties.title or "").strip() or _title_from_text(text, stem)
        else:
            text = data.decode("utf-8", errors="replace")
            title = _title_from_text(text, stem)
            if text.lstrip().startswith("---"):  # drop YAML front matter from the body
                _, sep, body = text.lstrip()[3:].partition("\n---")
                text = body.split("\n", 1)[-1] if sep else text
    except UnsupportedDocument:
        raise
    except Exception as exc:  # noqa: BLE001 - corrupt or encrypted files
        raise UnsupportedDocument(f"Could not read {filename}: {exc}") from exc

    if not text.strip():
        raise UnsupportedDocument(f"{filename} contains no extractable text (scanned PDF?).")
    return LoadedText(title=title[:300], text=text)


_DATE = re.compile(r"(\d{4})-(\d{2})-(\d{2})")


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    match = _DATE.search(value)
    if not match:
        return None
    try:
        return date(int(match[1]), int(match[2]), int(match[3]))
    except ValueError:
        return None


def html_to_text(html: str, url: str | None = None) -> LoadedText | None:
    """Main-text extraction with trafilatura (drops nav, ads, scripts, banners)."""
    import trafilatura

    extracted = trafilatura.bare_extraction(
        html,
        url=url,
        include_comments=False,
        include_tables=True,
        favor_precision=True,
        with_metadata=True,
    )
    if not extracted:
        return None
    doc = extracted if isinstance(extracted, dict) else extracted.as_dict()
    text = doc.get("text") or ""
    if not text.strip():
        return None
    title = (doc.get("title") or "").strip() or _title_from_text(text, url or "Untitled page")
    return LoadedText(title=title[:300], text=text, published_at=_parse_date(doc.get("date")))
