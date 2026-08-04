from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.infrastructure.db.session import get_db

router = APIRouter()


@router.get("/health/live")
def live() -> dict:
    return {"status": "ok"}


@router.get("/health/ready")
def ready(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict:
    db_ok = False
    db_error = None
    try:
        db.execute(text("SELECT 1"))
        db_ok = True
    except Exception as exc:  # noqa: BLE001 — surface readiness failure cleanly
        db_error = str(exc)

    status = "ok" if db_ok else "degraded"
    payload = {
        "status": status,
        "app": settings.app_name,
        "env": settings.app_env,
        "database": {"ok": db_ok},
        "etf_universe": settings.etf_universe,
    }
    if db_error:
        payload["database"]["error"] = db_error
    return payload
