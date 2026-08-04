"""Official Colombian TRM (USD/COP) from datos.gov.co open data."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import List

import httpx

from app.domain.market import FxPoint

# Dataset: Tasa de Cambio Representativa del Mercado (TRM)
TRM_URL = "https://www.datos.gov.co/resource/32sa-8pi3.json"


class ColombiaTrmClient:
    """Primary USDCOP source for Colombia — official daily TRM."""

    def __init__(self, timeout_s: float = 30.0) -> None:
        self.timeout_s = timeout_s

    def fetch_usdcop(self, lookback_days: int) -> List[FxPoint]:
        # Fetch enough rows to cover weekends/holidays gaps.
        limit = max(lookback_days + 40, 60)
        params = {
            "$limit": str(limit),
            "$order": "vigenciadesde DESC",
        }
        with httpx.Client(timeout=self.timeout_s, headers={"User-Agent": "ai-investment-advisor/1.0"}) as client:
            response = client.get(TRM_URL, params=params)
            response.raise_for_status()
            rows = response.json()

        cutoff = datetime.now(timezone.utc) - timedelta(days=lookback_days + 7)
        points: List[FxPoint] = []
        for row in rows:
            raw_date = row.get("vigenciadesde")
            raw_value = row.get("valor")
            if not raw_date or raw_value is None:
                continue
            # Example: 2026-08-04T00:00:00.000
            ts = datetime.fromisoformat(raw_date.replace("Z", "+00:00"))
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            else:
                ts = ts.astimezone(timezone.utc)
            if ts < cutoff:
                continue
            points.append(
                FxPoint(
                    pair="USDCOP_TRM",
                    ts=ts,
                    rate=Decimal(str(raw_value)),
                    source="datos.gov.co/TRM",
                )
            )

        # Return chronological order for feature engineering
        points.sort(key=lambda p: p.ts)
        return points
