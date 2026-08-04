"""Research agents — deterministic, no LLM."""

from __future__ import annotations

import time
from typing import Any, Dict, List

import numpy as np

from app.agents.contracts import AgentResult, EvidenceItem
from app.agents.context import AdvisoryContext
from app.domain.enums import ETF_RISK_BUCKETS, RiskBucket


def _timed(name: str, fn) -> AgentResult:
    start = time.perf_counter()
    result = fn()
    result.latency_ms = int((time.perf_counter() - start) * 1000)
    result.agent_name = name
    return result


def run_etf_agent(ctx: AdvisoryContext) -> AgentResult:
    def _run() -> AgentResult:
        signals = []
        evidence = []
        scores = {}
        for symbol, feat in ctx.etf_features.items():
            r20 = feat.get("return_20d")
            vol = feat.get("volatility_20d_ann")
            score = 0.0
            if r20 is not None:
                score += max(min(float(r20) * 5, 1.0), -1.0)
            if vol is not None and float(vol) > 0.35:
                score -= 0.15
            if ETF_RISK_BUCKETS.get(symbol) == RiskBucket.CONSERVATIVE and r20 and float(r20) > 0:
                score += 0.05
            scores[symbol] = round(score, 4)
            bias = "bullish" if score > 0.15 else "bearish" if score < -0.15 else "neutral"
            signals.append({"symbol": symbol, "score": scores[symbol], "bias": bias})
            evidence.append(
                EvidenceItem(
                    source="market_features",
                    ref_id=f"etf:{symbol}:v1",
                    summary=f"{symbol} r20={r20} vol={vol} score={scores[symbol]}",
                )
            )
        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return AgentResult(
            agent_name="etf",
            confidence=0.7 if scores else 0.2,
            signals=signals,
            evidence=evidence,
            payload={"scores": scores, "ranking": ranked},
            warnings=[w for w in ctx.warnings if w.startswith("missing_features:")],
        )

    return _timed("etf", _run)


def run_technical_agent(ctx: AdvisoryContext) -> AgentResult:
    def _run() -> AgentResult:
        signals = []
        evidence = []
        for symbol, closes in ctx.price_closes.items():
            if len(closes) < 20:
                signals.append({"symbol": symbol, "signal": "insufficient_data"})
                continue
            arr = np.array(closes, dtype=float)
            sma20 = float(np.mean(arr[-20:]))
            sma50 = float(np.mean(arr[-50:])) if len(arr) >= 50 else float(np.mean(arr))
            last = float(arr[-1])
            # RSI(14) simple
            deltas = np.diff(arr[-15:])
            gains = deltas.clip(min=0).mean() if len(deltas) else 0.0
            losses = (-deltas.clip(max=0)).mean() if len(deltas) else 0.0
            rs = gains / losses if losses > 1e-9 else 100.0
            rsi = 100 - (100 / (1 + rs))
            trend = "up" if last >= sma20 >= sma50 else "down" if last < sma20 else "mixed"
            momentum = "overbought" if rsi >= 70 else "oversold" if rsi <= 30 else "neutral"
            score = 0.0
            if trend == "up":
                score += 0.4
            elif trend == "down":
                score -= 0.4
            if momentum == "oversold":
                score += 0.2
            elif momentum == "overbought":
                score -= 0.2
            signals.append(
                {
                    "symbol": symbol,
                    "trend": trend,
                    "rsi": round(rsi, 2),
                    "sma20": round(sma20, 4),
                    "sma50": round(sma50, 4),
                    "score": round(score, 4),
                }
            )
            evidence.append(
                EvidenceItem(
                    source="price_bars",
                    ref_id=f"tech:{symbol}",
                    summary=f"{symbol} trend={trend} rsi={rsi:.1f}",
                )
            )
        return AgentResult(
            agent_name="technical",
            confidence=0.75,
            signals=signals,
            evidence=evidence,
            payload={"method": "sma20/sma50+rsi14"},
        )

    return _timed("technical", _run)


def run_dollar_agent(ctx: AdvisoryContext) -> AgentResult:
    def _run() -> AgentResult:
        feat = ctx.fx_features.get("USDCOP", {})
        r20 = feat.get("return_20d")
        rate = feat.get("rate")
        bias = "neutral"
        score = 0.0
        if r20 is not None:
            # USDCOP up => USD stronger vs COP
            score = max(min(float(r20) * 3, 1.0), -1.0)
            bias = "usd_strong" if score > 0.05 else "cop_strong" if score < -0.05 else "neutral"
        return AgentResult(
            agent_name="dollar",
            confidence=0.7 if feat else 0.2,
            signals=[{"pair": "USDCOP", "bias": bias, "score": round(score, 4), "rate": rate}],
            evidence=[
                EvidenceItem(
                    source="fx_rates",
                    ref_id="fx:USDCOP",
                    summary=f"USDCOP rate={rate} r20={r20} bias={bias}",
                )
            ]
            if feat
            else [],
            payload=feat,
            warnings=[] if feat else ["missing_USDCOP"],
        )

    return _timed("dollar", _run)


