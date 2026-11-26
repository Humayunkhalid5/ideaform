# Phase 4: Blueprint Generation (Week 8): spec alignment and build notes

**Goal:** turn the validated idea into a development-ready blueprint.
**Done when:** one idea produces a complete blueprint and any single section can be regenerated alone.
**Milestone M3:** complete idea-to-blueprint flow.

## 1. Brief vs. what was built

| # | Brief item | Built |
| --- | --- | --- |
| 1 | Product Design Agent: requirements, user flows, screen list, UI/UX concepts | `ui_ux` section (`services/blueprint/generators.py`, strong tier): 8-16 requirements (functional / non-functional, must/should/could, keeps the user's confirmed requirements), user roles, 2-4 user flows (each also drawn as a Mermaid flowchart), 5-10 screens with routes and key elements, design principles, accessibility |
| 2 | Technical Architect Agent: stack with reasons and alternatives, component architecture, security and scalability | `architecture` section (strong tier): 5-8 stack layers each with a reason, 1-3 alternatives and optional KB-B reference ids, 4-10 typed components and their connections (Mermaid component diagram), data flow, deployment, security (authentication, authorisation, input validation, secrets, OWASP), scalability. Automatic "Architecture Critic" checks (AI_DESIGN 6.4) add review notes: no data store, no authentication, unconnected components, single point of failure, no stack |
| 3 | Generators: PRD, architecture + Mermaid, schema + ER, API spec, UI/UX, roadmap | One call per section, each with its own schema (`schemas/blueprint.py`) and prompt (`prompts.py`, version `blueprint/v1`). The model only fills structured fields; `render.py` turns them into Markdown with fixed templates (PRD sections from AI_DESIGN 6.5) and builds every Mermaid diagram in code with sanitised ids and labels, so diagrams are always valid. Schema and API get review checks too (missing primary keys, foreign keys to unknown tables, duplicate endpoints, unauthenticated writes) |
| 4 | Section regeneration with optional instructions | `POST /projects/{id}/artifacts/{type}/regenerate {instructions?}` runs only that section. Its inputs are the newest stored versions of the sections it depends on (`DEPENDENCIES`), so nothing else is redone. Sections built on an older input are flagged `stale_inputs` in the API and UI |
| 5 | Artifact storage: versioned rows, user edits create new versions | `project_artifacts`: every generation, regeneration or edit adds a row with `artifact_version` + 1, the Markdown, the structured `data` (result, review notes, references used, `based_on` input versions, notices, model, prompt version), the user's `instructions` and the `run_id`. `PATCH /artifacts/{id}` saves an edit as a new version; older versions stay readable |
| 6 | Frontend: Blueprint tab with editable documents and Mermaid viewer | `app/(app)/projects/[id]/blueprint`: section list (version, edited and stale badges), rendered document (`MarkdownDoc`, GitHub-flavoured Markdown) with diagrams drawn by `MermaidDiagram` (lazy-loaded, `securityLevel: "strict"`, light/dark aware, source shown if a diagram fails), Markdown editor with live preview (save = new version), per-section regenerate with instructions, version history selector, live progress while generating (sections appear as they are saved) |

**Retrieval (KB-B):** the architecture, schema and API sections get up to 8 numbered technical
passages (`R1..R8`) from hybrid search over KB-B. Unknown `[R#]` citations are removed; cited
passages are listed under "References (KB-B)". If KB-B is empty (run `make seed-kb`), the
section says so in a notice and cites nothing.

## 2. Endpoints

| Method | Path | What it does |
| --- | --- | --- |
| POST | `/projects/{id}/blueprint` | Generate all six sections for the current version (understands it first if needed). Inline with `JOBS_INLINE=true`, else Celery `ideaform.generate_blueprint` |
| GET | `/projects/{id}/artifacts?version=` | Newest version of every section, `missing` sections, `has_evaluation` |
| GET | `/projects/{id}/artifacts/{type}/history` | All versions of one section, newest first |
| POST | `/projects/{id}/artifacts/{type}/regenerate` | Body `{instructions?}` (max 2,000 chars); regenerates that section only |
| GET | `/artifacts/{id}` | One artifact version |
| PATCH | `/artifacts/{id}` | Body `{content}`; saves the edit as the next version (422 if nothing changed) |

`{type}` is one of `ui_ux`, `architecture`, `database_schema`, `api_spec`, `prd`, `roadmap`.
All are owner-only (404 for other users) and generation counts against the daily token limit.

## 3. Checked against `architecture.md` (what differs, and why)

| `architecture.md` says | Phase 4 does | Why |
| --- | --- | --- |
| A separate **Documentation Agent** assembles PRD, roadmap and exports | PRD and roadmap are generators in the same pipeline; exports are not built | The brief lists PRD and roadmap under generators; export is Phase 5 |
| LangGraph orchestrator with an evidence-validation loop between agents | A sequential pipeline in dependency order (`ORDER`), each section committed as it finishes | LangGraph orchestration is Phase 5; the plan allows a simple sequential pipeline |
| Only three artifact endpoints | Three more: generate all, section history, read one artifact | The UI needs a one-click blueprint and version history |
| `artifact_type` also allows `business_model`, `feasibility_report`, `diagram` | Diagrams live inside the Markdown of their section; business model stays on the evaluation; feasibility report is an export | Keeps a section and its diagram one versioned unit; reports are Phase 5 |
| `project_artifacts` columns as in `database_design.md` 4.11 | Adds `data JSONB` and `instructions TEXT` (migration `0004`) | Regeneration needs the structured inputs, and users should see what instructions produced a version |
| React Flow (optional) | Not used | Mermaid covers the diagrams; one dependency fewer |

Everything else (strong tier for the agents, KB-B for technical agents, fixed PRD template,
roadmap with tasks, dependencies and estimates, owner-only access) follows the docs.

## 4. Free-tier notes

Six calls per full blueprint: `ui_ux`, `architecture`, `database_schema` on the strong model,
`api_spec`, `prd`, `roadmap` on the fast model (separate per-minute budgets). Output sizes are
bounded in the prompts and `max_tokens`; the Groq provider waits on `retry-after` when the
8k tokens-per-minute limit is hit, so a full blueprint takes about two to five minutes.

## 5. Verification

- Unit tests without a database: `tests/test_blueprint_unit.py` (9): lenient schemas, diagram
  sanitising, review checks, full render, reference stripping, prompt inputs and instructions,
  edited upstream passed as text.
- API tests on PostgreSQL: `tests/test_blueprint_api.py` (5): complete blueprint for one idea,
  regenerating one section leaves the others untouched and marks dependants stale, user edit
  creates a new version, validation and ownership, a failing section marks the run failed and
  keeps finished sections.
- Full suite with `TEST_DATABASE_URL`: **110 passed, 0 skipped** (all phases, including the
  Phase 1-3 database tests).
- Live run on 2026-11-26 (Groq free tier + local PostgreSQL, through the Blueprint tab) for the
  evaluated "Tutor Match" idea:
  - **Complete blueprint:** 6 LLM calls, 109 s, 20,047 tokens (11,778 in / 8,269 out); all six
    sections stored as v1 with 6 Mermaid diagrams (3 user flows, component diagram, ER
    diagram, roadmap), every one drawn in the browser without errors. No automatic review
    check fired. KB-B was empty, so architecture, schema and API carry that notice.
  - **One section alone:** regenerating the database schema with the instruction "Add soft
    deletes: a `deleted_at` column on bookings and reviews…" took 1 LLM call, 31.5 s and 4,835
    tokens. The schema became v2 and follows the instruction; every other section stayed v1;
    the API specification and roadmap were flagged as built on an older schema.
- Frontend: `npx tsc --noEmit` and `npm run build` pass.

## 6. Known limits

- Generated blueprints are starting points that need human review; durations are estimates.
- KB-B is empty until `make seed-kb` runs, so references are usually absent on a fresh install.
- Exports (PDF, Markdown, ZIP) and the LangGraph orchestrator are Phase 5.
