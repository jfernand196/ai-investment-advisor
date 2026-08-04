"""USD/COP spot from Google Finance (market mid, intraday)."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

import httpx

from app.domain.market import FxPoint

GOOGLE_USDCOP_URL = "https://www.google.com/finance/quote/USD-COP"


class GoogleFinanceFxClient:
    """Best-effort scrape of Google Finance USD-COP last price."""

    def __init__(self, timeout_s: float = 30.0) -> None:
        self.timeout_s = timeout_s

    def fetch_usdcop_spot(self) -> Optional[FxPoint]:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "en-US,en;q=0.9",
        }
        with httpx.Client(timeout=self.timeout_s, headers=headers, follow_redirects=True) as client:
            response = client.get(GOOGLE_USDCOP_URL)
            response.raise_for_status()
            html = response.text

        # Primary: price container used by Google Finance quote page
        match = re.search(
            r'class="N6SYTe"[^>]*>\s*<span[^>]*>\s*<span[^>]*>\s*([0-9,]+\.[0-9]+)\s*</span>',
            html,
        )
        if not match:
            match = re.search(r"USD / COP[^0-9]{0,120}([0-9,]+\.[0-9]+)", html)
        if not match:
            return None

        rate = Decimal(match.group(1).replace(",", ""))
        return FxPoint(
            pair="USDCOP_SPOT",
            ts=datetime.now(timezone.utc).replace(second=0, microsecond=0),
            rate=rate,
            source="google_finance",
        )
