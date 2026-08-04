"""Deterministic feature engineering (no LLM)."""

from __future__ import annotations

from collections import defaultdict
from typing import Dict, Iterable, List, Optional

import numpy as np

from app.domain.market import FeatureSnapshot, FxPoint, OhlcvBar

FEATURE_SET_VERSION = "v1"


def _returns(closes: List[float], window: int) -> Optional[float]:
    if len(closes) <= window:
        return None
    prev = closes[-(window + 1)]
    last = closes[-1]
    if prev == 0:
        return None
    return (last / prev) - 1.0


def _volatility(closes: List[float], window: int = 20) -> Optional[float]:
    if len(closes) < window + 1:
        return None
    arr = np.array(closes[-(window + 1) :], dtype=float)
    rets = np.diff(arr) / arr[:-1]
    if len(rets) == 0:
        return None
    return float(np.std(rets, ddof=1) * np.sqrt(252))


def build_equity_features(bars: Iterable[OhlcvBar]) -> List[FeatureSnapshot]:
    by_symbol: Dict[str, List[OhlcvBar]] = defaultdict(list)
    for bar in bars:
        by_symbol[bar.symbol].append(bar)

    features: List[FeatureSnapshot] = []
    for symbol, series in by_symbol.items():
        series.sort(key=lambda b: b.ts)
        closes = [float(b.close) for b in series]
        if not closes:
            continue
        last = series[-1]
        payload = {
            "close": float(last.close),
            "return_1d": _returns(closes, 1),
            "return_5d": _returns(closes, 5),
            "return_20d": _returns(closes, 20),
            "volatility_20d_ann": _volatility(closes, 20),
            "bars": len(series),
        }
        features.append(
            FeatureSnapshot(
                entity=symbol,
                feature_set_version=FEATURE_SET_VERSION,
                ts=last.ts,
                payload=payload,
            )
        )
    return features


def build_fx_features(points: Iterable[FxPoint]) -> List[FeatureSnapshot]:
    by_pair: Dict[str, List[FxPoint]] = defaultdict(list)
    for point in points:
        by_pair[point.pair].append(point)

    features: List[FeatureSnapshot] = []
    for pair, series in by_pair.items():
        series.sort(key=lambda p: p.ts)
        closes = [float(p.rate) for p in series]
        if not closes:
            continue
        last = series[-1]
        payload = {
            "rate": float(last.rate),
            "return_1d": _returns(closes, 1),
            "return_5d": _returns(closes, 5),
            "return_20d": _returns(closes, 20),
            "volatility_20d_ann": _volatility(closes, 20),
            "points": len(series),
            "source": last.source,
        }
        features.append(
            FeatureSnapshot(
                entity=pair,
                feature_set_version=FEATURE_SET_VERSION,
                ts=last.ts,
                payload=payload,
            )
        )
    return features
