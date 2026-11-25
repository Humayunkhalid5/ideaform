import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import auth, health, projects, runs
from app.config import get_settings

settings = get_settings()

logging.basicConfig(level=settings.log_level)

app = FastAPI(
    title="Ideaform API",
    version="0.2.0",
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
app.include_router(runs.router)


@app.get("/")
def root() -> dict[str, str]:
    return {"name": "Ideaform", "docs": "/docs", "health": "/health"}
