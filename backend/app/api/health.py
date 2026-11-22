from fastapi import APIRouter, Depends, HTTPException, status
from redis import Redis
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.session import get_db

router = APIRouter(tags=["health"])
settings = get_settings()


@router.get("/health")
def health() -> dict[str, str]:
    """Liveness: the process is up. No dependencies touched."""
    return {"status": "ok", "service": "ideaform-api"}


@router.get("/health/ready")
def readiness(db: Session = Depends(get_db)) -> dict[str, object]:
    """Readiness: Postgres, Redis, and the local model runtime answer."""
    checks: dict[str, object] = {}

    try:
        db.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as exc:  # noqa: BLE001 - surfaced to the caller
        checks["database"] = f"error: {exc}"

    try:
        Redis.from_url(settings.redis_url, socket_timeout=2).ping()
        checks["redis"] = "ok"
    except Exception as exc:  # noqa: BLE001
        checks["redis"] = f"error: {exc}"

    try:
        import httpx

        resp = httpx.get(f"{settings.ollama_base_url}/api/tags", timeout=3)
        checks["llm"] = "ok" if resp.status_code == 200 else f"error: {resp.status_code}"
    except Exception as exc:  # noqa: BLE001
        checks["llm"] = f"error: {exc}"

    ok = all(v == "ok" for v in checks.values())
    if not ok:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail=checks)
    return {"status": "ready", "checks": checks}
