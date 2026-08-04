"""FRED API adapter (free API key). Gracefully no-ops if key missing."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import List

import httpx

from app.domain.market import MacroPoint

DEFAULT_SERIES = [
    "CPIAUCSL",  # CPI
    "UNRATE",  # Unemployment
    "DFF",  # Fed Funds Effective Rate
    "DGS10",  # 10Y Treasury
    "T10Y2Y",  # 10Y-2Y spread
]


class FredMacroClient:
    def __init__(self, api_key: str, timeout_s: float = 30.0) -> None:
        self.api_key = api_key.strip()
        self.timeout_s = timeout_s
        self.base_url = "https://api.stlouisfed.org/fred/series/observations"

    @property
    def enabled(self) -> bool:
        return bool(self.api_key)

    def fetch_macro(self, series_ids: List[str], start: date) -> List[MacroPoint]:
        if not self.enabled:
            return []

        points: List[MacroPoint] = []
        with httpx.Client(timeout=self.timeout_s) as client:
            for series_id in series_ids:
                params = {
                    "series_id": series_id,
                    "api_key": self.api_key,
                    "file_type": "json",
                    "observation_start": start.isoformat(),
                }
                response = client.get(self.base_url, params=params)
                response.raise_for_status()
                payload = response.json()
                for obs in payload.get("observations", []):
                    value_raw = obs.get("value")
                    date_raw = obs.get("date")
                    if value_raw in (None, "."):
                        continue
                    points.append(
                        MacroPoint(
                            series_id=series_id,
                            ts=date.fromisoformat(date_raw),
                            value=Decimal(str(value_raw)),
                            source="fred",
                        )
                    )
        return points
