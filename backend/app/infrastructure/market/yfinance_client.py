"""yfinance adapter — free market data for personal use."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Dict, List, Optional

import pandas as pd
import yfinance as yf

from app.domain.market import FxPoint, OhlcvBar

FX_TICKERS: Dict[str, str] = {
    "USDCOP": "USDCOP=X",
    "DXY": "DX-Y.NYB",
}

DXY_FALLBACK_TICKER = "UUP"


def _to_decimal(value: object) -> Optional[Decimal]:
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    try:
        return Decimal(str(round(float(value), 6)))
    except (ValueError, TypeError):
        return None


def _normalize_ts(ts: object) -> datetime:
    stamp = pd.Timestamp(ts)
    if stamp.tzinfo is None:
        return stamp.to_pydatetime().replace(tzinfo=timezone.utc)
    return stamp.to_pydatetime().astimezone(timezone.utc)


class YFinanceMarketClient:
    def fetch_ohlcv(self, symbols: List[str], lookback_days: int) -> List[OhlcvBar]:
        bars: List[OhlcvBar] = []
        end = datetime.now(timezone.utc)
        start = end - timedelta(days=lookback_days + 7)

        for symbol in symbols:
            frame = self._download_single(symbol, start, end)
            if frame is None:
                continue
            bars.extend(self._frame_to_bars(symbol, frame))
        return bars

    def fetch_fx(self, pairs: List[str], lookback_days: int) -> List[FxPoint]:
        points: List[FxPoint] = []
        end = datetime.now(timezone.utc)
        start = end - timedelta(days=lookback_days + 7)

        for pair in pairs:
            ticker = FX_TICKERS.get(pair)
            if not ticker:
                continue
            frame = self._download_single(ticker, start, end)
            source = "yfinance"
            if frame is None and pair == "DXY":
                frame = self._download_single(DXY_FALLBACK_TICKER, start, end)
                source = "yfinance:UUP"
            if frame is None:
                continue

            for ts, row in frame.iterrows():
                rate = _to_decimal(row.get("Close"))
                if rate is None:
                    continue
                points.append(
                    FxPoint(
                        pair=pair,
                        ts=_normalize_ts(ts),
                        rate=rate,
                        source=source,
                    )
                )
        return points

    def _download_single(
        self,
        ticker: str,
        start: datetime,
        end: datetime,
    ) -> Optional[pd.DataFrame]:
        data = yf.download(
            tickers=ticker,
            start=start.date().isoformat(),
            end=(end + timedelta(days=1)).date().isoformat(),
            auto_adjust=True,
            progress=False,
            threads=False,
        )
        if data is None or data.empty:
            return None
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)
        return data

    def _frame_to_bars(self, symbol: str, frame: pd.DataFrame) -> List[OhlcvBar]:
        bars: List[OhlcvBar] = []
        for ts, row in frame.iterrows():
            open_ = _to_decimal(row.get("Open"))
            high = _to_decimal(row.get("High"))
            low = _to_decimal(row.get("Low"))
            close = _to_decimal(row.get("Close"))
            volume = _to_decimal(row.get("Volume"))
            if None in (open_, high, low, close):
                continue
            bars.append(
                OhlcvBar(
                    symbol=symbol,
                    timeframe="1D",
                    ts=_normalize_ts(ts),
                    open=open_,
                    high=high,
                    low=low,
                    close=close,
                    volume=volume,
                    source="yfinance",
                )
            )
        return bars
