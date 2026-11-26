# Phase 5: Orchestration and Export (Week 9): spec alignment and build notes

**Goal:** one submission runs the whole pipeline automatically and exports the results.
**Done when:** the full flow runs from one submission and produces a PDF and ZIP.
The fallback ("simple sequential pipeline, Markdown and PDF only") was **not** needed: the
LangGraph graph, and Markdown, PDF, Word and ZIP export, are all built.

## 1. Brief vs. what was built

| # | Brief item | Built |
| --- | --- | --- |
| 1 | LangGraph orchestrator, shared project state, six agents in order | `services/orchestrator/graph.py`: a `StateGraph` over `ProjectState` (the shared state of architecture.md 6). Nodes: understanding → **Research** → **Evaluation** → evidence validation → **Business** → **Product Design** → **Technical Architect** → **Documentation**. Understanding runs first because every agent needs the structured idea; it is reused (no tokens) when the version is already understood |
| 2 | Validation nodes, retry once, then continue with a low-confidence flag | After every agent its output is checked against the expected shape (six dimensions with 0-100 scores, a non-empty business model, each blueprint section stored and non-empty, reports stored). A failed or invalid step is retried once; if it fails again the step is marked failed, added to `low_confidence`, and the graph continues. The evidence-validation node re-checks every citation and every `verified_fact` label after the evaluation; broken references send the graph back to the evaluation once (conditional edge), thin evidence flags the evaluation as low confidence. Only an understanding failure stops the run |
| 3 | Run tracking and progress in the UI | The analysis is one `agent_runs` row (`agent_name="analysis"`) and every step is its own row linked by the new `parent_run_id`, with status, model, prompt version, tokens, start/finish (duration) and errors. `GET /runs/{id}` returns the steps; the run page shows them live (`AnalysisProgress`) and the Versions tab lists every run |
| 4 | Export: Markdown, PDF (ReportLab), Word (python-docx), ZIP | `services/export/`: one bundle (idea and requirements, feasibility report with competitor analysis and sources, business model, the six blueprint sections) rendered as Markdown, PDF (cover, contents, running header, page numbers, Unicode font, tables, diagrams drawn as vectors), Word (headings, lists, tables, hyperlinks, diagrams as PNG) and a ZIP (all three reports, every section as its own .md, Mermaid sources, `project.json`, README). `POST /projects/{id}/export?format=pdf|docx|md|zip&version=` |
| 5 | Version history screen for ideas and artifacts | Versions tab (`GET /projects/{id}/history`): every idea version with its evaluations and score, every artifact version (edited / regenerated-with-instructions marked), make-current and compare actions, and the run history table |
| 6 | Cost controls | Fast model for extraction (classification and structure); a **content-hash cache** (`services/llm/cache.py`: SHA-256 of provider, model, messages, schema and parameters; Redis when reachable, otherwise the `llm_cache` table) answers repeated extraction of the same text with zero tokens; per-user daily token limit (`analyse` returns 429 when spent); **per-run budgets** from NFR-10 and architecture.md 9: `ANALYSIS_TOKEN_BUDGET` and `ANALYSIS_MAX_SECONDS` stop a run early, keep finished work and mark the rest skipped |

## 2. Also required by the design documents (not in the brief)

| Source | Requirement | Built |
| --- | --- | --- |
| AI_DESIGN 7 | Feasibility report, competitor analysis, business model as documents | Documentation Agent writes `feasibility_report` and `business_model` artifacts from the evaluation (deterministic: no tokens, cannot contradict the evaluation); Documents tab |
| SRS 6.1 | Workspace tabs include Versions and Export | Documents, Versions and Export tabs |
| FR-ORC-2, NFR-1 | Long tasks in the background with progress; full analysis within 10 minutes | `POST /analyse` returns at once; inline mode runs it as a background task, otherwise Celery `ideaform.analyse_project` |
| FR-ORC-3, NFR-4 | Record inputs, outputs, duration, tokens; reproducibility | Each step stores its input (version, attempt), output, model, prompt version, tokens and timing |
| FR-ORC-4, NFR-2 | Retries and clear errors; partial results saved | Step retry, per-section commits, errors listed on the run; one analysis per project at a time (409) |
| UC-1 | Create and analyse in one flow; confirm or correct | New-project wizard: "Run full analysis" (one submission) or "Understand only, confirm first" |
| AI_DESIGN 6.7 | Evidence validation after evaluation, retry once | Evidence-validation node with a conditional retry edge |

Found while testing and fixed in this phase:
- `generate_json`'s one-repair path raised `UnboundLocalError` (Python clears an `except … as e`
  name after the block), so invalid JSON was never repaired; the orchestrator's step retry
  caught it live. Fixed, with a regression test.
