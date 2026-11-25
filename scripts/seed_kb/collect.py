"""Collect seed documents for KB-A (business) and KB-B (technical).

One adapter per source (AI_DESIGN 3.7). Structured sources are read through their
documented APIs; web pages go through the same robots.txt/rate-limit guard and
trafilatura extraction as live research. Output: JSON Lines per source in
``data/scraped_corpus/kb_seed/`` (git-ignored). Load them with ``ingest.py``.

    backend/.venv/Scripts/python scripts/seed_kb/collect.py                 # all sources
    backend/.venv/Scripts/python scripts/seed_kb/collect.py --only wikipedia arxiv

Sources: Wikipedia, World Bank, arXiv, Hacker News, GitHub, documentation sites,
architecture guides, GLEIF, and SEC EDGAR (only when SEC_CONTACT_EMAIL is set).
"""

from __future__ import annotations

import argparse
import re
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import doc, use_backend, write_jsonl  # noqa: E402

use_backend()

import httpx  # noqa: E402

from app.config import get_settings  # noqa: E402
from app.services.knowledge.text import truncate_words  # noqa: E402
from app.services.scrapers import adapters  # noqa: E402
from app.services.scrapers.fetcher import fetch  # noqa: E402
from app.services.scrapers.guard import DomainRateLimiter, RobotsCache, domain_of  # noqa: E402

USER_AGENT = get_settings().crawler_user_agent
CLIENT = httpx.Client(timeout=30, follow_redirects=True, headers={"User-Agent": USER_AGENT})
LIMITER = DomainRateLimiter(1.5)


def get_json(url: str, params: dict | None = None, delay_domain: str | None = None) -> dict | list:
    LIMITER.wait(delay_domain or domain_of(url))
    for attempt in range(5):
        resp = CLIENT.get(url, params=params)
        if resp.status_code == 200:
            return resp.json()
        if resp.status_code in (429, 500, 502, 503) and attempt < 4:
            wait = resp.headers.get("retry-after")
            time.sleep(float(wait) if wait and wait.isdigit() else 5 * (attempt + 1))
            continue
        resp.raise_for_status()
    return {}


# --------------------------------------------------------------------------- Wikipedia

WIKI_TOPICS = {
    # KB-A business intelligence
    ("A", "business"): [
        "Business model", "Business model canvas", "Lean startup", "Startup company",
        "Minimum viable product", "Product-market fit", "Venture capital", "Seed money",
        "Angel investor", "Crowdfunding", "Bootstrapping", "Unit economics",
        "Customer acquisition cost", "Customer lifetime value", "Churn rate",
        "Subscription business model", "Freemium", "Two-sided market", "Network effect",
        "Platform economy", "Sharing economy", "Gig economy", "Marketplace",
        "Market segmentation", "Total addressable market", "Competitive advantage",
        "Porter's five forces analysis", "SWOT analysis", "Blue Ocean Strategy",
        "Pricing strategies", "Price discrimination", "Go-to-market strategy",
        "E-commerce", "Online food ordering", "Laundry", "Coworking", "Meal kit",
        "Tutoring", "Online tutoring", "Microfinance", "Mobile payment",
        "Economy of Pakistan", "Startup ecosystem", "Failure of startups",
        "Business plan", "Value proposition", "Customer development",
    ],
    # KB-B technical intelligence
    ("B", "technology"): [
        "Internet of things", "LoRa", "LPWAN", "Wireless sensor network", "Leak detection",
        "Solar power", "Edge computing", "Computer vision", "Object detection",
        "People counter", "Closed-circuit television", "Speech recognition",
        "Urdu", "On-device machine learning", "Quantization (signal processing)",
        "Federated learning", "Differential privacy", "Large language model",
        "Retrieval-augmented generation", "Recommender system",
    ],
    ("B", "software"): [
        "Software as a service", "Mobile app", "Progressive web app", "Web application",
        "Microservices", "Service-oriented architecture", "Representational state transfer",
        "OAuth", "JSON Web Token", "PostgreSQL", "Database normalization",
        "Electronic health record", "Appointment scheduling software",
        "Browser extension", "Time tracking software", "Role-based access control",
        "Continuous integration", "Twelve-Factor App methodology", "Scalability",
        "Software architecture", "Event-driven architecture",
    ],
}

