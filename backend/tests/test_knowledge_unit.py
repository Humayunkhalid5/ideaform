"""White-box unit tests: text processing, RRF, keyword sanitising, isolation predicate,
robots guard, rate limiter, adapters (no database, no network)."""

from __future__ import annotations

import uuid

import pytest

from app.services.knowledge import text as T
from app.services.knowledge.embeddings import HashingEmbedder
from app.services.knowledge.retrieval import Filters, Scope, build_where, keyword_terms, rrf
from app.services.scrapers import adapters
from app.services.scrapers.guard import DomainRateLimiter, RobotsCache, host_blocked
from app.services.scrapers.quality import check_quality

# ------------------------------------------------------------------ text


def test_chunk_size_and_overlap():
    words = [f"w{i}" for i in range(1000)]
    chunks = T.chunk_text(" ".join(words), size=300, overlap=40)
    assert [c.word_count for c in chunks[:-1]] == [300] * (len(chunks) - 1)
    # consecutive chunks share exactly the 40-word overlap
    for a, b in zip(chunks, chunks[1:]):
        assert a.text.split()[-40:] == b.text.split()[:40]
    # every word appears, nothing invented
    covered = set(" ".join(c.text for c in chunks).split())
    assert covered == set(words)


def test_chunk_respects_headings_without_carrying_text_across():
    text = "# Intro\n\n" + " ".join(["alpha"] * 50) + "\n\n# Pricing\n\n" + " ".join(["beta"] * 50)
    chunks = T.chunk_text(text, size=300, overlap=40)
    assert [c.heading for c in chunks] == ["Intro", "Pricing"]
    assert "beta" not in chunks[0].text and "alpha" not in chunks[1].text


def test_chunk_short_text_and_bad_params():
    assert [c.text for c in T.chunk_text("just a few words", 300, 40)] == ["just a few words"]
    assert T.chunk_text("", 300, 40) == []
    with pytest.raises(ValueError):
        T.chunk_text("x", 40, 40)


def test_clean_text_drops_boilerplate_and_whitespace():
    raw = "We use cookies to improve your experience.\nReal   content here.\n\n\n\nMore."
    assert T.clean_text(raw) == "Real content here.\n\nMore."


def test_content_hash_ignores_case_and_spacing():
    assert T.content_hash("Hello   World") == T.content_hash("hello world")
    assert T.content_hash("hello world") != T.content_hash("hello there")


def test_english_check_and_near_duplicates():
    english = "The market for tutoring is growing because students want help with their exams."
    assert T.is_english(english)
    assert not T.is_english("Lorem ipsum dolor sit amet consectetur adipiscing elit sed do")
    a, b = T.shingles(english), T.shingles(english + " Really.")
    assert T.jaccard(a, b) > 0.8


def test_hashing_embedder_is_normalised_and_deterministic():
    emb = HashingEmbedder()
    v1, v2 = emb.embed(["solar gateway", "solar gateway"])
    assert v1 == v2 and len(v1) == 384
    assert abs(sum(x * x for x in v1) - 1.0) < 1e-6


# ------------------------------------------------------------------ retrieval internals


def test_rrf_matches_design_formula():
    fused = rrf([["a", "b", "c"], ["c", "a", "d"]], k=60)
    assert fused[0] == "a"  # 1/61 + 1/62 beats c's 1/63 + 1/61
    assert set(fused) == {"a", "b", "c", "d"}


def test_keyword_terms_are_sanitised():
    terms = keyword_terms("Solar-powered LoRa gateway'); DROP TABLE users; -- costs?")
    assert "drop" in terms and "table" in terms  # harmless words survive
    assert all(t.replace("-", "").isalpha() for t in terms)
    assert not any(ch in "".join(terms) for ch in ";()'|&!:")


def test_isolation_predicate_is_always_present():
    where, params = build_where(Scope(), Filters(kbs=["C"]))
    assert "c.kb IN ('A','B')" in where  # no scope: KB-C unreachable even if asked for
    uid, pid = uuid.uuid4(), uuid.uuid4()
    where, params = build_where(Scope(uid, pid), Filters())
    assert "c.user_id = :scope_user" in where and "c.project_id = :scope_project" in where
    assert params["scope_user"] == uid and params["scope_project"] == pid


# ------------------------------------------------------------------ guard


def _robots(body: str, status: int = 200):
    calls = []

    def fetch(url):
        calls.append(url)
        return status, body

    return RobotsCache("IdeaformBot/1.0", fetch=fetch), calls


