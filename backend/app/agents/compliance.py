"""Compliance agent — deterministic fail-closed guardrails."""

from __future__ import annotations

import time
from typing import Dict, List

from app.agents.contracts import AgentResult, EvidenceItem, RecommendationDraft
from app.agents.context import AdvisoryContext
from app.domain.enums import ETF_MAX_ALLOCATION_PCT, ETF_RISK_BUCKETS, RiskBucket


def run_compliance_agent(
    ctx: AdvisoryContext,
    strategy: AgentResult,
    risk: AgentResult,
) -> AgentResult:
    start = time.perf_counter()
    drafts = [RecommendationDraft.model_validate(d) for d in strategy.payload.get("drafts", [])]
    weights = {
        k: float(v) * 100
        for k, v in (ctx.portfolio.get("weights") or {}).items()
        if k != "CASH"
    }
    targets = {
        RiskBucket.CONSERVATIVE.value: ctx.profile["allocation_conservative_pct"],
        RiskBucket.MODERATE.value: ctx.profile["allocation_moderate_pct"],
        RiskBucket.AGGRESSIVE.value: ctx.profile["allocation_aggressive_pct"],
    }
    bucket_current = {"conservative": 0.0, "moderate": 0.0, "aggressive": 0.0}
    for symbol, w in weights.items():
        bucket = ETF_RISK_BUCKETS.get(symbol)
        if bucket:
            bucket_current[bucket.value] += w

    approved: List[RecommendationDraft] = []
    for draft in drafts:
        notes: List[str] = []
        status = "approved"
        symbol = draft.symbol
        bucket = ETF_RISK_BUCKETS[symbol].value
        cap = ETF_MAX_ALLOCATION_PCT[symbol]
        current = weights.get(symbol, 0.0)

        if draft.action in {"BUY", "INCREASE"}:
            projected = current + draft.size_pct
            if projected > cap:
                adjusted = max(cap - current, 0.0)
                if adjusted < 0.5:
                    status = "rejected"
                    draft.action = "HOLD"
                    draft.size_pct = 0.0
                    draft.size_amount_usd = 0.0
                    notes.append(f"rejected_exceeds_cap_{cap}%")
                else:
                    status = "adjusted"
                    draft.size_pct = round(adjusted, 4)
                    draft.size_amount_usd = round(
                        float(ctx.portfolio["nav_usd"]) * draft.size_pct / 100.0, 2
                    )
                    notes.append(f"adjusted_to_cap_{cap}%")

            # Bucket target hard ceiling (+2pp tolerance)
            if draft.action in {"BUY", "INCREASE"}:
                projected_bucket = bucket_current[bucket] + draft.size_pct
                if projected_bucket > targets[bucket] + 2:
                    status = "rejected"
                    draft.action = "HOLD"
                    draft.size_pct = 0.0
                    draft.size_amount_usd = 0.0
                    notes.append(f"rejected_bucket_target_{bucket}")

            if symbol in {"SOXL", "TQQQ"} and ctx.profile["risk_profile"] != "aggressive":
                status = "rejected"
                draft.action = "HOLD"
                draft.size_pct = 0.0
                draft.size_amount_usd = 0.0
                notes.append("rejected_leveraged_requires_aggressive")

            if risk.payload.get("risk_off") and symbol in {"SOXL", "TQQQ", "SMH"}:
                if draft.action in {"BUY", "INCREASE"}:
                    status = "rejected"
                    draft.action = "HOLD"
                    draft.size_pct = 0.0
                    draft.size_amount_usd = 0.0
                    notes.append("rejected_risk_off_blocks_high_beta")

        draft.compliance_status = status  # type: ignore[assignment]
        draft.compliance_notes = notes
        approved.append(draft)

        # Update local bucket tracker for sequential checks
        if draft.action in {"BUY", "INCREASE"} and status != "rejected":
            bucket_current[bucket] += draft.size_pct
            weights[symbol] = current + draft.size_pct

    return AgentResult(
        agent_name="compliance",
        confidence=1.0,
        signals=[d.model_dump() for d in approved],
        evidence=[
            EvidenceItem(
                source="compliance",
                ref_id="compliance:v1",
                summary="fail-closed allocation and leveraged ETF guards applied",
            )
        ],
        payload={"recommendations": [d.model_dump() for d in approved]},
        latency_ms=int((time.perf_counter() - start) * 1000),
    )
