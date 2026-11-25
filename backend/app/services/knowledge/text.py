"""Text cleaning, hashing, chunking and quality heuristics (no external deps)."""

from __future__ import annotations

import hashlib
import re
import unicodedata
from dataclasses import dataclass

_WS = re.compile(r"[ \t\f\v]+")
_BLANKS = re.compile(r"\n{3,}")
_WORD = re.compile(r"[A-Za-z][A-Za-z'\-]+")
_HEADING = re.compile(r"^(#{1,6}\s+.+|={2,}\s*.+?\s*={2,})$")

BOILERPLATE = (
    "accept cookies",
    "cookie policy",
    "we use cookies",
    "subscribe to our newsletter",
    "sign up for our newsletter",
    "all rights reserved",
    "skip to main content",
    "javascript is disabled",
    "enable javascript",
    "share on facebook",
    "share on twitter",
    "advertisement",
)

ENGLISH_STOPWORDS = frozenset(
    "the of and to a in is that for it as with on be by this are from or an at "
    "was which can have not but their they has more its also we you will one "
    "use used these other such than into about how what when".split()
)


def clean_text(text: str) -> str:
    """Normalise unicode and whitespace and drop obvious boilerplate lines."""
    text = unicodedata.normalize("NFKC", text or "")
    text = text.replace("\r\n", "\n").replace("\r", "\n").replace(" ", " ")
    lines = []
    for raw in text.split("\n"):
        line = _WS.sub(" ", raw).strip()
        low = line.lower()
        if line and len(line) < 160 and any(b in low for b in BOILERPLATE):
            continue
        lines.append(line)
    cleaned = "\n".join(lines)
    return _BLANKS.sub("\n\n", cleaned).strip()


def content_hash(text: str) -> str:
    """Stable hash of the normalised text (case and whitespace insensitive)."""
    normalised = " ".join(text.lower().split())
    return hashlib.sha256(normalised.encode("utf-8")).hexdigest()


def words(text: str) -> list[str]:
    return _WORD.findall(text.lower())


def truncate_words(text: str, limit: int) -> str:
    """Keep the first ``limit`` words without flattening line breaks."""
    for i, match in enumerate(re.finditer(r"\S+", text)):
        if i == limit:
            return text[: match.start()].rstrip()
    return text


def word_count(text: str) -> int:
    return len(text.split())


def english_ratio(text: str) -> float:
    tokens = words(text[:20_000])
    if not tokens:
        return 0.0
    return sum(t in ENGLISH_STOPWORDS for t in tokens) / len(tokens)


def is_english(text: str, threshold: float = 0.08) -> bool:
    """Cheap language check: English prose has ~25-45% stopwords; terse technical text ~10%."""
    return english_ratio(text) >= threshold


def shingles(text: str, size: int = 5) -> set[str]:
    tokens = words(text)
    if len(tokens) < size:
        return {" ".join(tokens)} if tokens else set()
    return {" ".join(tokens[i : i + size]) for i in range(len(tokens) - size + 1)}


def jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


@dataclass
class Chunk:
    index: int
    text: str
    heading: str | None
    word_count: int


def _blocks(text: str) -> list[tuple[str | None, str]]:
    """Split into (heading, paragraph) blocks: headings and blank lines first."""
    heading: str | None = None
    blocks: list[tuple[str | None, str]] = []
    for para in re.split(r"\n\s*\n", text):
        para = para.strip()
        if not para:
            continue
        lines = para.split("\n")
        first = lines[0].strip()
        if len(first) <= 150 and _HEADING.match(first):  # a long "# ..." line is prose
            heading = lines[0].strip().strip("#= ").strip()
            lines = lines[1:]
            if not lines:
                continue
        blocks.append((heading, " ".join(line.strip() for line in lines)))
    return blocks


def chunk_text(text: str, size: int = 300, overlap: int = 40) -> list[Chunk]:
    """Pack paragraphs into ~``size``-word chunks with ``overlap`` words carried over.

    Paragraph and heading boundaries are respected where possible; a paragraph
    longer than ``size`` is split by words. Each chunk keeps its nearest heading.
    """
    if size <= 0 or overlap < 0 or overlap >= size:
        raise ValueError("need size > overlap >= 0")

    chunks: list[Chunk] = []
    current: list[str] = []
    fresh = 0  # words in ``current`` not already emitted in the previous chunk
    current_heading: str | None = None

    def flush(carry: bool) -> None:
        nonlocal current, fresh
        if fresh:
            chunks.append(Chunk(len(chunks), " ".join(current), current_heading, len(current)))
        current = current[-overlap:] if (carry and overlap) else []
        fresh = 0

    for heading, para in _blocks(text):
        tokens = para.split()
        if heading != current_heading:
            flush(carry=False)  # never carry text across a section change
            current_heading = heading
        while tokens:
            room = size - len(current)
            taken = tokens[:room]
            current.extend(taken)
            fresh += len(taken)
            tokens = tokens[room:]
            if len(current) >= size:
                flush(carry=True)

    flush(carry=False)
    return chunks