def test_robots_disallow_and_crawl_delay():
    cache, calls = _robots("User-agent: *\nDisallow: /private\nCrawl-delay: 5\n")
    assert not cache.check("https://site.test/private/x").allowed
    ok = cache.check("https://site.test/public")
    assert ok.allowed and ok.crawl_delay == 5.0
    assert calls == ["https://site.test/robots.txt"]  # cached per domain


def test_robots_status_codes():
    assert _robots("", 404)[0].check("https://a.test/x").allowed
    assert not _robots("", 403)[0].check("https://a.test/x").allowed
    assert not _robots("", 503)[0].check("https://a.test/x").allowed


def test_robots_unreachable_is_conservative():
    def boom(url):
        raise OSError("dns")

    assert not RobotsCache("UA", fetch=boom).check("https://a.test/x").allowed


def test_terms_policy_blocks_search_engines_and_social():
    for host in ("www.google.com", "google.co.uk", "www.linkedin.com", "x.com", "bing.com"):
        assert host_blocked(host), host
    for host in ("box.com", "en.wikipedia.org", "abing.com"):
        assert not host_blocked(host), host
    cache, calls = _robots("")
    assert cache.check("https://www.google.com/search?q=x").reason == "host excluded by terms policy"
    assert calls == []  # not even robots.txt is requested
    assert not cache.check("ftp://files.test/x").allowed


def test_rate_limiter_spaces_requests_per_domain():
    now = [0.0]
    slept = []
    limiter = DomainRateLimiter(2.0, clock=lambda: now[0], sleep=lambda s: slept.append(s))
    assert limiter.wait("a.test") == 0
    assert limiter.wait("a.test") == 2.0  # second hit waits the delay
    assert limiter.wait("b.test") == 0  # other domains are independent
    assert limiter.wait("a.test", crawl_delay=10) == 4.0  # queued behind the previous slot
    assert slept == [2.0, 4.0]


# ------------------------------------------------------------------ adapters and quality


def test_adapter_selection_and_github_rewrite():
    assert adapters.select("https://en.wikipedia.org/wiki/LoRa").name == "wikipedia"
    gh = adapters.select("https://github.com/fastapi/fastapi")
    assert gh.name == "github"
    assert gh.fetch_url("https://github.com/fastapi/fastapi") == (
        "https://raw.githubusercontent.com/fastapi/fastapi/HEAD/README.md"
    )
    assert adapters.select("https://github.com/fastapi/fastapi/issues/1").name == "generic"
    assert adapters.select("https://12factor.net/config").name == "docs"
    assert adapters.select("https://news.ycombinator.com/item?id=1").name == "forum"


def test_generic_adapter_extracts_main_text():
    html = (
        "<html><head><title>Water leak sensors</title></head><body><nav>Home | About</nav>"
        "<article><h1>Water leak sensors</h1>"
        + "".join(
            f"<p>Paragraph {i}: LoRa leak sensors report pressure drops in apartment risers "
            "to a solar gateway, which alerts the building manager within seconds.</p>"
            for i in range(12)
        )
        + "</article><footer>Cookie policy</footer></body></html>"
    )
    out = adapters.select("https://blog.test/leaks").extract("https://blog.test/leaks", html.encode(), "text/html")
    assert out is not None and "solar gateway" in out.text and "Home | About" not in out.text
    assert out.licence_note and out.source_type == "web"


def test_quality_filter():
    good = " ".join(["The solar gateway forwards leak alerts to the manager."] * 30)
    assert check_quality(good, raw_size=5000, min_words=50) is None
    assert "too short" in check_quality("short text", raw_size=100, min_words=50)
    assert check_quality(good, raw_size=5000, min_words=50, topic_terms=["tutor"]).startswith("off-topic")
    assert check_quality(good, raw_size=5000, min_words=50, topic_terms=["gateway"]) is None


# ------------------------------------------------------------------ loaders


def test_markdown_front_matter_gives_title_and_is_stripped():
    from app.services.knowledge.loaders import load_file

    md = b"---\ntitle: Idea validation framework\nkb: A\n---\n# Idea validation framework\n\nBody text here."
    loaded = load_file(md, "01_notes.md")
    assert loaded.title == "Idea validation framework"
    assert "kb: A" not in loaded.text and loaded.text.lstrip().startswith("# Idea validation")


def test_truncate_words_keeps_line_breaks():
    text = "# Heading\n\npara one two three\n\npara four five"
    assert T.truncate_words(text, 4) == "# Heading\n\npara one"
    assert T.truncate_words(text, 100) == text


def test_long_first_line_is_not_a_heading():
    line = "# " + " ".join(["word"] * 200)
    chunks = T.chunk_text(line, size=300, overlap=40)
    assert chunks and chunks[0].heading is None
