"""Market data ingestion use case."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from typing import List, Optional

from app.application.market.features import build_equity_features, build_fx_features
from app.core.config import Settings
from app.infrastructure.db.market_repository import MarketRepository
from app.infrastructure.market.fred_client import DEFAULT_SERIES, FredMacroClient
from app.infrastructure.market.yfinance_client import YFinanceMarketClient


@dataclass
class IngestResult:
    etf_bars: int = 0
    fx_points: int = 0
    macro_points: int = 0
    features: int = 0
    warnings: List[str] = field(default_factory=list)
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    finished_at: Optional[datetime] = None

    def finalize(self) -> "IngestResult":
        self.finished_at = datetime.now(timezone.utc)
        return self


class IngestMarketDataUseCase:
    def __init__(
        self,
        repo: MarketRepository,
        settings: Settings,
        equity_fx_client: Optional[YFinanceMarketClient] = None,
        macro_client: Optional[FredMacroClient] = None,
    ) -> None:
        self.repo = repo
        self.settings = settings
        self.equity_fx_client = equity_fx_client or YFinanceMarketClient()
        self.macro_client = macro_client or FredMacroClient(settings.fred_api_key)

    def execute(self, lookback_days: Optional[int] = None) -> IngestResult:
        result = IngestResult()
        days = lookback_days or self.settings.market_lookback_days

        try:
            bars = self.equity_fx_client.fetch_ohlcv(self.settings.etf_universe, days)
            result.etf_bars = self.repo.upsert_price_bars(bars)
        except Exception as exc:  # noqa: BLE001
            result.warnings.append(f"etf_ingest_failed: {exc}")
            bars = []

        try:
            fx_points = self.equity_fx_client.fetch_fx(["USDCOP", "DXY"], days)
            result.fx_points = self.repo.upsert_fx(fx_points)
        except Exception as exc:  # noqa: BLE001
            result.warnings.append(f"fx_ingest_failed: {exc}")
            fx_points = []

        if self.macro_client.enabled:
            try:
                start = date.today() - timedelta(days=days)
                macro_points = self.macro_client.fetch_macro(DEFAULT_SERIES, start)
                result.macro_points = self.repo.upsert_macro(macro_points)
            except Exception as exc:  # noqa: BLE001
                result.warnings.append(f"macro_ingest_failed: {exc}")
        else:
            result.warnings.append(
                "FRED_API_KEY empty — macro series skipped. Get a free key at https://fred.stlouisfed.org/docs/api/api_key.html"
            )

        try:
            features = build_equity_features(bars) + build_fx_features(fx_points)
            result.features = self.repo.upsert_features(features)
        except Exception as exc:  # noqa: BLE001
            result.warnings.append(f"feature_build_failed: {exc}")

        self.repo.commit()
        return result.finalize()
