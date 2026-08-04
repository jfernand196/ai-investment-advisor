from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class HoldingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    symbol: str
    quantity: Decimal
    avg_cost_usd: Decimal
    updated_at: datetime


class PortfolioOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    base_currency: str
    cash_usd: Decimal
    is_primary: bool
    holdings: List[HoldingOut]
    created_at: datetime
    updated_at: datetime


class HoldingUpsert(BaseModel):
    symbol: str = Field(min_length=1, max_length=16)
    quantity: Decimal = Field(ge=0)
    avg_cost_usd: Decimal = Field(ge=0)


class PortfolioHoldingsReplace(BaseModel):
    cash_usd: Optional[Decimal] = Field(default=None, ge=0)
    holdings: List[HoldingUpsert]
