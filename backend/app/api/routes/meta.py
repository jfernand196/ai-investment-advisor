from fastapi import APIRouter, Depends

from app.core.config import Settings, get_settings
from app.domain.enums import ETF_MAX_ALLOCATION_PCT, ETF_RISK_BUCKETS

router = APIRouter()


@router.get("/meta/config")
def public_config(settings: Settings = Depends(get_settings)) -> dict:
    """Non-secret product defaults for the dashboard bootstrap."""
    return {
        "app_name": settings.app_name,
        "base_currency": settings.base_currency,
        "risk_profile": settings.risk_profile,
        "allocation_targets": {
            "conservative_pct": settings.allocation_conservative_pct,
            "moderate_pct": settings.allocation_moderate_pct,
            "aggressive_pct": settings.allocation_aggressive_pct,
        },
        "available_capital_usd": settings.available_capital_usd,
        "etf_universe": [
            {
                "symbol": symbol,
                "bucket": ETF_RISK_BUCKETS[symbol].value,
                "max_allocation_pct": ETF_MAX_ALLOCATION_PCT[symbol],
            }
            for symbol in settings.etf_universe
        ],
        "notifications": ["dashboard", "email"],
    }