_WIKI_TAIL = re.compile(r"\n== (See also|References|External links|Further reading|Notes|Bibliography) ==.*", re.S)


def collect_wikipedia() -> list[dict]:
    if not get_settings().scraper_contact:
        # Wikimedia's User-Agent policy requires contact details and answers 403 without them
        print("  wikipedia: skipped (set SCRAPER_CONTACT in .env to an email or URL)")
        return []
    out = []
    for (kb, category), titles in WIKI_TOPICS.items():
        for title in titles:
            data = get_json(
                "https://en.wikipedia.org/w/api.php",
                {
                    "action": "query", "prop": "extracts|info|revisions", "explaintext": 1,
                    "inprop": "url", "rvprop": "timestamp", "titles": title, "redirects": 1,
                    "format": "json", "formatversion": 2,
                },
                "en.wikipedia.org",
            )
            pages = (data.get("query") or {}).get("pages") or []
            if not pages or pages[0].get("missing"):
                print(f"  wikipedia: missing {title!r}")
                continue
            page = pages[0]
            text = _WIKI_TAIL.sub("", page.get("extract") or "")
            if len(text.split()) < 80:
                continue
            text = truncate_words(text, 3500)
            stamp = ((page.get("revisions") or [{}])[0].get("timestamp") or "")[:10] or None
            out.append(doc(
                title=page["title"], text=text, url=page.get("fullurl"), kb=kb,
                source_type="wikipedia", publisher="Wikipedia", published_at=stamp,
                licence_note="CC BY-SA 4.0 (Wikipedia): attribute and link, share-alike",
                attribution=f"Wikipedia contributors, \"{page['title']}\"", category=category,
                adapter="wikipedia",
            ))
    return out


# --------------------------------------------------------------------------- World Bank

WB_INDICATORS = {
    "NY.GDP.MKTP.CD": "GDP (current US$)",
    "NY.GDP.PCAP.CD": "GDP per capita (current US$)",
    "SP.POP.TOTL": "Population, total",
    "SP.URB.TOTL.IN.ZS": "Urban population (% of total population)",
    "IT.NET.USER.ZS": "Individuals using the Internet (% of population)",
    "IT.CEL.SETS.P2": "Mobile cellular subscriptions (per 100 people)",
    "SE.TER.ENRR": "School enrollment, tertiary (% gross)",
    "IC.BUS.NREG": "New businesses registered (number)",
    "SL.UEM.1524.ZS": "Youth unemployment (% of labor force ages 15-24)",
    "FX.OWN.TOTL.ZS": "Account ownership at a financial institution or mobile-money provider (% of age 15+)",
    "EG.ELC.ACCS.ZS": "Access to electricity (% of population)",
    "ER.H2O.FWTL.ZS": "Annual freshwater withdrawals, total (% of internal resources)",
}
WB_COUNTRIES = "PAK;IND;BGD;USA;GBR;ARE;WLD"


