"""Research Agent, Tavily discovery (cache, cap, fallback) and crawl compliance."""

from __future__ import annotations

import json

import httpx
import pytest
from sqlalchemy import select

from app.config import get_settings
from app.models.scrape import CrawlPage, ScrapeJob
from app.models.search import SearchCache, SearchUsage
from app.services.research import discovery
from app.services.research.discovery import SearchHit, TavilyProvider
from app.services.scrapers.crawler import Crawler, CrawlTarget
from app.services.scrapers.fetcher import FetchResult
from app.services.scrapers.guard import Decision

PAGE = (
    "<html><head><title>{title}</title></head><body><article><h1>{title}</h1>"
    + "".join(
        f"<p>Paragraph {i} about {{topic}}: university students compare affordable tutors, "
        "read verified reviews and book sessions; marketplaces charge tutors a commission.</p>"
        for i in range(15)
    )
    + "</article></body></html>"
)


class FakeRobots:
    def __init__(self, disallowed=()):
        self.disallowed = set(disallowed)

    def check(self, url):
        if url in self.disallowed:
            return Decision(False, "disallowed by robots.txt")
        return Decision(True)


class FakeFetcher:
    def __init__(self, pages):
        self.pages = pages
        self.calls = []

    def __call__(self, url):
        self.calls.append(url)
        if url not in self.pages:
            return FetchResult(url=url, status=404, error="HTTP 404")
        return FetchResult(url=url, final_url=url, status=200, content_type="text/html",
                           body=self.pages[url].encode(), fetch_ms=5)


class FakeProvider:
    name = "fake"

    def __init__(self, urls):
        self.urls = urls
        self.queries = []

    def search(self, db, query, *, max_results, category=None):
        self.queries.append(query)
        return [SearchHit(url=u, title=u, origin="tavily") for u in self.urls]


def _page(title, topic="tutoring"):
    return PAGE.format(title=title, topic=topic).replace("{topic}", topic)


# ------------------------------------------------------------------ crawl compliance


def _crawler(db, project_row, robots, fetcher, **kw):
    job = ScrapeJob(project_id=project_row.id, adapter="test", status="queued")
    db.add(job)
    db.flush()
    return Crawler(db, job, kb="C", user_id=project_row.user_id, project_id=project_row.id,
                   robots=robots, fetcher=fetcher, **kw), job


@pytest.fixture
def project_row(db_session, project):
    from app.models.project import Project

    return db_session.get(Project, project["id"])


def test_robots_blocked_urls_are_never_fetched(db_session, project_row):
    allowed, blocked = "https://ok.test/a", "https://blocked.test/b"
    fetcher = FakeFetcher({allowed: _page("Tutor market"), blocked: _page("Secret")})
    crawler, job = _crawler(db_session, project_row, FakeRobots([blocked]), fetcher)
    stats = crawler.crawl([CrawlTarget(blocked), CrawlTarget(allowed)])
    db_session.commit()

    assert fetcher.calls == [allowed]  # zero fetches against a disallow
    assert stats.skipped_robots == 1 and stats.stored == 1
    pages = {p.url: p for p in db_session.scalars(select(CrawlPage).where(CrawlPage.job_id == job.id))}
    assert pages[blocked].robots_allowed is False and pages[blocked].skip_reason == "disallowed by robots.txt"
    assert pages[blocked].http_status is None
    ok = pages[allowed]
    assert ok.robots_allowed and ok.http_status == 200 and ok.content_hash and ok.source_id
    assert job.pages_skipped_robots == 1 and job.pages_fetched == 1


