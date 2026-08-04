from __future__ import annotations

from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict


class EtfOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    symbol: str
    name: str
    risk_bucket: str
    max_allocation_pct: Decimal
    is_leveraged: bool
    is_active: bool
    category: Optional[str] = None