- An API restart in inline mode left an in-progress analysis "running" for ever; on startup the
  API now marks such runs failed ("interrupted"), keeping finished work.

## 3. Checked against `architecture.md`

| `architecture.md` says | Phase 5 does |
| --- | --- |
| `POST /projects/{id}/analyse` (background) and `GET /runs/{id}` (status and progress) | Built as specified; runs also carry `steps` |
| `POST /projects/{id}/export?format=pdf\|md\|zip` | Built, plus `docx` and `version=` |
| Agent workflow diagram (Research → Retrieve → Evaluation → Business → Product Design → Technical Architect → evidence validation → Documentation) | Same agents and order; evidence validation sits right after the evaluation (AI_DESIGN 6.7), which is where its "retry or flag" loop belongs |
| Redis as cache | Used when reachable; local runs without Redis use the Postgres `llm_cache` table |
| python-docx, ReportLab, zipfile | Used |

## 4. Endpoints

| Method | Path | What it does |
| --- | --- | --- |
| POST | `/projects/{id}/analyse` | Body `{depth?}`; full pipeline in the background, returns `run_id` (409 if one is already running) |
| GET | `/runs/{id}` | Run with `steps` (child runs) and `duration_seconds` |
| GET / POST | `/projects/{id}/reports` | Feasibility report and business model / rebuild from the evaluation |
| GET | `/projects/{id}/history` | Versions, evaluations, artifact versions, run history |
| POST | `/projects/{id}/export?format=&version=` | `pdf`, `docx`, `md` or `zip` download |

## 5. Verification

**Automated (PostgreSQL test database):** 129 passed, 0 skipped, 0 failed across all phases.
New for Phase 5:
- `tests/test_orchestration.py` (10 tests): one submission runs all eight steps and exports PDF,
  ZIP, Word and Markdown; help levels; retry-once-then-flag; evidence validation looping back to
  the evaluation; understanding failure stops the run; token budget stops early; one analysis
  at a time; history, reports and ownership; export before evaluation; content-hash cache.
- `tests/test_export_unit.py` (6 tests): every generated diagram parsed and drawn, unknown
  Mermaid falls back to source, PNG rendering, Markdown blocks, heading shifts, `generate_json`
  repair (regression).
- `tests/test_clarity_unit.py` (3 tests): vague idea questions, clear idea, priority calibration.

**Live run, 2026-11-26** (Groq free tier, local PostgreSQL, the app's own API), sample idea 2
from `data/test_ideas/sample_ideas.md` ("WashRun Lahore", help level *everything*):
- **RAG:** two of the project's own notes (`rag/03_business_model_patterns.md`,
  `rag/07_startup_risk_checklist.md`) uploaded to KB-C; hybrid search with reranking returned the
  revenue-models passage first for a pricing query and the risk checklist for an operations
  query. KB-A/B were empty (data is added later); the Research Agent crawled 8 sources.
- **One submission → full pipeline:** 8 steps, 262 s, 36,298 tokens. Evaluation used **20
  evidence passages** (all KB-C), overall score 51; all 4 verified facts carry citations. The
  Technical Architect failed once (the `generate_json` bug above), was retried automatically and
  succeeded; the documentation step wrote PRD, roadmap, feasibility report and business model.
- **NLP:** category *business* (high confidence); all five expected must-have requirements of
  sample 2 found (pickup scheduling, per-kg price, order tracking, riders, payment); missing
  information listed instead of invented. Sample 10 ("Something with AI for students.") is now
  flagged vague with four clarifying questions, and none of its AI-suggested requirements is a
  *must*.
- **Exports:** PDF 127 KB (32 pages for the earlier Tutor Match project, cover, contents, tables,
  diagrams rendered), ZIP 413 KB with 20 files, Word 263 KB, Markdown 39 KB.
- **Cache:** understanding the same text again used 1,270 tokens instead of 2,788
  (classification and extraction answered from the content-hash cache).
- **UI:** run page shows every step live; Documents, Versions and Export tabs checked in the
  browser, including a real PDF download ("ideaform-tutor-match-v1.pdf · 130 KB").
- Frontend: `npx tsc --noEmit` and `npm run build` pass.

## 6. Known limits

- KB-A and KB-B are empty until `make seed-kb` runs; most evidence then comes from research and
  uploads, so confidence is usually low.
- `TAVILY_API_KEY` is empty: research uses cached results and curated seed URLs only.
- In `JOBS_INLINE` mode the analysis runs inside the API process; restarting the API marks an
  in-progress run as failed (finished steps are kept). Use Celery + Redis for production.