def test_crawler_rejects_bad_pages_and_logs_reasons(db_session, project_row):
    pages = {
        "https://a.test/short": "<html><body><p>Too short.</p></body></html>",
        "https://a.test/one": _page("Tutors one"),
        "https://a.test/two": _page("Tutors one").replace("Paragraph", "Paragraph"),  # near-dup same domain
        "https://b.test/offtopic": _page("Cats", topic="cats").replace("students", "cats")
        .replace("tutors", "kittens").replace("tutor", "kitten"),
    }
    fetcher = FakeFetcher(pages)
    crawler, job = _crawler(db_session, project_row, FakeRobots(), fetcher,
                            topic_terms=["tutors", "students"])
    crawler.min_words = 50
    stats = crawler.crawl([CrawlTarget(u) for u in list(pages) + ["https://a.test/missing"]])
    db_session.commit()
    reasons = {p.url: p.skip_reason for p in db_session.scalars(select(CrawlPage).where(CrawlPage.job_id == job.id))}
    assert reasons["https://a.test/one"] is None
    assert reasons["https://a.test/short"] in ("no main text",) or reasons["https://a.test/short"].startswith("too short")
    assert reasons["https://a.test/two"] in ("near-duplicate of another page on this domain", "duplicate content")
    assert reasons["https://b.test/offtopic"].startswith("off-topic")
    assert reasons["https://a.test/missing"] == "fetch failed"
    assert stats.stored == 1


def test_crawler_respects_page_cap(db_session, project_row, monkeypatch):
    urls = [f"https://p{i}.test/x" for i in range(5)]
    fetcher = FakeFetcher({u: _page(f"Tutors {i}") for i, u in enumerate(urls)})
    crawler, _ = _crawler(db_session, project_row, FakeRobots(), fetcher)
    crawler.max_pages = 2
    crawler.crawl([CrawlTarget(u) for u in urls])
    assert len(fetcher.calls) == 2


# ------------------------------------------------------------------ Tavily discovery


def _transport(responses, calls):
    def handler(request: httpx.Request):
        calls.append(json.loads(request.content))
        status, body = responses.pop(0) if responses else (200, {"results": []})
        return httpx.Response(status, json=body)

    return httpx.MockTransport(handler)


@pytest.fixture
def tavily_key(monkeypatch):
    monkeypatch.setattr(get_settings(), "tavily_api_key", "tvly-test-key-123")


def test_tavily_success_is_cached_and_counted(db_session, tavily_key):
    calls = []
    body = {"results": [{"url": "https://a.test/1", "title": "A", "content": "snippet", "score": 0.9}]}
    provider = TavilyProvider(transport=_transport([(200, body)], calls))
    hits = provider.search(db_session, "tutor marketplace competitors", max_results=5)
    assert [h.url for h in hits] == ["https://a.test/1"] and hits[0].origin == "tavily"
    assert calls[0]["search_depth"] == "basic" and calls[0]["include_raw_content"] is False
    again = provider.search(db_session, "Tutor   marketplace COMPETITORS", max_results=5)
    assert len(calls) == 1 and again[0].origin == "cache"  # normalised query hits the cache
    assert discovery.credits_used_today(db_session) == 1


def test_tavily_daily_cap_uses_fallbacks(db_session, tavily_key, monkeypatch):
    monkeypatch.setattr(get_settings(), "tavily_daily_credit_cap", 0)
    calls = []
    provider = TavilyProvider(transport=_transport([], calls))
    hits = provider.search(db_session, "laundry pickup app", max_results=5, category="business")
    assert calls == []  # no paid call over the cap
    assert hits and all(h.origin == "seed" for h in hits)


def test_tavily_failure_falls_back_to_stale_cache_then_seeds(db_session, tavily_key, monkeypatch):
    monkeypatch.setattr(get_settings(), "tavily_cache_ttl_hours", 0)  # everything is stale
    calls = []
    provider = TavilyProvider(transport=_transport(
        [(200, {"results": [{"url": "https://old.test", "title": "Old"}]}), (401, {"detail": "bad key"})], calls))
    provider.search(db_session, "clinic scheduling software", max_results=5)
    stale = provider.search(db_session, "clinic scheduling software", max_results=5)
    assert [h.origin for h in stale] == ["stale-cache"] and stale[0].url == "https://old.test"

    seeds = TavilyProvider(transport=_transport([(432, {})], [])).search(
        db_session, "never searched before", max_results=3, category="technology")
    assert seeds and all(h.origin == "seed" for h in seeds)


