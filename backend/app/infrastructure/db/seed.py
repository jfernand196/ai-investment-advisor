"""Idempotent seed for personal single-user bootstrap."""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.domain.enums import ETF_MAX_ALLOCATION_PCT, ETF_RISK_BUCKETS
from app.infrastructure.db.models import (
    EtfUniverseModel,
    InvestorProfileModel,
    PortfolioModel,
)

ETF_NAMES = {
    "VOO": "Vanguard S&P 500 ETF",
    "VTI": "Vanguard Total Stock Market ETF",
    "SCHD": "Schwab U.S. Dividend Equity ETF",
    "QQQ": "Invesco QQQ Trust",
    "VGT": "Vanguard Information Technology ETF",
    "VXUS": "Vanguard Total International Stock ETF",
    "SMH": "VanEck Semiconductor ETF",
    "SOXL": "Direxion Daily Semiconductor Bull 3X Shares",
    "TQQQ": "ProShares UltraPro QQQ",
}

LEVERAGED = {"SOXL", "TQQQ"}


def seed_reference_data(db: Session, settings: Settings) -> dict:
    etfs_upserted = 0
    for symbol in settings.etf_universe:
        existing = db.get(EtfUniverseModel, symbol)
        if existing is None:
            db.add(
                EtfUniverseModel(
                    symbol=symbol,
                    name=ETF_NAMES.get(symbol, symbol),
                    risk_bucket=ETF_RISK_BUCKETS[symbol].value,
                    max_allocation_pct=Decimal(str(ETF_MAX_ALLOCATION_PCT[symbol])),
                    is_leveraged=symbol in LEVERAGED,
                    is_active=True,
                    category=ETF_RISK_BUCKETS[symbol].value,
                )
            )
            etfs_upserted += 1

    profile = db.scalar(select(InvestorProfileModel).limit(1))
    profile_created = False
    portfolio_created = False

    if profile is None:
        profile = InvestorProfileModel(
            base_currency=settings.base_currency,
            risk_profile=settings.risk_profile,
            available_capital_usd=Decimal(str(settings.available_capital_usd)),
            allocation_conservative_pct=settings.allocation_conservative_pct,
            allocation_moderate_pct=settings.allocation_moderate_pct,
            allocation_aggressive_pct=settings.allocation_aggressive_pct,
            investment_horizon="long",
            favorite_etfs=list(settings.etf_universe),
            financial_goals={},
            notification_email_enabled=True,
            version=1,
        )
        db.add(profile)
        db.flush()
        profile_created = True

    portfolio = db.scalar(
        select(PortfolioModel).where(PortfolioModel.profile_id == profile.id).limit(1)
    )
    if portfolio is None:
        db.add(
            PortfolioModel(
                profile_id=profile.id,
                name="Primary",
                base_currency=settings.base_currency,
                cash_usd=Decimal(str(settings.available_capital_usd)),
                is_primary=True,
            )
        )
        portfolio_created = True

    db.commit()
    return {
        "etfs_inserted": etfs_upserted,
        "profile_created": profile_created,
        "portfolio_created": portfolio_created,
        "profile_id": profile.id,
    }
