from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.schemas.portfolio import PortfolioHoldingsReplace, PortfolioOut
from app.core.config import Settings, get_settings
from app.infrastructure.db.models import HoldingModel, PortfolioModel
from app.infrastructure.db.seed import seed_reference_data
from app.infrastructure.db.session import get_db

router = APIRouter(prefix="/portfolios")


def _get_primary_portfolio(db: Session, settings: Settings) -> PortfolioModel:
    portfolio = db.scalar(
        select(PortfolioModel)
        .options(selectinload(PortfolioModel.holdings))
        .where(PortfolioModel.is_primary.is_(True))
        .limit(1)
    )
    if portfolio is None:
        seed_reference_data(db, settings)
        portfolio = db.scalar(
            select(PortfolioModel)
            .options(selectinload(PortfolioModel.holdings))
            .where(PortfolioModel.is_primary.is_(True))
            .limit(1)
        )
    if portfolio is None:
        raise HTTPException(status_code=500, detail="Portfolio bootstrap failed")
    return portfolio


@router.get("/primary", response_model=PortfolioOut)
def get_primary_portfolio(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> PortfolioModel:
    return _get_primary_portfolio(db, settings)


@router.put("/primary/holdings", response_model=PortfolioOut)
def replace_primary_holdings(
    payload: PortfolioHoldingsReplace,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> PortfolioModel:
    portfolio = _get_primary_portfolio(db, settings)

    allowed = set(settings.etf_universe)
    for holding in payload.holdings:
        symbol = holding.symbol.upper()
        if symbol not in allowed:
            raise HTTPException(
                status_code=422,
                detail=f"Symbol {symbol} is outside the configured ETF universe",
            )

    if payload.cash_usd is not None:
        portfolio.cash_usd = payload.cash_usd

    portfolio.holdings.clear()
    db.flush()

    for holding in payload.holdings:
        portfolio.holdings.append(
            HoldingModel(
                symbol=holding.symbol.upper(),
                quantity=holding.quantity,
                avg_cost_usd=holding.avg_cost_usd,
            )
        )

    db.commit()
    db.refresh(portfolio)
    return _get_primary_portfolio(db, settings)
