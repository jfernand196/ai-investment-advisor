from enum import Enum


class RiskBucket(str, Enum):
    CONSERVATIVE = "conservative"
    MODERATE = "moderate"
    AGGRESSIVE = "aggressive"


class RecommendationAction(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"
    INCREASE = "INCREASE"
    REDUCE = "REDUCE"


class AdvisoryRunStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


ETF_RISK_BUCKETS = {
    "VOO": RiskBucket.CONSERVATIVE,
    "VTI": RiskBucket.CONSERVATIVE,
    "SCHD": RiskBucket.CONSERVATIVE,
    "QQQ": RiskBucket.MODERATE,
    "VGT": RiskBucket.MODERATE,
    "VXUS": RiskBucket.MODERATE,
    "SMH": RiskBucket.AGGRESSIVE,
    "SOXL": RiskBucket.AGGRESSIVE,
    "TQQQ": RiskBucket.AGGRESSIVE,
}

# Hard caps as % of total portfolio (Architecture v1.0)
ETF_MAX_ALLOCATION_PCT = {
    "VOO": 25.0,
    "VTI": 25.0,
    "SCHD": 25.0,
    "QQQ": 20.0,
    "VGT": 20.0,
    "VXUS": 20.0,
    "SMH": 10.0,
    "SOXL": 5.0,
    "TQQQ": 5.0,
}