def collect_worldbank() -> list[dict]:
    out = []
    for code, name in WB_INDICATORS.items():
        LIMITER.wait("api.worldbank.org", 4.0)  # the API throttles bursts with 429
        try:
            data = get_json(
                f"https://api.worldbank.org/v2/country/{WB_COUNTRIES}/indicator/{code}",
                {"format": "json", "date": "2014:2024", "per_page": 500},
            )
        except httpx.HTTPError as exc:
            print(f"  worldbank: skipped {code} ({exc.__class__.__name__})")
            continue
        if not isinstance(data, list) or len(data) < 2 or not data[1]:
            continue
        by_country: dict[str, list[tuple[str, float]]] = {}
        for row in data[1]:
            if row.get("value") is not None:
                by_country.setdefault(row["country"]["value"], []).append((row["date"], row["value"]))
        lines = [f"{name} (World Bank indicator {code}), 2014-2024."]
        for country, series in sorted(by_country.items()):
            series.sort()
            first, last = series[0], series[-1]
            change = ((last[1] - first[1]) / first[1] * 100) if first[1] else 0
            values = "; ".join(f"{y}: {v:,.2f}" for y, v in series)
            lines.append(
                f"{country}: latest {last[1]:,.2f} in {last[0]}, {change:+.1f}% versus {first[0]}. "
                f"Series: {values}."
            )
        out.append(doc(
            title=f"World Bank: {name}", text="\n\n".join(lines),
            url=f"https://data.worldbank.org/indicator/{code}", kb="A",
            source_type="worldbank", publisher="World Bank Open Data",
            licence_note="CC BY 4.0 (World Bank Open Data): attribution required",
            attribution="The World Bank, World Development Indicators", category="business",
            adapter="worldbank",
        ))
    return out


# --------------------------------------------------------------------------- arXiv

ARXIV_TOPICS = {
    ("B", "technology"): [
        "LoRa water leak detection sensor network", "people counting CCTV privacy",
        "on-device speech recognition low resource language", "edge AI model quantization mobile",
        "retrieval augmented generation evaluation", "hybrid search BM25 dense retrieval fusion",
    ],
    ("B", "software"): ["microservices architecture migration", "recommender system tutoring"],
    ("A", "business"): ["startup success prediction", "two-sided marketplace platform economics"],
}
ATOM = "{http://www.w3.org/2005/Atom}"


def collect_arxiv(per_topic: int = 4) -> list[dict]:
    out = []
    for (kb, category), topics in ARXIV_TOPICS.items():
        for topic in topics:
            LIMITER.wait("export.arxiv.org", 3.0)  # arXiv API terms: one request per 3 s
            resp = CLIENT.get(
                "https://export.arxiv.org/api/query",
                params={"search_query": f"all:{topic}", "max_results": per_topic, "sortBy": "relevance"},
            )
            if resp.status_code != 200:
                continue
            for entry in ET.fromstring(resp.text).findall(f"{ATOM}entry"):
                title = " ".join((entry.findtext(f"{ATOM}title") or "").split())
                summary = " ".join((entry.findtext(f"{ATOM}summary") or "").split())
                url = entry.findtext(f"{ATOM}id")
                authors = [a.findtext(f"{ATOM}name") for a in entry.findall(f"{ATOM}author")]
                published = (entry.findtext(f"{ATOM}published") or "")[:10] or None
                if len(summary.split()) < 60:
                    continue
                out.append(doc(
                    title=title, text=f"{title}\n\nAbstract: {summary}", url=url, kb=kb,
                    source_type="arxiv", publisher="arXiv", published_at=published,
                    licence_note="arXiv metadata and abstract (CC0 metadata); full text per paper licence",
                    attribution=f"{', '.join(a for a in authors[:3] if a)}{' et al.' if len(authors) > 3 else ''}, arXiv",
                    category=category, adapter="arxiv",
                ))
    return out


# --------------------------------------------------------------------------- Hacker News

HN_QUERIES = [
    "startup post-mortem", "why my startup failed", "lessons from shutting down",
    "Show HN marketplace", "Ask HN pricing SaaS", "Ask HN first customers",
    "tutoring startup", "IoT startup hardware", "clinic software", "laundry startup",
]
_TAGS = re.compile(r"<[^>]+>")


