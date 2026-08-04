"""Persistence helpers for market data upserts."""

from __future__ import annotations

from typing import List, Optional, Sequence

from sqlalchemy import Select, desc, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.domain.market import FeatureSnapshot, FxPoint, MacroPoint, OhlcvBar
from app.infrastructure.db.models import (
    FxRateModel,
    MacroSeriesModel,
    MarketFeatureModel,
    PriceBarModel,
)


class MarketRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def upsert_price_bars(self, bars: Sequence[OhlcvBar]) -> int:
        if not bars:
            return 0
        rows = [
            {
                "symbol": b.symbol,
                "timeframe": b.timeframe,
                "ts": b.ts,
                "open": b.open,
                "high": b.high,
                "low": b.low,
                "close": b.close,
                "volume": b.volume,
                "source": b.source,
            }
            for b in bars
        ]
        stmt = insert(PriceBarModel).values(rows)
        stmt = stmt.on_conflict_do_update(
            constraint="uq_price_bars_symbol_tf_ts",
            set_={
                "open": stmt.excluded.open,
                "high": stmt.excluded.high,
                "low": stmt.excluded.low,
                "close": stmt.excluded.close,
                "volume": stmt.excluded.volume,
                "source": stmt.excluded.source,
            },
        )
        self.db.execute(stmt)
        return len(rows)

    def upsert_fx(self, points: Sequence[FxPoint]) -> int:
        if not points:
            return 0
        rows = [
            {
                "pair": p.pair,
                "ts": p.ts,
                "rate": p.rate,
                "source": p.source,
            }
            for p in points
        ]
        stmt = insert(FxRateModel).values(rows)
        stmt = stmt.on_conflict_do_update(
            constraint="uq_fx_rates_pair_ts",
            set_={
                "rate": stmt.excluded.rate,
                "source": stmt.excluded.source,
            },
        )
        self.db.execute(stmt)
        return len(rows)

    def upsert_macro(self, points: Sequence[MacroPoint]) -> int:
        if not points:
            return 0
        rows = [
            {
                "series_id": p.series_id,
                "ts": p.ts,
                "value": p.value,
                "source": p.source,
            }
            for p in points
        ]
        stmt = insert(MacroSeriesModel).values(rows)
        stmt = stmt.on_conflict_do_update(
            constraint="uq_macro_series_id_ts",
            set_={
                "value": stmt.excluded.value,
                "source": stmt.excluded.source,
            },
        )
        self.db.execute(stmt)
        return len(rows)

    def upsert_features(self, features: Sequence[FeatureSnapshot]) -> int:
        if not features:
            return 0
        rows = [
            {
                "entity": f.entity,
                "feature_set_version": f.feature_set_version,
                "ts": f.ts,
                "payload": f.payload,
            }
            for f in features
        ]
        stmt = insert(MarketFeatureModel).values(rows)
        stmt = stmt.on_conflict_do_update(
            constraint="uq_market_features_entity_version_ts",
            set_={"payload": stmt.excluded.payload},
        )
        self.db.execute(stmt)
        return len(rows)

    def list_price_bars(
        self,
        symbol: str,
        timeframe: str = "1D",
        limit: int = 120,
    ) -> List[PriceBarModel]:
        stmt: Select = (
            select(PriceBarModel)
            .where(PriceBarModel.symbol == symbol.upper(), PriceBarModel.timeframe == timeframe)
            .order_by(desc(PriceBarModel.ts))
            .limit(limit)
        )
        return list(self.db.scalars(stmt).all())

    def latest_fx(self, pair: str) -> Optional[FxRateModel]:
        stmt = (
            select(FxRateModel)
            .where(FxRateModel.pair == pair.upper())
            .order_by(desc(FxRateModel.ts))
            .limit(1)
        )
        return self.db.scalars(stmt).first()

    def list_fx(self, pair: str, limit: int = 120) -> List[FxRateModel]:
        stmt = (
            select(FxRateModel)
            .where(FxRateModel.pair == pair.upper())
            .order_by(desc(FxRateModel.ts))
            .limit(limit)
        )
        return list(self.db.scalars(stmt).all())

    def latest_macro(self, series_id: str) -> Optional[MacroSeriesModel]:
        stmt = (
            select(MacroSeriesModel)
            .where(MacroSeriesModel.series_id == series_id)
            .order_by(desc(MacroSeriesModel.ts))
            .limit(1)
        )
        return self.db.scalars(stmt).first()

    def latest_feature(self, entity: str, version: str = "v1") -> Optional[MarketFeatureModel]:
        stmt = (
            select(MarketFeatureModel)
            .where(
                MarketFeatureModel.entity == entity,
                MarketFeatureModel.feature_set_version == version,
            )
            .order_by(desc(MarketFeatureModel.ts))
            .limit(1)
        )
        return self.db.scalars(stmt).first()

    def commit(self) -> None:
        self.db.commit()
