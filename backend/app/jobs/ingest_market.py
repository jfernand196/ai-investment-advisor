"""CLI: python -m app.jobs.ingest_market [--lookback-days 365]"""

from __future__ import annotations

import argparse
import json

from app.application.market.ingest import IngestMarketDataUseCase
from app.core.config import get_settings
from app.infrastructure.db.market_repository import MarketRepository
from app.infrastructure.db.session import SessionLocal


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest ETF/FX/macro market data")
    parser.add_argument("--lookback-days", type=int, default=None)
    args = parser.parse_args()

    settings = get_settings()
    db = SessionLocal()
    try:
        result = IngestMarketDataUseCase(
            repo=MarketRepository(db),
            settings=settings,
        ).execute(lookback_days=args.lookback_days)
        print(
            json.dumps(
                {
                    "etf_bars": result.etf_bars,
                    "fx_points": result.fx_points,
                    "macro_points": result.macro_points,
                    "features": result.features,
                    "warnings": result.warnings,
                    "started_at": result.started_at.isoformat(),
                    "finished_at": result.finished_at.isoformat() if result.finished_at else None,
                },
                indent=2,
            )
        )
    finally:
        db.close()


if __name__ == "__main__":
    main()