def collect_hackernews(per_query: int = 5) -> list[dict]:
    out, seen = [], set()
    import html as htmllib

    for q in HN_QUERIES:
        data = get_json(
            "https://hn.algolia.com/api/v1/search",
            {"query": q, "tags": "(story,ask_hn,show_hn)", "hitsPerPage": 20},
        )
        taken = 0
        for hit in data.get("hits", []):
            text = htmllib.unescape(_TAGS.sub(" ", hit.get("story_text") or ""))
            if hit["objectID"] in seen or len(text.split()) < 80:
                continue
            seen.add(hit["objectID"])
            url = f"https://news.ycombinator.com/item?id={hit['objectID']}"
            out.append(doc(
                title=hit.get("title") or q, text=f"{hit.get('title')}\n\n{text}", url=url, kb="A",
                source_type="hackernews", publisher="Hacker News",
                published_at=(hit.get("created_at") or "")[:10] or None,
                licence_note="Hacker News public API: cite and link, do not republish threads",
                attribution=f"{hit.get('author') or 'HN user'} on Hacker News", category="business",
                adapter="hackernews",
            ))
            taken += 1
            if taken >= per_query:
                break
    return out


# --------------------------------------------------------------------------- GitHub

GITHUB_REPOS = [
    ("fastapi/fastapi", "software"), ("tiangolo/full-stack-fastapi-template", "software"),
    ("vercel/next.js", "software"), ("pgvector/pgvector", "software"),
    ("celery/celery", "software"), ("supabase/supabase", "software"),
    ("calcom/cal.com", "software"), ("openemr/openemr", "software"),
    ("mattermost/mattermost", "software"), ("medusajs/medusa", "software"),
    ("saleor/saleor", "software"), ("chatwoot/chatwoot", "software"),
    ("RocketChat/Rocket.Chat", "software"), ("ActivityWatch/activitywatch", "software"),
    ("home-assistant/core", "technology"),
    ("TheThingsNetwork/lorawan-stack", "technology"), ("openai/whisper", "technology"),
    ("ultralytics/ultralytics", "technology"), ("deepinsight/insightface", "technology"),
    ("UKPLab/sentence-transformers", "technology"), ("langchain-ai/langchain", "technology"),
    ("run-llama/llama_index", "technology"), ("chroma-core/chroma", "technology"),
    ("adbar/trafilatura", "technology"),
]


def collect_github() -> list[dict]:
    out = []
    for repo, category in GITHUB_REPOS:
        try:
            meta = get_json(f"https://api.github.com/repos/{repo}", delay_domain="api.github.com")
        except httpx.HTTPError:
            continue
        if not isinstance(meta, dict) or not meta.get("full_name"):
            continue
        branch = meta.get("default_branch") or "main"
        LIMITER.wait("raw.githubusercontent.com")
        resp = CLIENT.get(f"https://raw.githubusercontent.com/{meta['full_name']}/{branch}/README.md")
        if resp.status_code != 200 or len(resp.text.split()) < 80:
            continue
        text = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", resp.text)  # drop images/badges
        text = re.sub(r"<[^>]+>", " ", text)
        text = truncate_words(text, 4000)
        licence = ((meta.get("license") or {}).get("spdx_id")) or "unspecified"
        out.append(doc(
            title=f"{meta['full_name']}: {meta.get('description') or 'README'}"[:300],
            text=text, url=meta["html_url"], kb="B", source_type="github", publisher="GitHub",
            published_at=(meta.get("pushed_at") or "")[:10] or None,
            licence_note=f"Repository licence: {licence}; README cited and linked",
            attribution=f"{meta['full_name']} contributors (GitHub)", category=category,
            adapter="github",
        ))
    return out


# --------------------------------------------------------------------------- docs and architecture guides