def test_tavily_without_key_never_calls_out(db_session, monkeypatch):
    monkeypatch.setattr(get_settings(), "tavily_api_key", None)
    calls = []
    hits = TavilyProvider(transport=_transport([], calls)).search(db_session, "x y z", max_results=3)
    assert calls == [] and all(h.origin == "seed" for h in hits)


# ------------------------------------------------------------------ Research Agent end to end


def test_research_endpoint_end_to_end(client, auth, project, fake_llm, monkeypatch, db_session):
    pid = project["id"]
    client.post(f"/projects/{pid}/understand", headers=auth)

    urls = ["https://tutors.test/market", "https://reviews.test/tutors", "https://blocked.test/x"]
    fetcher = FakeFetcher({urls[0]: _page("Tutor market size"), urls[1]: _page("Tutor reviews compared")})
    provider = FakeProvider(urls)

    from app.services.research import agent

    monkeypatch.setattr(agent, "get_search_provider", lambda: provider)

    def factory(*args, **kwargs):
        return Crawler(*args, robots=FakeRobots([urls[2]]), fetcher=fetcher, **kwargs)

    real = agent.run_research
    monkeypatch.setattr(agent, "run_research",
                        lambda *a, **k: real(*a, crawler_factory=factory, **k))

    r = client.post(f"/projects/{pid}/research", json={"queries": ["peer tutoring apps"]}, headers=auth)
    assert r.status_code == 202, r.text
    run = client.get(f"/runs/{r.json()['run_id']}", headers=auth).json()
    assert run["status"] == "succeeded" and run["agent_name"] == "research"

    # planner fell back to templates (no LLM key) and the user query came first
    assert provider.queries[0] == "peer tutoring apps"
    assert 4 <= len(provider.queries) <= 9

    sources = client.get(f"/projects/{pid}/sources", headers=auth).json()
    assert {s["url"] for s in sources} == set(urls[:2])
    assert all(s["kb"] == "C" and s["licence_note"] and s["retrieved_at"] for s in sources)

    jobs = client.get(f"/projects/{pid}/crawl", headers=auth).json()
    assert jobs[0]["pages_skipped_robots"] == 1 and jobs[0]["status"] == "succeeded"
    blocked = next(p for p in jobs[0]["pages"] if p["url"] == urls[2])
    assert blocked["robots_allowed"] is False and urls[2] not in fetcher.calls

    hits = client.post(f"/projects/{pid}/search", json={"query": "affordable tutors verified reviews"},
                       headers=auth).json()["passages"]
    assert hits and hits[0]["kb"] == "C" and hits[0]["url"] in urls

    detail = client.get(f"/projects/{pid}", headers=auth).json()
    assert detail["status"] == "ready"


def test_research_validation_and_ownership(client, auth, other_auth, project):
    pid = project["id"]
    bad = client.post(f"/projects/{pid}/research", json={"urls": ["not a url"]}, headers=auth)
    assert bad.status_code == 422
    assert client.post(f"/projects/{pid}/research", headers=other_auth).status_code == 404
    assert client.get(f"/projects/{pid}/crawl", headers=other_auth).status_code == 404


def test_research_respects_token_quota(client, auth, project, fake_llm, db_session):
    from app.models.user import User

    user = db_session.scalar(select(User))
    user.daily_token_limit = 1
    db_session.commit()
    client.post(f"/projects/{project['id']}/understand", headers=auth)  # spends > 1 token
    assert client.post(f"/projects/{project['id']}/research", headers=auth).status_code == 429


def test_search_cache_tables_exist(db_session):
    assert db_session.scalar(select(SearchCache).limit(1)) is None
    assert db_session.scalar(select(SearchUsage).limit(1)) is None
