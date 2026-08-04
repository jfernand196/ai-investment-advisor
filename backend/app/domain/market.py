"""Market domain value objects (provider-agnostic)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class OhlcvBar:
    symbol: str
    timeframe: str
    ts: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Optional[Decimal]
    source: str = "yfinance"


@dataclass(frozen=True)
class FxPoint:
    pair: str
    ts: datetime
    rate: Decimal
    source: str = "yfinance"


@dataclass(frozen=True)
class MacroPoint:
    series_id: str
    ts: date
    value: Decimal
    source: str = "fred"


@dataclass(frozen=True)
class FeatureSnapshot:
    entity: str
    feature_set_version: str
    ts: datetime
    payload: Dict[str, Any]