DOC_PAGES = [
    ("https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/", "software"),
    ("https://fastapi.tiangolo.com/tutorial/sql-databases/", "software"),
    ("https://fastapi.tiangolo.com/tutorial/background-tasks/", "software"),
    ("https://fastapi.tiangolo.com/deployment/concepts/", "software"),
    ("https://www.postgresql.org/docs/current/textsearch-intro.html", "software"),
    ("https://www.postgresql.org/docs/current/ddl-constraints.html", "software"),
    ("https://www.postgresql.org/docs/current/indexes-types.html", "software"),
    ("https://www.postgresql.org/docs/current/ddl-rowsecurity.html", "software"),
    ("https://developer.mozilla.org/en-US/docs/Web/HTTP/Guides/Caching", "software"),
    ("https://developer.mozilla.org/en-US/docs/Web/HTTP/Guides/CORS", "software"),
    ("https://developer.mozilla.org/en-US/docs/Web/HTTP/Guides/Authentication", "software"),
    ("https://developer.mozilla.org/en-US/docs/Web/Progressive_web_apps", "software"),
    ("https://developer.mozilla.org/en-US/docs/Mozilla/Add-ons/WebExtensions/What_are_WebExtensions", "software"),
    ("https://nextjs.org/docs/app/getting-started/layouts-and-pages", "software"),
    ("https://nextjs.org/docs/app/guides/authentication", "software"),
    ("https://docs.celeryq.dev/en/stable/getting-started/introduction.html", "software"),
    ("https://redis.io/docs/latest/develop/get-started/", "software"),
    ("https://docs.docker.com/get-started/docker-overview/", "software"),
    ("https://12factor.net/", "software"),
    ("https://12factor.net/config", "software"),
    ("https://12factor.net/backing-services", "software"),
    ("https://12factor.net/processes", "software"),
    ("https://microservices.io/patterns/microservices.html", "software"),
    ("https://microservices.io/patterns/monolithic.html", "software"),
    ("https://microservices.io/patterns/data/database-per-service.html", "software"),
    ("https://microservices.io/patterns/apigateway.html", "software"),
    ("https://learn.microsoft.com/en-us/azure/architecture/guide/architecture-styles/", "software"),
    ("https://learn.microsoft.com/en-us/azure/architecture/patterns/cqrs", "software"),
    ("https://learn.microsoft.com/en-us/azure/architecture/best-practices/api-design", "software"),
    ("https://learn.microsoft.com/en-us/azure/architecture/patterns/retry", "software"),
]


def collect_docs() -> list[dict]:
    settings = get_settings()
    robots = RobotsCache(settings.scraper_user_agent)
    limiter = DomainRateLimiter(settings.scraper_min_delay_seconds)
    out = []
    for url, category in DOC_PAGES:
        decision = robots.check(url)
        if not decision.allowed:
            print(f"  docs: skipped {url} ({decision.reason})")
            continue
        limiter.wait(domain_of(url), decision.crawl_delay)
        result = fetch(url)
        if not result.ok:
            print(f"  docs: failed {url} ({result.error})")
            continue
        adapter = adapters.select(url)
        extracted = adapter.extract(url, result.body, result.content_type)
        if extracted is None or len(extracted.text.split()) < 120:
            continue
        host = domain_of(url)
        out.append(doc(
            title=extracted.title, text=extracted.text, url=result.final_url or url, kb="B",
            source_type="docs" if adapter.name == "docs" else "web", publisher=extracted.publisher or host,
            published_at=str(extracted.published_at) if extracted.published_at else None,
            licence_note=f"{extracted.licence_note} (robots.txt allowed)",
            attribution=f"{host} documentation", category=category, adapter=adapter.name,
        ))
    return out


# --------------------------------------------------------------------------- GLEIF and SEC EDGAR

GLEIF_NAMES = ["Careem", "Daraz", "Airbnb", "Uber Technologies", "Shopify", "Chegg", "Coursera", "Upwork"]


