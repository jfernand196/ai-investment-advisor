from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class InvestorProfileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    base_currency: str
    risk_profile: str
    available_capital_usd: Decimal
    allocation_conservative_pct: int
    allocation_moderate_pct: int
    allocation_aggressive_pct: int
    investment_horizon: str
    favorite_etfs: List[Any]
    financial_goals: dict
    notification_email_enabled: bool
    version: int
    created_at: datetime
    updated_at: datetime


class InvestorProfileUpdate(BaseModel):
    available_capital_usd: Optional[Decimal] = Field(default=None, ge=0)
    risk_profile: Optional[str] = None
    allocation_conservative_pct: Optional[int] = Field(default=None, ge=0, le=100)
    allocation_moderate_pct: Optional[int] = Field(default=None, ge=0, le=100)
    allocation_aggressive_pct: Optional[int] = Field(default=None, ge=0, le=100)
    investment_horizon: Optional[str] = None
    favorite_etfs: Optional[List[str]] = None
    financial_goals: Optional[dict] = None
    notification_email_enabled: Optional[bool] = None
