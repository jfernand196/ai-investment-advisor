"""Risk agent — deterministic risk budget and concentration checks."""

from __future__ import annotations

import time
from typing import Dict

from app.agents.contracts import AgentResult, EvidenceItem
from app.agents.context import AdvisoryContext
from app.domain.enums import ETF_MAX_ALLOCATION_PCT, ETF_RISK_BUCKETS


def run_risk_agent(ctx: AdvisoryContext, research: Dict[str, AgentResult]) -> AgentResult:
    start = time.perf_counter()
    profile = ctx.profile
    targets = {
        "conservative": profile["allocation_conservative_pct"] / 100.0,
        "moderate": profile["allocation_moderate_pct"] / 100.0,
        "aggressive": profile["allocation_aggressive_pct"] / 100.0,
    }
    portfolio = research["portfolio"].payload
    bucket_weights = portfolio.get("bucket_weights", {})
    weights = portfolio.get("weights", {})

    flags = []
    for bucket, target in targets.items():
        current = float(bucket_weights.get(bucket, 0.0))
        drift = current - target
        if abs(drift) >= 0.08:
            flags.append(
                {
                    "type": "bucket_drift",
                    "bucket": bucket,
                    "current": round(current, 4),
                    "target": target,
                    "drift": round(drift, 4),
                }
            )

    for symbol, max_pct in ETF_MAX_ALLOCATION_PCT.items():
        w = float(weights.get(symbol, 0.0)) * 100
        if w > max_pct + 0.5:
            flags.append(
                {
                    "type": "concentration_breach",
                    "symbol": symbol,
                    "weight_pct": round(w, 2),
                    "max_pct": max_pct,
                }
            )

    # Remaining risk budget for aggressive sleeve
    aggressive_current = float(bucket_weights.get("aggressive", 0.0))
    aggressive_budget = max(targets["aggressive"] - aggressive_current, 0.0)
    cash_pct = float(bucket_weights.get("cash", 0.0))

    dxy = research.get("dxy")
    risk_off = False
    if dxy and dxy.signals:
        risk_off = dxy.signals[0].get("risk_implication") == "risk_off_bias"

    macro = research.get("macro")
    if macro and macro.payload.get("regime") in {"restrictive", "risk_off", "tight"}:
        risk_off = True

    max_new_risk_pct = 5.0 if risk_off else 10.0
    if profile["risk_profile"] == "aggressive" and not risk_off:
        max_new_risk_pct = 12.0

    result = AgentResult(
        agent_name="risk",
        confidence=0.85,
        signals=[
            {
                "aggressive_budget_pct": round(aggressive_budget * 100, 2),
                "cash_pct": round(cash_pct * 100, 2),
                "max_new_position_pct": max_new_risk_pct,
                "risk_off": risk_off,
                "flags": flags,
            }
        ],
        evidence=[
            EvidenceItem(
                source="risk_engine",
                ref_id="risk:budget",
                summary=f"risk_off={risk_off} cash={cash_pct:.1%} agg_budget={aggressive_budget:.1%}",
            )
        ],
        payload={
            "targets": targets,
            "bucket_weights": bucket_weights,
            "flags": flags,
            "max_new_position_pct": max_new_risk_pct,
            "risk_off": risk_off,
            "per_symbol_caps": ETF_MAX_ALLOCATION_PCT,
        },
        latency_ms=int((time.perf_counter() - start) * 1000),
    )
    return result
