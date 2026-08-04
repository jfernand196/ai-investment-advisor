"""Strategy agent — rule-based drafts (LLM can refine later)."""

from __future__ import annotations

import time
from typing import Dict, List

from app.agents.contracts import AgentResult, EvidenceItem, RecommendationDraft
from app.agents.context import AdvisoryContext
from app.domain.enums import ETF_MAX_ALLOCATION_PCT, ETF_RISK_BUCKETS, RiskBucket


def run_strategy_agent(
    ctx: AdvisoryContext,
    research: Dict[str, AgentResult],
    risk: AgentResult,
) -> AgentResult:
    start = time.perf_counter()
    etf_scores = {s["symbol"]: s.get("score", 0.0) for s in research["etf"].signals if "symbol" in s}
    tech_scores = {
        s["symbol"]: s.get("score", 0.0) for s in research["technical"].signals if "symbol" in s
    }
    weights = research["portfolio"].payload.get("weights", {})
    nav = float(ctx.portfolio["nav_usd"] or ctx.profile["available_capital_usd"] or 1)
    cash = float(ctx.portfolio["cash_usd"])
    risk_off = bool(risk.payload.get("risk_off"))
    max_new = float(risk.payload.get("max_new_position_pct", 5.0))

    drafts: List[RecommendationDraft] = []

    for symbol in ctx.etf_features.keys():
        combined = 0.6 * float(etf_scores.get(symbol, 0.0)) + 0.4 * float(tech_scores.get(symbol, 0.0))
        if risk_off and ETF_RISK_BUCKETS[symbol] == RiskBucket.AGGRESSIVE:
            combined -= 0.35

        current_w = float(weights.get(symbol, 0.0)) * 100
        cap = ETF_MAX_ALLOCATION_PCT[symbol]
        room = max(cap - current_w, 0.0)
        rationale = [
            f"combined_score={combined:.3f}",
            f"current_weight={current_w:.2f}%",
            f"cap={cap}%",
        ]
        refs = [f"etf:{symbol}:v1", f"tech:{symbol}"]

        action = "HOLD"
        size_pct = 0.0

        if combined >= 0.25 and room >= 1.0 and cash > 0:
            action = "BUY" if current_w < 0.5 else "INCREASE"
            size_pct = min(room, max_new, cash / nav * 100)
            rationale.append("momentum_and_trend_support_entry")
        elif combined <= -0.25 and current_w > 0:
            action = "SELL" if combined <= -0.45 else "REDUCE"
            size_pct = min(current_w, max_new if action == "REDUCE" else current_w)
            rationale.append("weak_momentum_suggests_trim")
        else:
            rationale.append("no_edge_hold")

        # Leveraged ETFs: only when aggressive profile and not risk_off
        if symbol in {"SOXL", "TQQQ"}:
            if ctx.profile["risk_profile"] != "aggressive" or risk_off:
                if action in {"BUY", "INCREASE"}:
                    action = "HOLD"
                    size_pct = 0.0
                    rationale.append("leveraged_blocked_by_regime_or_profile")

        amount = round(nav * (size_pct / 100.0), 2)
        drafts.append(
            RecommendationDraft(
                symbol=symbol,
                action=action,  # type: ignore[arg-type]
                size_pct=round(size_pct, 4),
                size_amount_usd=amount,
                confidence=min(0.9, 0.45 + abs(combined) / 2),
                rationale_points=rationale,
                evidence_refs=refs,
            )
        )

    # Prefer actionable first, keep all for transparency
    actionable = [d for d in drafts if d.action != "HOLD"]
    holds = [d for d in drafts if d.action == "HOLD"]
    ordered = sorted(actionable, key=lambda d: d.confidence, reverse=True) + holds

    return AgentResult(
        agent_name="strategy",
        confidence=0.7,
        signals=[d.model_dump() for d in ordered],
        evidence=[
            EvidenceItem(
                source="strategy",
                ref_id="strategy:v1",
                summary=f"{len(actionable)} actionable / {len(drafts)} total; risk_off={risk_off}",
            )
        ],
        payload={"drafts": [d.model_dump() for d in ordered], "risk_off": risk_off},
        latency_ms=int((time.perf_counter() - start) * 1000),
    )
