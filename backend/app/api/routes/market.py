from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.schemas.market import (
    FeatureOut,
    FxRateOut,
    IngestRequest,
    IngestResponse,
    MacroPointOut,
    MarketOverviewOut,
    PriceBarOut,
)
from app.application.market.ingest import IngestMarketDataUseCase
from app.core.config import Settings, get_settings
from app.infrastructure.db.market_repository import MarketRepository
from app.infrastructure.db.session import get_db
from app.infrastructure.market.fred_client import DEFAULT_SERIES

router = APIRouter(prefix="/market")


@router.post("/ingest", response_model=IngestResponse)
def ingest_market(
    payload: Optional[IngestRequest] = None,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> IngestResponse:
    body = payload or IngestRequest()
    use_case = IngestMarketDataUseCase(repo=MarketRepository(db), settings=settings)
    result = use_case.execute(lookback_days=body.lookback_days)
    return IngestResponse(
        etf_bars=result.etf_bars,
        fx_points=result.fx_points,
        macro_points=result.macro_points,
        features=result.features,
        warnings=result.warnings,
        started_at=result.started_at,
        finished_at=result.finished_at,
    )


@router.get("/overview", response_model=MarketOverviewOut)
def market_overview(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> MarketOverviewOut:
    repo = MarketRepository(db)
    warnings: list[str] = []
    if not settings.fred_api_key:
        warnings.append("FRED_API_KEY not configured")

    etf_features = []
    for symbol in settings.etf_universe:
        feature = repo.latest_feature(symbol)
        if feature:
            etf_features.append(feature)

    macro_latest = []
    for series_id in DEFAULT_SERIES:
        point = repo.latest_macro(series_id)
        if point:
            macro_latest.append(point)

    spot = repo.latest_fx("USDCOP_SPOT") or repo.latest_fx("USDCOP")
    trm = repo.latest_fx("USDCOP_TRM")
    return MarketOverviewOut(
        usdcop_spot=spot,
        usdcop_trm=trm,
        usdcop=spot,
        dxy=repo.latest_fx("DXY"),
        etf_latest_features=etf_features,
        macro_latest=macro_latest,
        warnings=warnings,
    )


@router.get("/etfs/{symbol}/bars", response_model=List[PriceBarOut])
def etf_bars(
    symbol: str,
    limit: int = Query(default=120, ge=1, le=2000),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> list:
    symbol_u = symbol.upper()
    if symbol_u not in settings.etf_universe:
        raise HTTPException(status_code=404, detail="Symbol outside ETF universe")
    rows = MarketRepository(db).list_price_bars(symbol_u, limit=limit)
    return list(reversed(rows))


@router.get("/fx/{pair}", response_model=List[FxRateOut])
def fx_history(
    pair: str,
    limit: int = Query(default=120, ge=1, le=2000),
    db: Session = Depends(get_db),
) -> list:
    pair_u = pair.upper()
    if pair_u not in {"USDCOP", "USDCOP_SPOT", "USDCOP_TRM", "DXY"}:
        raise HTTPException(
            status_code=404,
            detail="Supported pairs: USDCOP, USDCOP_SPOT, USDCOP_TRM, DXY",
        )
    # Newest first so clients can take index 0 as latest quote.
    return MarketRepository(db).list_fx(pair_u, limit=limit)


@router.get("/features/{entity}", response_model=FeatureOut)
def latest_feature(entity: str, db: Session = Depends(get_db)) -> FeatureOut:
    feature = MarketRepository(db).latest_feature(entity.upper())
    if feature is None:
        raise HTTPException(status_code=404, detail="No features for entity")
    return feature


@router.get("/macro/{series_id}", response_model=MacroPointOut)
def latest_macro(series_id: str, db: Session = Depends(get_db)) -> MacroPointOut:
    point = MarketRepository(db).latest_macro(series_id.upper())
    if point is None:
        # try exact case as stored
        point = MarketRepository(db).latest_macro(series_id)
    if point is None:
        raise HTTPException(status_code=404, detail="No macro observations")
    return point
