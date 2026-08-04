from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class IngestRequest(BaseModel):
    lookback_days: Optional[int] = Field(default=None, ge=30, le=3000)


class IngestResponse(BaseModel):
    etf_bars: int
    fx_points: int
    macro_points: int
    features: int
    warnings: List[str]
    started_at: datetime
    finished_at: Optional[datetime]


class PriceBarOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    symbol: str
    timeframe: str
    ts: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Optional[Decimal] = None
    source: str


class FxRateOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    pair: str
    ts: datetime
    rate: Decimal
    source: str


class MacroPointOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    series_id: str
    ts: date
    value: Decimal
    source: str


class FeatureOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    entity: str
    feature_set_version: str
    ts: datetime
    payload: Dict[str, Any]


class MarketOverviewOut(BaseModel):
    usdcop: Optional[FxRateOut] = None
    dxy: Optional[FxRateOut] = None
    etf_latest_features: List[FeatureOut]
    macro_latest: List[MacroPointOut]
    warnings: List[str] = []
