import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import auth, blueprint, evaluation, health, orchestration, projects, research, runs, versions
from app.config import check_jwt_secret, get_settings

settings = get_settings()

logging.basicConfig(level=settings.log_level)
check_jwt_secret(settings)

def fail_interrupted_runs() -> int:
    """With JOBS_INLINE the API process runs background analyses itself, so a run still
    marked queued/running at startup was cut off by a restart: mark it failed (finished work
    is kept) instead of leaving it "running" forever."""
    if not settings.jobs_inline:
        return 0  # Celery workers own their runs
    from sqlalchemy import update

    from app.db.session import SessionLocal
    from app.models.agent import AgentRun

    try:
        with SessionLocal() as db:
            result = db.execute(
                update(AgentRun)
                .where(AgentRun.status.in_(("queued", "running")))
                .values(status="failed", finished_at=datetime.now(timezone.utc),
                        error_message="Interrupted: the API restarted while this run was in progress. Run it again.")
            )
            db.commit()
            return result.rowcount or 0
    except Exception as exc:  # noqa: BLE001 - never block startup on this
        logging.getLogger(__name__).warning("could not check for interrupted runs: %s", exc)
        return 0


@asynccontextmanager
async def lifespan(_app: FastAPI):
    count = fail_interrupted_runs()
    if count:
        logging.getLogger(__name__).warning("marked %s interrupted run(s) as failed", count)
    yield


app = FastAPI(
    lifespan=lifespan,
    title="Ideaform API",
    version="0.5.0",
    description="AI idea analysis platform: provider-agnostic LLM, self-hosted scraper, Tavily discovery.",
)

app.add_middleware(
    CORSMiddleware,
    # Local development is served from either localhost or 127.0.0.1, and on any
    # port a developer happens to free up. Only loopback origins are allowed.
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_origin_regex=r"^http://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(projects.router)
app.include_router(versions.router)
app.include_router(research.router)
app.include_router(evaluation.router)
app.include_router(blueprint.router)
app.include_router(blueprint.artifacts_router)
app.include_router(orchestration.router)
app.include_router(runs.router)


@app.get("/")
def root() -> dict[str, str]:
    return {"name": "Ideaform", "docs": "/docs", "health": "/health"}
