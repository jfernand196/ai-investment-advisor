from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.infrastructure.db.seed import seed_reference_data
from app.infrastructure.db.session import get_db

router = APIRouter(prefix="/admin")


@router.post("/seed")
def run_seed(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict:
    result = seed_reference_data(db, settings)
    return {"status": "ok", **result}
