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

## Run

```bash
cp .env.example .env          # then set GROQ_API_KEY (and TAVILY_API_KEY when researching)
docker compose up -d --build  # start everything
docker compose exec api alembic upgrade head
curl -fsS localhost:8000/health/ready
```

Open http://localhost:3000 and register an account.

## Checks

```bash
make health          # liveness + readiness
make migrate         # apply migrations
make test            # pytest inside the api container
```

`/health/ready` returns 503 unless Postgres, Redis andthe configured LLM provider all
answer. It checks wiring, not model quality.

## Layout

```
backend/app/        FastAPI app: config, db, models, schemas, api, services, worker
backend/migrations  Alembic; 0001 creates all 16 tables
frontend/app/       Next.js app router (login, dashboard, project flow)
data/               sample ideas, knowledge seeds, eval fixtures, scraped corpus
docs/               the five blueprint documents
scripts/            ingestion and maintenance scripts
```

## Configuration

All settings come from `.env` (git-ignored) via `backend/app/config.py`; `.env.example`
lists every variable. `GROQ_API_KEY` is read from the environment only and is never
logged, returned, or committed.

##   Design docs

`SRS.md`, `architecture.md`, `database_design.md`, `implementation_plan.md`, `AI_DESIGN.md`.




## Configuration

All settings come from `.env` (git-ignored) via `backend/app/config.py`; `.env.example`
lists every variable. `GROQ_API_KEY` is read from the environment only and is never
logged, returned, or committed.

## Design docs

`docs/SRS.md`, `docs/architecture.md`, `docs/database_design.md`,
`docs/implementation_plan.md`, `docs/AI_DESIGN.md`.

Contribution rules are in `CONTRIBUTING.md`.
