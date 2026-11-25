# Ideaform

Turn a rough idea into evidence-backed evaluation and a buildable blueprint: six analysis
dimensions, cited research, and generated PRD/architecture/roadmap.

All reasoning goes through one **Groq** provider interface: fast tier for classification
and extraction, strong tier for evaluation and blueprint generation. **Tavily** is the only
paid search API and is used solely to discover URLs; page content is fetched by our own scraper.

## Services

| Service | Port | What it is |
| --- | --- | --- |
| `api` | 8000 | FastAPI app (`/docs`, `/health`, `/health/ready`, `/auth`, `/projects`, `/runs`) |
| `worker` | — | Celery worker on Redis (extraction tasks) |
| `web` | 3000 | Next.js app (`/login`, `/dashboard`, `/projects/new`) |
| `db` | 5432 | PostgreSQL 16 + pgvector |
| `redis` | 6379 | Broker and cache |

## Run with Docker

```bash
cp .env.example .env          # set JWT_SECRET and GROQ_API_KEY (TAVILY_API_KEY for research)
docker compose up -d --build  # start everything
docker compose exec api alembic upgrade head
curl -fsS localhost:8000/health/ready
```

Open http://localhost:3000 and register an account.

## Run locally (Windows, no Docker)

Uses a local PostgreSQL service and runs extraction jobs inside the API request
(`JOBS_INLINE=true`), so Redis and the Celery worker are not needed.

```powershell
copy .env.example .env   # then set DATABASE_URL to your local DB, JWT_SECRET, GROQ_API_KEY, JOBS_INLINE=true
cd backend
py -m venv .venv
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\alembic upgrade head
.venv\Scripts\python -m uvicorn app.main:app --reload --port 8000
```

```powershell
cd frontend
npm install
npm run dev
```

**pgvector.** Stock Windows PostgreSQL has no pgvector. Migration `0001` then creates
`embeddings.embedding` as `REAL[]` and skips the HNSW index; nothing in Phase 1 reads it.
Before Phase 2 retrieval, build it with `scripts/install_pgvector_windows.ps1` (admin
"x64 Native Tools" prompt) and run `scripts/enable_pgvector.py` to convert the column.

## API (Phase 1)

| Method | Path | What it does |
| --- | --- | --- |
| POST | `/auth/register`, `/auth/login` | Rate-limited per client IP (`AUTH_RATE_LIMIT_*`) |
| GET | `/auth/me` | Current user |
| GET/POST | `/projects` | List / create (creates version 1) |
| GET/PATCH/DELETE | `/projects/{id}` | Read, update, delete (owner only, others get 404) |
| GET/PATCH | `/projects/{id}/requirements` | List / edit or confirm (all-or-nothing) |
| POST | `/projects/{id}/understand` | Classify + extract structure and requirements for the current version |
| POST | `/projects/{id}/requirements/regenerate` | Re-extract requirements; keeps confirmed and user-edited rows |
| GET/POST | `/projects/{id}/versions` | List versions / add a new idea version (becomes current) |
| GET | `/projects/{id}/versions/{n}` | One version with its structure and requirements |
| POST | `/projects/{id}/versions/{n}/restore` | Make an earlier version current again |
| GET | `/runs/{id}` | Background run status, model and token use |

`understand` and `regenerate` return 429 once the user's `daily_token_limit` (tokens
used by their runs since 00:00 UTC) is spent.

## Checks

```bash
make health          # liveness + readiness
make migrate         # apply migrations
make test            # pytest inside the api container
make test-local      # pytest with backend/.venv (needs TEST_DATABASE_URL)
```

Tests need a **separate, disposable** PostgreSQL database in `TEST_DATABASE_URL`
(every table in it is dropped and recreated); without it the database tests are skipped.
The LLM is faked in tests, so no Groq key is used.

`/health/ready` returns 503 unless Postgres, Redis (skipped when `JOBS_INLINE=true`)
and the configured LLM provider all answer. It checks wiring, not model quality.

## Scripts and data

| Script | Purpose |
| --- | --- |
| `scripts/profile_datasets.py` | Catalogue the `10 sample datasets/` folder into `data/knowledge_seed/datasets_catalogue.{json,md}` |
| `scripts/build_eval_set.py` | Build `data/eval/classification_labels.csv` from the 10 sample ideas + 42 labelled ideas in the business-ideas dataset |
| `scripts/run_eval.py` | Classification accuracy, latency and tokens against Groq (writes `data/eval/results/`) |
| `scripts/seed_demo.py` | Demo account with the 10 sample ideas as projects (`--understand` to extract them) |
| `scripts/enable_pgvector.py` | Convert the embeddings fallback column to `vector(384)` |
| `scripts/install_pgvector_windows.ps1` | Build pgvector from the official source for local Windows PostgreSQL |
| `scripts/backup_db.ps1` | `pg_dump` the database into `backups/` |

Run the Python scripts from the repo root with `backend/.venv/Scripts/python`.

## Layout

```
backend/app/        FastAPI app: config, db, models, schemas, api, services, worker
backend/migrations  Alembic; 0001 creates all 16 tables
backend/tests/      pytest suite (auth, ownership, projects, versions, quota, pipeline)
frontend/app/       Next.js app router (login, dashboard, project flow)
data/               sample ideas, dataset catalogue, eval labels, scraped corpus (ignored)
docs/               the five blueprint documents
scripts/            dataset, eval, seed, backup and pgvector scripts
10 sample datasets/ raw CSV datasets (see data/knowledge_seed/datasets_catalogue.md)
```

## Configuration

All settings come from `.env` (git-ignored) via `backend/app/config.py`, which reads the
repo-root `.env` and then `backend/.env`. `.env.example` lists every variable.
`GROQ_API_KEY` is read from the environment only and is never logged, returned, or
committed. The API refuses to start if `JWT_SECRET` is a placeholder or shorter than
32 characters (only `ENVIRONMENT=test` is exempt).

## Design docs

`docs/SRS.md`, `docs/architecture.md`, `docs/database_design.md`,
`docs/implementation_plan.md`, `docs/AI_DESIGN.md`.

Contribution rules are in `CONTRIBUTING.md`.
