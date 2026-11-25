# Phase 2: Intelligence (Weeks 4-5): spec alignment and build notes

**Goal:** the system can research an idea and retrieve cited evidence.
**Done when:** for each sample idea the system returns relevant passages with working source links, and hybrid search beats vector-only on the labelled query set.
**Milestone M1:** idea, extraction, research and retrieval working end to end in the UI.

This page compares the Phase 2 brief from the team (Nov 2026) with the frozen blueprint (`implementation_plan.md` §4, `AI_DESIGN.md` §3-4 and §10, `architecture.md` §7-9, `SRS.md` FR-RES) and records what was built for each item.

## 1. Comparison: brief vs. design documents

| Topic | Team brief | Design docs | Decision (built) |
| --- | --- | --- | --- |
| Seeding scripts | `seed_kb/collect.py`, `add_documents.py`, `ingest.py` | `scripts/ingest_kb.py` | Brief's three scripts in `scripts/seed_kb/` (the design's single script is split into collect → add → ingest) |
| Seed size | about 150-300 documents | not fixed | 159 sources / 765 passages loaded now; +~90 Wikipedia articles once `SCRAPER_CONTACT` is set (≈250) |
| Seed sources | Wikipedia, World Bank, arXiv, Hacker News, GitHub API, documentation sites, architecture guides | adds SEC EDGAR, GLEIF, OECD/Eurostat, Kaggle/HF datasets, case studies | All brief sources **plus** GLEIF and SEC EDGAR adapters (EDGAR runs only with `SEC_CONTACT_EMAIL`), the team's `rag/` notes and the 10 sample datasets. arXiv was missing from the design and is added there |
| Chunking | ~300 words, 40 overlap | 300-500 tokens, ~50 overlap; split on headings/paragraphs | 300 words / 40 overlap (≈400 tokens, inside the design range); headings and paragraphs first, heading path kept on each passage |
| Metadata | kb, category, source type, dates, licence note | adds url, title, publisher, attribution, user/project for KB-C | All of them; licence **and** attribution are mandatory for KB-A/B (rows without them are rejected) |
| Dedupe | content hash | exact hash + near-duplicate shingles per domain | Both |
| Retrieval | semantic top 30 + keyword top 30, RRF, filters, rerank, final 5-8 | same, plus query rewrite, recency, near-duplicate removal | Same; near-duplicate removal and max 3 passages per source; date/KB/category/source-type filters. LLM query rewrite is left out of search (the Research Agent already plans 4-8 queries) |
| Isolation | public KB-A/B or KB-C of current user+project; automated test | same (FR-RES-7) | One predicate in `retrieval.build_where`, applied to every mode; tested in pytest and in the black-box run |
| Research Agent | 4-8 queries, Tavily, fetch permitted pages, store KB-C with citations | adds robots/terms guard, rate limits, provenance, 7-day cache, spend cap, fallback, unanswered questions; competitor extraction | All of it; competitor **table** stays in Phase 3 (task 3.4) as the plan schedules it |
| Page fetching | "Firecrawl or trafilatura" | own scraper only, no third-party scraping API | trafilatura + httpx (Firecrawl would be a second paid API, which the design rules out). Playwright is used for JS pages only when it is installed |
| Uploads | PDF, DOCX, TXT, MD into KB-C | same + size/type limits | 10 MB limit, 415 on other types, duplicates detected |
| Frontend | Research tab: sources, links, dates, passage previews | S11: summary strip, filters, source cards, claim chips, competitor table, "Run research again", "Add source" | All except claim chips and competitor table (Phase 3 data); adds knowledge-base search with mode switch and the crawl log |
| Endpoints | `POST /projects/{id}/research`, `GET /projects/{id}/sources`, `POST /projects/{id}/documents`, internal retrieval | `GET /projects/{id}/sources`, `POST /projects/{id}/documents` | Those plus `GET/DELETE /projects/{id}/sources/{sid}`, `POST /projects/{id}/search`, `GET /projects/{id}/crawl`, `GET /runs/project/{id}`, `GET /knowledge/stats` |
| Models | Sentence Transformers, cross-encoder reranker (Hugging Face Hub) | all-MiniLM-L6-v2 (384-d), ms-marco-MiniLM-L-6-v2 | Same, on CPU; cache directory configurable with `HF_HOME` |
| Vector store | pgvector | pgvector + HNSW | pgvector when installed; until then `REAL[]` + exact cosine in Python over the already-scoped rows (same results, slower). `scripts/install_pgvector_windows.ps1` + `scripts/enable_pgvector.py` switch over |
| Background jobs | Celery | Celery | Celery task `ideaform.research_project`; `JOBS_INLINE=true` runs it in the request for local Windows without Redis |

