# Phase 3: Evaluation (Weeks 6-7): spec alignment and build notes

**Goal:** an evidence-based evaluation instead of a single score, and an improvement loop.
**Done when:** a full evaluation is generated for a sample idea, and after editing the idea the user sees a before/after comparison with stated reasons.
**Milestone M2:** evaluation and improvement loop demo-ready.

## 1. Brief vs. what was built

| # | Brief item | Built |
| --- | --- | --- |
| 1 | Evaluation Agent, six dimensions with score, confidence, explanation, evidence ids, assumptions, recommendations | `services/evaluation/evaluator.py`: two strong-tier calls of three dimensions each, schema-validated (`schemas/evaluation.py`) with one repair, plus one follow-up call if a dimension is missing. Rubric, direction notes and confidence rules from `AI_DESIGN.md` §5 are in the prompt (`prompts.py`, version `evaluation/v1`, saved on the run) |
| 2 | Evidence validation | `services/evaluation/evidence.py`: one hybrid-retrieval query per dimension plus a risk query (KB-A/B/C by dimension), passages numbered E1..En once for the whole evaluation and stored with it. After generation: unknown `[E#]` citations are removed from text and id lists, a `verified_fact` with no valid citation is relabelled `assumption` and added to the assumptions, confidence is forced to `low` with no evidence and capped at `medium` below 3 independent sources. Every correction becomes a notice shown in the UI |
| 3 | Claim labels in the UI | `ClaimChip` (verified fact / assumption / AI suggestion) on every claim, on hidden assumptions and on improvement suggestions; legend on the evaluation summary |
| 4 | Competitor analysis with source links and table | Fast-tier extraction limited to competitors **named in the evidence**; uncited competitors are dropped; a website is kept only if its domain appears in the evidence, otherwise Tavily is asked for the official site (URL discovery only, cached, capped at 3 lookups). Stored in `competitors` with `evaluation_id`, `source_id`, `source_url`, `evidence_ids`; comparison table in the Competitors section |
| 5 | Business model analysis | Strong-tier call: customer segments, value proposition, channels, revenue streams, cost structure, 2-3 pricing options, key metrics, assumptions (`evaluations.business_model`) |
| 6 | Risks and Devil's Advocate | Critique call: 4-6 risks with severity, likelihood, mitigation, dimension and evidence; Devil's Advocate argument; hidden assumptions; "what would have to be true" |
| 7 | Improvements and alternatives | 3-5 improvements, each with a concrete `change` to the idea text and `dimension_affected` (unknown names fall back to the weakest dimension); 2-3 alternatives |
| 8 | Improvement loop | `POST /improve`: accept / reject / edit per suggestion (+ optional own change), decisions saved in `project_feedback` and on the evaluation; `services/evaluation/improve.py` rewrites the idea (strong tier), creates the next version, runs understanding (carrying over confirmed or user-edited requirements), then re-evaluates with the previous evaluation as baseline. The model must give a `change_reason` per dimension; if it does not, a reason is generated from the score, confidence and explanation, so no change is ever unexplained |
| 9 | Frontend | Evaluation tab: disclaimer, overall gauge with delta, radar (Recharts) with the previous version overlaid, 3x2 score cards that expand to explanation with clickable citations, claims, assumptions, recommendations, sources and "why it moved"; sections for risks and Devil's Advocate, competitors, business model, improvement loop, all evidence. Compare tab: version pickers, overall delta, grouped bar chart, per-dimension change with reason, risks and requirements added/removed, sentence-level idea diff, "make vN current" |

## 2. Endpoints

| Method | Path | What it does |
| --- | --- | --- |
| POST | `/projects/{id}/evaluate` | Evaluate the current version (runs understanding first if it has no structure). Inline with `JOBS_INLINE=true`, else Celery `ideaform.evaluate_project` |
| GET | `/projects/{id}/evaluations?version=` | Evaluations of a version (default current), newest first, with dimensions, claims, evidence catalogue, risks, critique, improvements, competitors, business model, notices |
| POST | `/projects/{id}/improve` | Body `{evaluation_id?, decisions: [{improvement_id, decision, edited_text?}], note?}`; creates and evaluates the next version (Celery `ideaform.improve_project`, never retried so it cannot create two versions) |
| GET | `/projects/{id}/compare?a=&b=` | Latest evaluation of each version: per-dimension delta with reason, overall delta and summary, risks and requirements added/removed, idea text diff |

All are owner-only (404 for other users) and count against the daily token limit.

## 3. Storage (migration `0003`)

`0001` builds tables from the models, so `0003` uses `ADD COLUMN IF NOT EXISTS` and is safe on new and existing databases.

| Table | New columns |
| --- | --- |
| `evaluations` | `overall_score`, `critique`, `alternatives`, `business_model`, `evidence` (E-id catalogue), `notices`, `baseline_evaluation_id`, `model_name`, `prompt_version` |
| `evaluation_dimensions` | `claims`, `evidence_ids`, `previous_score`, `change_reason` |
| `competitors` | `evaluation_id`, `source_url`, `evidence_ids` |

`evaluation_evidence` links every cited chunk to its dimension with the strongest claim label that cites it.

## 4. Groq free tier

The free tier allows 8,000 tokens per minute per model. Each call is kept below that
(`reasoning_effort=low` for gpt-oss, about 3k prompt + 3.2k completion tokens), and the
provider now honours `Retry-After` / `x-ratelimit-reset-tokens` on 429 (up to 6 attempts,
max 65 s wait). A full evaluation is 5-6 calls and takes about 1-4 minutes on the free tier;
competitor extraction runs on the fast model, which has its own budget.

## 5. Verification (26 Nov 2026)

* `pytest`: 46 passed, 50 skipped (database tests need `TEST_DATABASE_URL`; not run on this machine, which has no reachable test database). New: `tests/test_evaluation_unit.py` (14 tests, no database) and `tests/test_evaluation_api.py` (6 API tests with a schema-aware fake LLM).
* `scripts/phase3_offline_demo.py` (real Groq calls, evidence from `rag/` notes instead of the database) on sample idea 4: six dimensions with cited evidence, 5 risks, 4 improvements; two improvements accepted, idea rewritten, re-evaluated; comparison 58 → 59 overall, market opportunity 45 → 50 "due to the explicit plan for a pilot study, though no evidence confirms demand", every other dimension unchanged with a stated reason. Output: `data/eval/results/phase3_offline_demo.json`.
* Frontend: `tsc --noEmit` and `next build` pass; the Evaluation and Compare tabs were checked in a browser against the demo output.

## 6. Known limits

* Validation checks citation ids, not whether a passage really supports a sentence; that needs the manual citation-validity sample from `AI_DESIGN.md` §10.
* Risk and Devil's Advocate text can still mention companies the evidence does not name; only the competitor table is restricted to cited companies.
* Competitors appear only when research has stored pages that name them; run Research before evaluating.
