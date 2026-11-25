from fastapi import APIRouter, Depends, HTTPException, status
from redis import Redis
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.session import get_db
from app.services.llm import get_llm

router = APIRouter(tags=["health"])
settings = get_settings()


@router.get("/health")
def health() -> dict[str, str]:
    """Liveness: the process is up. No dependencies touched."""
    return {"status": "ok", "service": "ideaform-api"}


@router.get("/health/ready")
def readiness(db: Session = Depends(get_db)) -> dict[str, object]:
    """Readiness: Postgres, Redis, and the configured LLM provider answer."""
    checks: dict[str, object] = {}

    try:
        db.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as exc:  # noqa: BLE001 - surfaced to the caller
        checks["database"] = f"error: {exc}"

    if settings.jobs_inline:
        checks["redis"] = "ok"
        checks["jobs"] = "inline (JOBS_INLINE=true, Redis not required)"
    else:
        try:
            Redis.from_url(settings.redis_url, socket_timeout=2).ping()
            checks["redis"] = "ok"
        except Exception as exc:  # noqa: BLE001
            checks["redis"] = f"error: {exc}"

    try:
        provider = get_llm()
        ok, detail = provider.health()
        checks["llm"] = "ok" if ok else f"error: {detail}"
        checks["llm_provider"] = provider.name
        checks["llm_model_strong"] = provider.strong_model
    except Exception as exc:  # noqa: BLE001
        checks["llm"] = f"error: {exc}"

    ok = all(checks.get(name) == "ok" for name in ("database", "redis", "llm"))
    if not ok:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail=checks)
    return {"status": "ready", "checks": checks}
