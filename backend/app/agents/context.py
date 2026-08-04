"""Load advisory context from DB (Data Plane → Decision Plane)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.config import Settings
from app.domain.enums import ETF_MAX_ALLOCATION_PCT, ETF_RISK_BUCKETS
from app.infrastructure.db.market_repository import MarketRepository
from app.infrastructure.db.models import InvestorProfileModel, PortfolioModel
from app.infrastructure.db.seed import seed_reference_data
from app.infrastructure.market.fred_client import DEFAULT_SERIES


@dataclass
class AdvisoryContext:
    as_of: datetime
    profile: Dict[str, Any]
    portfolio: Dict[str, Any]
    etf_features: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    fx_features: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    macro_latest: Dict[str, Any] = field(default_factory=dict)
    price_closes: Dict[str, List[float]] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)


def load_advisory_context(db: Session, settings: Settings) -> AdvisoryContext:
    repo = MarketRepository(db)
    as_of = datetime.now(timezone.utc)

    profile = db.scalar(select(InvestorProfileModel).limit(1))
    if profile is None:
        seed_reference_data(db, settings)
        profile = db.scalar(select(InvestorProfileModel).limit(1))
    assert profile is not None

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
    assert portfolio is not None

    holdings = []
    invested = Decimal("0")
    weights: Dict[str, float] = {}
    for h in portfolio.holdings:
        feat = repo.latest_feature(h.symbol)
        px = Decimal(str((feat.payload or {}).get("close", 0))) if feat else Decimal("0")
        mkt = h.quantity * px
        invested += mkt
        holdings.append(
            {
                "symbol": h.symbol,
                "quantity": float(h.quantity),
                "avg_cost_usd": float(h.avg_cost_usd),
                "mark_price": float(px),
                "market_value": float(mkt),
                "bucket": ETF_RISK_BUCKETS[h.symbol].value
                if h.symbol in ETF_RISK_BUCKETS
                else "unknown",
            }
        )

    nav = invested + portfolio.cash_usd
    if nav > 0:
        for h in holdings:
            weights[h["symbol"]] = h["market_value"] / float(nav)
        weights["CASH"] = float(portfolio.cash_usd) / float(nav)

    etf_features: Dict[str, Dict[str, Any]] = {}
    price_closes: Dict[str, List[float]] = {}
    warnings: List[str] = []

    for symbol in settings.etf_universe:
        feat = repo.latest_feature(symbol)
        if feat is None:
            warnings.append(f"missing_features:{symbol}")
            continue
        etf_features[symbol] = {
            **(feat.payload or {}),
            "bucket": ETF_RISK_BUCKETS[symbol].value,
            "max_allocation_pct": ETF_MAX_ALLOCATION_PCT[symbol],
            "as_of": feat.ts.isoformat(),
        }
        bars = list(reversed(repo.list_price_bars(symbol, limit=60)))
        price_closes[symbol] = [float(b.close) for b in bars]

    fx_features: Dict[str, Dict[str, Any]] = {}
    for pair in ("USDCOP", "USDCOP_SPOT", "USDCOP_TRM", "DXY"):
        feat = repo.latest_feature(pair)
        if feat:
            fx_features[pair] = {**(feat.payload or {}), "as_of": feat.ts.isoformat()}
        else:
            # Spot/TRM may be sparse; don't hard-warn for missing historical Yahoo only once.
            if pair in {"USDCOP", "DXY"}:
                warnings.append(f"missing_features:{pair}")

    macro_latest: Dict[str, Any] = {}
    for series_id in DEFAULT_SERIES:
        point = repo.latest_macro(series_id)
        if point:
            macro_latest[series_id] = {
                "value": float(point.value),
                "ts": point.ts.isoformat(),
                "source": point.source,
            }

    if not macro_latest:
        warnings.append("macro_empty")

    return AdvisoryContext(
        as_of=as_of,
        profile={
            "id": profile.id,
            "base_currency": profile.base_currency,
            "risk_profile": profile.risk_profile,
            "available_capital_usd": float(profile.available_capital_usd),
            "allocation_conservative_pct": profile.allocation_conservative_pct,
            "allocation_moderate_pct": profile.allocation_moderate_pct,
            "allocation_aggressive_pct": profile.allocation_aggressive_pct,
            "investment_horizon": profile.investment_horizon,
        },
        portfolio={
            "id": portfolio.id,
            "cash_usd": float(portfolio.cash_usd),
            "nav_usd": float(nav),
            "holdings": holdings,
            "weights": weights,
        },
        etf_features=etf_features,
        fx_features=fx_features,
        macro_latest=macro_latest,
        price_closes=price_closes,
        warnings=warnings,
    )