def collect_gleif() -> list[dict]:
    out = []
    for name in GLEIF_NAMES:
        data = get_json(
            "https://api.gleif.org/api/v1/lei-records",
            {"filter[entity.legalName]": name, "page[size]": 1},
        )
        for rec in (data.get("data") or [])[:1]:
            attrs = rec.get("attributes", {})
            ent = attrs.get("entity", {})
            addr = ent.get("legalAddress", {})
            text = (
                f"Legal entity record for {ent.get('legalName', {}).get('name')} (LEI {attrs.get('lei')}). "
                f"Status: {ent.get('status')}. Legal form: {(ent.get('legalForm') or {}).get('id')}. "
                f"Jurisdiction: {ent.get('jurisdiction')}. Legal address: {', '.join(addr.get('addressLines') or [])}, "
                f"{addr.get('city')}, {addr.get('country')}. Registration status: "
                f"{(attrs.get('registration') or {}).get('status')}, initial registration "
                f"{(attrs.get('registration') or {}).get('initialRegistrationDate', '')[:10]}, "
                f"last update {(attrs.get('registration') or {}).get('lastUpdateDate', '')[:10]}. "
                f"This record identifies the company as a legal entity in the Global LEI System and "
                f"can be used to confirm a competitor's legal name, home country and registration status."
            )
            out.append(doc(
                title=f"GLEIF LEI record: {ent.get('legalName', {}).get('name')}", text=text,
                url=f"https://search.gleif.org/#/record/{attrs.get('lei')}", kb="A",
                source_type="gleif", publisher="GLEIF",
                licence_note="GLEIF open data (CC0): keep source attribution",
                attribution="Global Legal Entity Identifier Foundation (GLEIF)",
                category="business", adapter="gleif",
            ))
    return out


def collect_edgar() -> list[dict]:
    contact = get_settings().sec_contact_email
    if not contact:
        print("  edgar: skipped (set SEC_CONTACT_EMAIL in .env; SEC requires a real contact)")
        return []
    headers = {"User-Agent": f"Ideaform research {contact}"}
    out = []
    for cik, name in [("0001559720", "Airbnb"), ("0001543151", "Uber"), ("0001364954", "Chegg")]:
        LIMITER.wait("data.sec.gov", 0.2)
        resp = CLIENT.get(f"https://data.sec.gov/submissions/CIK{cik}.json", headers=headers)
        if resp.status_code != 200:
            continue
        data = resp.json()
        recent = data.get("filings", {}).get("recent", {})
        forms = list(zip(recent.get("form", [])[:15], recent.get("filingDate", [])[:15]))
        text = (
            f"{data.get('name')} (CIK {cik}) files with the SEC under SIC code {data.get('sic')} "
            f"({data.get('sicDescription')}). State of incorporation: {data.get('stateOfIncorporation')}. "
            f"Fiscal year end: {data.get('fiscalYearEnd')}. Recent filings: "
            + "; ".join(f"{f} on {d}" for f, d in forms)
            + ". Annual reports (10-K) describe the business model, competition and risk factors."
        )
        out.append(doc(
            title=f"SEC EDGAR filings: {data.get('name')}", text=text,
            url=f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={cik}", kb="A",
            source_type="edgar", publisher="U.S. SEC EDGAR",
            licence_note="US government public information; attribution courtesy",
            attribution="U.S. Securities and Exchange Commission, EDGAR", category="business",
            adapter="edgar",
        ))
    return out


SOURCES = {
    "wikipedia": collect_wikipedia,
    "worldbank": collect_worldbank,
    "arxiv": collect_arxiv,
    "hackernews": collect_hackernews,
    "github": collect_github,
    "docs": collect_docs,
    "gleif": collect_gleif,
    "edgar": collect_edgar,
}


def main() -> None:
    parser = argparse.ArgumentParser(description="Collect KB-A/KB-B seed documents.")
    parser.add_argument("--only", nargs="*", choices=sorted(SOURCES), help="sources to collect")
    args = parser.parse_args()
    total = 0
    for name in args.only or SOURCES:
        print(f"collecting {name} …", flush=True)
        try:
            docs = SOURCES[name]()
        except Exception as exc:  # noqa: BLE001 - one failing source must not stop the rest
            print(f"  {name}: failed ({exc})")
            continue
        path = write_jsonl(name, docs)
        total += len(docs)
        print(f"  {name}: {len(docs)} documents -> {path.name}", flush=True)
    print(f"done: {total} documents")


if __name__ == "__main__":
    main()
