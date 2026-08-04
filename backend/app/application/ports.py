"""Application ports (interfaces). Implementations live in infrastructure."""

from __future__ import annotations

from datetime import date
from typing import List, Protocol

from app.domain.market import FxPoint, MacroPoint, OhlcvBar


class EquityHistoryPort(Protocol):
    def fetch_ohlcv(self, symbols: List[str], lookback_days: int) -> List[OhlcvBar]:
        """Fetch daily OHLCV bars for equity/ETF symbols."""


class FxHistoryPort(Protocol):
    def fetch_fx(self, pairs: List[str], lookback_days: int) -> List[FxPoint]:
        """Fetch FX / dollar index points. pairs use internal names (USDCOP, DXY)."""


class MacroHistoryPort(Protocol):
    def fetch_macro(self, series_ids: List[str], start: date) -> List[MacroPoint]:
        """Fetch macroeconomic series."""