def run_dxy_agent(ctx: AdvisoryContext) -> AgentResult:
    def _run() -> AgentResult:
        feat = ctx.fx_features.get("DXY", {})
        r20 = feat.get("return_20d")
        rate = feat.get("rate")
        score = max(min(float(r20) * 4, 1.0), -1.0) if r20 is not None else 0.0
        bias = "strong" if score > 0.05 else "weak" if score < -0.05 else "neutral"
        # Strong DXY often headwind for risk assets / EM
        risk_implication = "risk_off_bias" if bias == "strong" else "risk_on_bias" if bias == "weak" else "neutral"
        return AgentResult(
            agent_name="dxy",
            confidence=0.7 if feat else 0.2,
            signals=[
                {
                    "pair": "DXY",
                    "bias": bias,
                    "score": round(score, 4),
                    "rate": rate,
                    "risk_implication": risk_implication,
                }
            ],
            evidence=[
                EvidenceItem(
                    source="fx_rates",
                    ref_id="fx:DXY",
                    summary=f"DXY rate={rate} r20={r20} implication={risk_implication}",
                )
            ]
            if feat
            else [],
            payload=feat,
            warnings=[] if feat else ["missing_DXY"],
        )

    return _timed("dxy", _run)


def run_macro_agent(ctx: AdvisoryContext) -> AgentResult:
    def _run() -> AgentResult:
        macro = ctx.macro_latest
        regime = "unknown"
        score = 0.0
        notes: List[str] = []
        if macro:
            unrate = macro.get("UNRATE", {}).get("value")
            dff = macro.get("DFF", {}).get("value")
            spread = macro.get("T10Y2Y", {}).get("value")
            if spread is not None and float(spread) < 0:
                regime = "restrictive"
                score -= 0.3
                notes.append("yield_curve_inverted_or_negative")
            elif dff is not None and float(dff) >= 4.5:
                regime = "tight"
                score -= 0.1
                notes.append("elevated_policy_rate")
            else:
                regime = "neutral"
            if unrate is not None and float(unrate) >= 5.0:
                score -= 0.2
                notes.append("elevated_unemployment")
                regime = "risk_off"
        else:
            notes.append("no_macro_data_using_neutral_prior")
            regime = "neutral_prior"

        return AgentResult(
            agent_name="macro",
            confidence=0.65 if macro else 0.35,
            signals=[{"regime": regime, "score": round(score, 4)}],
            evidence=[
                EvidenceItem(
                    source="macro_series",
                    ref_id=f"macro:{k}",
                    summary=f"{k}={v.get('value')} @ {v.get('ts')}",
                )
                for k, v in macro.items()
            ],
            payload={"regime": regime, "series": macro, "notes": notes},
            warnings=[] if macro else ["macro_empty"],
        )

    return _timed("macro", _run)


def run_portfolio_agent(ctx: AdvisoryContext) -> AgentResult:
    def _run() -> AgentResult:
        weights = ctx.portfolio.get("weights", {})
        bucket_weights = {"conservative": 0.0, "moderate": 0.0, "aggressive": 0.0, "cash": 0.0}
        for symbol, w in weights.items():
            if symbol == "CASH":
                bucket_weights["cash"] += w
                continue
            bucket = ETF_RISK_BUCKETS.get(symbol)
            if bucket:
                bucket_weights[bucket.value] += w
        return AgentResult(
            agent_name="portfolio",
            confidence=0.95,
            signals=[{"type": "allocation", "bucket_weights": bucket_weights}],
            evidence=[
                EvidenceItem(
                    source="portfolio",
                    ref_id=f"portfolio:{ctx.portfolio['id']}",
                    summary=f"NAV={ctx.portfolio['nav_usd']} cash={ctx.portfolio['cash_usd']}",
                )
            ],
            payload={
                "nav_usd": ctx.portfolio["nav_usd"],
                "cash_usd": ctx.portfolio["cash_usd"],
                "weights": weights,
                "bucket_weights": bucket_weights,
                "holdings": ctx.portfolio["holdings"],
            },
        )

    return _timed("portfolio", _run)


def run_all_research(ctx: AdvisoryContext) -> Dict[str, AgentResult]:
    return {
        "etf": run_etf_agent(ctx),
        "technical": run_technical_agent(ctx),
        "dollar": run_dollar_agent(ctx),
        "dxy": run_dxy_agent(ctx),
        "macro": run_macro_agent(ctx),
        "portfolio": run_portfolio_agent(ctx),
    }
