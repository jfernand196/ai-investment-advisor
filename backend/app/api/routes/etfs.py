from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.schemas.etf import EtfOut
from app.core.config import Settings, get_settings
from app.infrastructure.db.models import EtfUniverseModel
from app.infrastructure.db.seed import seed_reference_data
from app.infrastructure.db.session import get_db

router = APIRouter(prefix="/etfs")


@router.get("", response_model=List[EtfOut])
def list_etfs(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> list[EtfUniverseModel]:
    rows = db.scalars(
        select(EtfUniverseModel).where(EtfUniverseModel.is_active.is_(True)).order_by(EtfUniverseModel.symbol)
    ).all()
    if not rows:
        seed_reference_data(db, settings)
        rows = db.scalars(
            select(EtfUniverseModel)
            .where(EtfUniverseModel.is_active.is_(True))
            .order_by(EtfUniverseModel.symbol)
        ).all()
    return list(rows)


@router.get("/{symbol}", response_model=EtfOut)
def get_etf(symbol: str, db: Session = Depends(get_db)) -> EtfUniverseModel:
    etf = db.get(EtfUniverseModel, symbol.upper())
    if etf is None or not etf.is_active:
        raise HTTPException(status_code=404, detail="ETF not found")
    return etf
