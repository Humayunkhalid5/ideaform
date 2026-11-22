# Ideaform

Turn a rough idea into evidence-backed evaluation and a buildable blueprint: six analysis dimensions, cited research, and generated PRD/architecture/roadmap.

All reasoning runs on **local models** (Ollama). **Tavily** is the only paid external API and is used solely to discover URLs; page content is fetched by our own scraper.

## Phase 0: foundation

| Service | Port | What it is |
| --- | --- | --- |
| `api` | 8000 | FastAPI app (`/docs`, `/health`, `/health/ready`) |
| `worker` | — | Celery worker on Redis |
| `web` | 3000 | Next.js app |
| `db` | 5432 | PostgreSQL 16 + pgvector |
| `redis` | 6379 | Broker and cache |
| `ollama` | 11434 | Local model runtime |

## Run

```bash
cp .env.example .env          # then set TAVILY_API_KEY
docker compose up -d --build  # start everything
bash scripts/pull_models.sh   # pull the fast + strong local models
curl -fsS localhost:8000/health/ready
```

Requirements: Docker with the Compose plugin. The models need roughly 6–8 GB of RAM for the 7B model at Q4.

## Checks

```bash
make health          # liveness + readiness
make migrate         # apply migrations (baseline is empty until Phase 1 models)
make test            # pytest inside the api container
```

`/health/ready` returns 503 unless Postgres, Redis, and the Ollama `/api/tags` endpoint all answer. It reports wiring, not installed models — run `make models` for that.

## Layout

```
backend/app/       FastAPI app: config, db, api, worker
backend/migrations Alembic (baseline only; 16 tables land in Phase 1)
frontend/app/      Next.js app router
scripts/           model pull and future ingestion scripts
```

## Design docs

`SRS.md`, `architecture.md`, `database_design.md`, `implementation_plan.md`, `AI_DESIGN.md`.