## 2. What runs where

```
scripts/seed_kb/collect.py      Wikipedia*, World Bank, arXiv, HN, GitHub, docs + architecture guides, GLEIF, EDGAR*
scripts/seed_kb/add_documents.py  rag/*.md notes, data/knowledge_seed/documents/*, 10 sample datasets
scripts/seed_kb/ingest.py       clean -> hash/dedupe -> chunk 300/40 -> tag -> embed -> research_sources/chunks/embeddings
backend/app/services/knowledge  text.py, loaders.py, embeddings.py, rerank.py, vector_store.py, ingest.py, retrieval.py
backend/app/services/scrapers   guard.py (robots.txt, terms, per-domain rate limit), fetcher.py, adapters.py, quality.py, crawler.py
backend/app/services/research   discovery.py (Tavily, cache, cap, fallback), planner.py (4-8 queries), agent.py (Research Agent v1)
backend/app/api/research.py     research, sources, documents, search, crawl, knowledge stats
frontend/app/(app)/projects/[id]/research/page.tsx   Research tab
scripts/eval_retrieval.py       keyword vs vector vs hybrid vs hybrid+rerank on data/eval/retrieval_queries.json
scripts/research_sample_ideas.py  Phase 2 gate on the 10 sample ideas
scripts/blackbox_api_test.py    HTTP-only test of every endpoint against a running API
```
`*` needs a contact in the User-Agent: set `SCRAPER_CONTACT` (Wikipedia) and `SEC_CONTACT_EMAIL` (EDGAR) in `.env`.

## 3. Results

**Knowledge base:** 243 public sources / 2,110 passages (KB-A 118 / 820, KB-B 125 / 1,290) after adding 84 Wikipedia articles.

**Retrieval (40 labelled queries, KB-A + KB-B, 26 Nov 2026):**

| Mode | Precision@5 | Recall@10 | MRR | nDCG@10 | ms/query (no pgvector) |
| --- | --- | --- | --- | --- | --- |
| keyword | 0.405 | 0.672 | 0.743 | 0.505 | 68 |
| vector | 0.585 | 0.852 | 0.926 | 0.687 | 961 |
| hybrid (RRF only) | 0.505 | 0.823 | 0.856 | 0.645 | 513 |
| **hybrid + rerank (the pipeline the app uses)** | 0.570 | **0.858** | **0.975** | **0.702** | 3276 |

The full hybrid pipeline beats vector-only on Recall@10, MRR and nDCG@10 and is 0.015 behind on Precision@5. Plain RRF *without* the reranker does not beat vector-only on this corpus: the keyword list adds noise that equal-weight fusion passes through, and the cross-encoder removes it. Before Wikipedia was loaded (159 sources) plain RRF also beat vector-only (Recall@10 0.949 vs 0.941, MRR 0.942 vs 0.919). The relevance labels were extended with the matching Wikipedia articles when those were added; no weights were tuned on the labels.

**Sample ideas (Phase 2 gate):** all 10 sample ideas researched end to end; 15-27 KB-C sources each, 3/3 questions answered with cited passages for every idea, and 42 of 44 cited links open (`data/eval/results/sample_research_latest.md`).

**Black-box API run:** 55/55 checks passed against the live server with real Groq and Tavily calls.

* Retrieval comparison: `data/eval/results/retrieval_latest.md` (40 labelled queries).
* Sample ideas: `data/eval/results/sample_research_latest.md`.
* Black-box API run: `data/eval/results/api_blackbox_*.md`.
* Unit/integration tests: `backend/tests/` (`make test-local`).

## 4. Known limits

* Without pgvector, vector search scans every in-scope embedding (≈0.8 s/query at 765 passages); with pgvector + HNSW it is an index lookup.
* The cross-encoder reranker adds ≈3 s per search on CPU. It can be switched off with `RERANKER_ENABLED=false`.
* A research run is synchronous in `JOBS_INLINE` mode (2-3 minutes for ~30 pages). With Redis + Celery it is queued and the UI shows "running".
* Many commercial sites block crawlers in robots.txt; those URLs are recorded as skipped and never fetched.
