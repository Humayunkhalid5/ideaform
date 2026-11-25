"""Platform adapters: ``select(url) -> Adapter`` with a shared ``extract`` contract.

Each adapter can rewrite the URL to a cleaner representation of the same page
(e.g. a GitHub repo to its raw README) and post-process the extracted text.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from urllib.parse import urlsplit

from app.services.knowledge.loaders import LoadedText, html_to_text, load_file


@dataclass
class Extracted:
    title: str
    text: str
    published_at: date | None
    publisher: str | None
    licence_note: str
    source_type: str


class Adapter:
    name = "generic"
    source_type = "web"
    licence_note = "Third-party web page: cite and link, do not republish"

    def matches(self, url: str) -> bool:
        return True

    def fetch_url(self, url: str) -> str:
        return url

    def publisher(self, url: str) -> str | None:
        host = urlsplit(url).hostname or ""
        return host.removeprefix("www.") or None

    def postprocess(self, text: str) -> str:
        return text

    def extract(self, url: str, body: bytes, content_type: str | None) -> Extracted | None:
        if content_type == "application/pdf" or url.lower().endswith(".pdf"):
            loaded: LoadedText | None = load_file(body, "page.pdf")
        elif content_type in ("text/plain", "text/markdown") or url.endswith((".md", ".txt")):
            loaded = load_file(body, "page.md")
        else:
            loaded = html_to_text(body.decode("utf-8", errors="replace"), url)
        if loaded is None:
            return None
        return Extracted(
            title=loaded.title,
            text=self.postprocess(loaded.text),
            published_at=loaded.published_at,
            publisher=self.publisher(url),
            licence_note=self.licence_note,
            source_type=self.source_type,
        )


class WikipediaAdapter(Adapter):
    name = "wikipedia"
    source_type = "wikipedia"
    licence_note = "CC BY-SA 4.0 (Wikipedia): attribute and link, share-alike"
    _TAIL = re.compile(r"\n(See also|References|External links|Further reading|Notes)\n.*", re.S)

    def matches(self, url: str) -> bool:
        return (urlsplit(url).hostname or "").endswith("wikipedia.org")

    def publisher(self, url: str) -> str | None:
        return "Wikipedia"

    def postprocess(self, text: str) -> str:
        return self._TAIL.sub("\n", text)


class GitHubAdapter(Adapter):
    """github.com/<owner>/<repo> pages are fetched as the raw README."""

    name = "github"
    source_type = "github"
    licence_note = "GitHub README: licence per repository, cite and link"
    _REPO = re.compile(r"^/([\w.-]+)/([\w.-]+)/?$")

    def matches(self, url: str) -> bool:
        parts = urlsplit(url)
        return parts.hostname in ("github.com", "www.github.com") and bool(
            self._REPO.match(parts.path)
        )

    def fetch_url(self, url: str) -> str:
        owner, repo = self._REPO.match(urlsplit(url).path).groups()
        return f"https://raw.githubusercontent.com/{owner}/{repo}/HEAD/README.md"

    def publisher(self, url: str) -> str | None:
        return "GitHub"


class DocsAdapter(Adapter):
    """Official documentation sites (KB-B)."""

    name = "docs"
    source_type = "docs"
    licence_note = "Official documentation: cite and link; licence per project"
    HOSTS = (
        "fastapi.tiangolo.com", "www.postgresql.org", "developer.mozilla.org",
        "nextjs.org", "docs.python.org", "docs.sqlalchemy.org", "react.dev",
        "docs.celeryq.dev", "redis.io", "12factor.net", "microservices.io",
        "learn.microsoft.com", "docs.docker.com", "kubernetes.io",
    )

    def matches(self, url: str) -> bool:
        return (urlsplit(url).hostname or "") in self.HOSTS


class ForumAdapter(Adapter):
    """Public forum/review pages: keep the discussion text, label it as opinion."""

    name = "forum"
    source_type = "forum"
    licence_note = "Public discussion: opinions, cite and link, do not republish threads"
    HOSTS = ("news.ycombinator.com", "www.reddit.com", "old.reddit.com", "stackoverflow.com",
             "www.producthunt.com", "www.g2.com", "www.capterra.com", "www.trustpilot.com")

    def matches(self, url: str) -> bool:
        return (urlsplit(url).hostname or "") in self.HOSTS


ADAPTERS: tuple[Adapter, ...] = (
    WikipediaAdapter(), GitHubAdapter(), DocsAdapter(), ForumAdapter(), Adapter()
)


def select(url: str) -> Adapter:
    return next(a for a in ADAPTERS if a.matches(url))
